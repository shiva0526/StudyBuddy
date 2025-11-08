from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import uuid
import shutil
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from backend.db_client import db_client
from backend.llm_client import llm_client
from backend.extract import extract_text
from backend.chunk import chunk_text
from backend.embeddings import store_chunk_embedding, retrieve_top_k
from backend.rag import rag_query
from backend.plan_generator import generate_plan
from backend.quiz import generate_quiz, grade_quiz
from backend.revision import generate_revision_pack
from backend.videos import find_best_videos_for_topic
from backend.spaced_repetition import get_due_cards, review_card, create_flashcard
from backend.topic_parser import parse_topics_from_csv, parse_topics_from_text, merge_and_deduplicate_topics
from backend.question_generator import generate_topic_questions, generate_important_questions, compute_topic_frequency

app = FastAPI(title="StudyBuddy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("exports", exist_ok=True)

try:
    app.mount("/exports", StaticFiles(directory="exports"), name="exports")
except:
    pass

class CreatePlanRequest(BaseModel):
    username: str
    subject: str
    topics: List[str]
    exam_date: str
    prefs: Dict[str, Any]

class RAGQueryRequest(BaseModel):
    username: str
    query: str
    use_only_my_materials: bool = False

class GenerateQuizRequest(BaseModel):
    username: str
    topic: str
    num_questions: int = 5
    difficulty: str = "medium"

class SubmitQuizRequest(BaseModel):
    username: str
    quiz_id: str
    answers: List[int]

class GenerateRevisionPackRequest(BaseModel):
    username: str
    options: Optional[Dict] = None

class SessionStartRequest(BaseModel):
    username: str
    session_id: str

class ReviewCardRequest(BaseModel):
    username: str
    card_id: str
    quality: int

class FindVideosRequest(BaseModel):
    username: str
    topic: str

@app.get("/")
async def root():
    return {"message": "StudyBuddy API", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {"status": "ok"}

@app.get("/api/user/{username}")
async def get_or_create_user(username: str):
    """Get or create user profile using PostgreSQL"""
    user = db_client.get_user(username)
    
    if not user:
        prefs = {
            "daily_minutes": 60,
            "session_length": 45,
            "preferred_times": ["morning", "evening"]
        }
        user = db_client.create_user(username, username, prefs)
    
    # Convert datetime to ISO string if present
    if 'created_at' in user and user['created_at']:
        user['created_at'] = user['created_at'].isoformat()
    
    return user

@app.post("/api/create_plan")
async def create_plan(
    username: str = Form(...),
    subject: str = Form(...),
    exam_date: str = Form(...),
    prefs: str = Form("{}"),
    topics_text: str = Form(""),
    topics_csv: Optional[UploadFile] = File(None),
    files: List[UploadFile] = File(default=[])
):
    """
    Create personalized study plan with integrated resource indexing and question generation.
    Accepts multipart form-data with topics (typed or CSV) and resource files.
    """
    logger.info(f"Creating integrated plan for user: {username}, subject: {subject}")
    
    try:
        # Parse preferences
        import json
        prefs_dict = json.loads(prefs) if prefs else {}
    except:
        prefs_dict = {}
    
    # Step 1: Parse and merge topics
    typed_topics = parse_topics_from_text(topics_text) if topics_text else []
    csv_topics = []
    
    if topics_csv:
        try:
            csv_content = await topics_csv.read()
            csv_topics = parse_topics_from_csv(csv_content, topics_csv.filename)
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")
    
    # Merge and deduplicate topics
    final_topics = merge_and_deduplicate_topics(typed_topics, csv_topics)
    
    if not final_topics:
        raise HTTPException(status_code=400, detail="No topics provided")
    
    logger.info(f"Final topics ({len(final_topics)}): {final_topics}")
    
    # Step 2: Create plan ID and initialize plan
    plan_id = str(uuid.uuid4())
    
    # Step 3: Process uploaded files (notes and past papers)
    resource_ids = []
    resource_chunks = {}
    
    for file in files:
        try:
            # Generate resource ID
            resource_id = str(uuid.uuid4())
            
            # SECURITY: Sanitize filename to prevent path traversal
            # Use only the base filename (no path components)
            import os
            original_filename = os.path.basename(file.filename)
            
            # Additional safety: use UUID-based filename but keep extension
            file_extension = os.path.splitext(original_filename)[1]
            safe_filename = f"{resource_id}{file_extension}"
            file_path = f"uploads/{safe_filename}"
            
            # Store original filename in metadata
            filename = original_filename
            
            # Save file
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            logger.info(f"Saved file: {filename} -> {file_path}")
            
            # Extract text
            text = extract_text(file_path)
            
            if not text:
                logger.warning(f"No text extracted from {filename}")
                continue
            
            # Chunk text
            chunks = chunk_text(text)
            
            # Store resource metadata
            db_client.store_resource(
                resource_id=resource_id,
                filename=filename,
                path=file_path,
                type="note",  # Could be enhanced to detect type
                uploader=username,
                chunks=len(chunks)
            )
            
            # Store chunks and embeddings
            chunk_data = []
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"chunk_{i}"
                
                # Store chunk
                db_client.store_chunk(
                    resource_id=resource_id,
                    chunk_id=chunk_id,
                    text=chunk_text,
                    start_pos=i * 1000,
                    end_pos=i * 1000 + len(chunk_text)
                )
                
                # Store embedding
                store_chunk_embedding(resource_id, chunk_id, chunk_text)
                
                chunk_data.append({
                    'chunk_id': chunk_id,
                    'text': chunk_text
                })
            
            resource_chunks[resource_id] = chunk_data
            resource_ids.append(resource_id)
            
            logger.info(f"Indexed {len(chunks)} chunks from {filename}")
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            # Continue with other files
    
    # Step 4: Generate base study plan
    result = generate_plan(
        username,
        subject,
        final_topics,
        exam_date,
        prefs_dict
    )
    
    # Use the generated plan_id
    plan_id = result['plan_id']
    
    # Step 5: Generate practice questions for each topic
    all_questions = {}
    topic_frequencies = {}
    
    for topic in final_topics:
        # Retrieve relevant chunks for this topic
        try:
            top_chunks = retrieve_top_k(topic, k=5)
            context_chunks = [chunk['text'] for chunk in top_chunks]
        except:
            context_chunks = []
        
        # Generate questions for this topic
        questions = generate_topic_questions(
            llm_client,
            topic,
            context_chunks,
            num_questions=prefs_dict.get('questions_per_topic', 5)
        )
        
        all_questions[topic] = questions
        
        # Store questions in database
        db_client.store_plan_questions(plan_id, topic, questions)
        
        # Compute topic frequency for important questions ranking
        topic_frequencies[topic] = compute_topic_frequency(topic, resource_chunks)
        
        logger.info(f"Generated {len(questions)} questions for topic '{topic}'")
    
    # Step 6: Generate Important Questions list
    important_questions = generate_important_questions(
        llm_client,
        final_topics,
        all_questions,
        topic_frequencies,
        top_n=prefs_dict.get('important_questions_count', 10)
    )
    
    # Store important questions
    db_client.store_important_questions(plan_id, important_questions)
    
    # Step 7: Store plan in PostgreSQL
    db_client.store_plan(
        plan_id=plan_id,
        username=username,
        subject=subject,
        exam_date=exam_date,
        plan_data=result['plan']
    )
    
    logger.info(f"Plan created successfully: {plan_id}")
    
    # Return response with preview
    return {
        'plan_id': plan_id,
        'summary': result.get('summary', ''),
        'next_session': result.get('next_session', {}),
        'important_questions_preview': important_questions[:5],
        'total_questions': sum(len(qs) for qs in all_questions.values()),
        'resources_indexed': len(resource_ids),
        'status': 'ready'
    }

@app.get("/api/plan/{username}/{plan_id}")
async def get_plan(username: str, plan_id: str):
    """Get study plan from PostgreSQL with ownership validation, including questions"""
    plan_row = db_client.get_plan(plan_id)
    
    if not plan_row:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # SECURITY: Validate plan ownership
    if plan_row.get('username') != username:
        raise HTTPException(status_code=403, detail="Unauthorized access to plan")
    
    # Get the plan_data field which contains the full plan
    plan = plan_row.get('plan_data', plan_row)
    
    # Convert datetime fields if present
    if 'created_at' in plan_row and plan_row['created_at']:
        plan['db_created_at'] = plan_row['created_at'].isoformat()
    
    # Add questions and important questions
    plan['questions'] = db_client.get_plan_questions(plan_id)
    plan['important_questions'] = db_client.get_important_questions(plan_id)
    
    return plan

@app.get("/api/plan/{username}/{plan_id}/important_questions")
async def get_plan_important_questions(username: str, plan_id: str):
    """Get important questions for a plan"""
    plan_row = db_client.get_plan(plan_id)
    
    if not plan_row:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # SECURITY: Validate plan ownership
    if plan_row.get('username') != username:
        raise HTTPException(status_code=403, detail="Unauthorized access to plan")
    
    important_questions = db_client.get_important_questions(plan_id)
    
    return {
        'plan_id': plan_id,
        'important_questions': important_questions,
        'count': len(important_questions)
    }

@app.get("/api/plan_status/{username}/{plan_id}")
async def get_plan_status(username: str, plan_id: str):
    """Get plan creation status (for async indexing support)"""
    plan_row = db_client.get_plan(plan_id)
    
    if not plan_row:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # SECURITY: Validate plan ownership
    if plan_row.get('username') != username:
        raise HTTPException(status_code=403, detail="Unauthorized access to plan")
    
    # For now, always return ready since we do synchronous indexing
    # Could be enhanced for async indexing in the future
    return {
        'plan_id': plan_id,
        'status': 'ready',
        'message': 'Plan ready'
    }

@app.post("/api/upload_resource")
async def upload_resource(
    username: str = Form(...),
    type: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload and index study resource with PostgreSQL storage"""
    logger.info(f"Upload request from user: {username}")
    resource_id = str(uuid.uuid4())[:8]
    filename = file.filename or "upload.txt"
    file_ext = filename.split('.')[-1] if '.' in filename else 'txt'
    file_path = f"uploads/{resource_id}.{file_ext}"
    
    # Ensure uploads directory exists
    os.makedirs("uploads", exist_ok=True)
    
    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Extract text from file
    text = extract_text(file_path, file_type=file_ext)
    
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from file")
    
    # Chunk the text
    chunks = chunk_text(text)
    logger.info(f"Created {len(chunks)} chunks from {filename}")
    
    # Store chunks and embeddings in PostgreSQL
    for chunk in chunks:
        try:
            store_chunk_embedding(
                resource_id,
                str(chunk["id"]),
                chunk["text"],
                metadata={"start": chunk["start"], "end": chunk["end"]}
            )
        except Exception as e:
            logger.error(f"Error storing chunk {chunk['id']}: {e}")
            # Continue with other chunks even if one fails
    
    # Store resource metadata in PostgreSQL
    db_client.store_resource(
        resource_id=resource_id,
        filename=filename,
        path=file_path,
        type=type,
        uploader=username,
        chunks=len(chunks)
    )
    
    logger.info(f"Successfully indexed {filename} with {len(chunks)} chunks")
    
    return {
        "resource_id": resource_id,
        "filename": filename,
        "chunks_indexed": len(chunks),
        "status": "success"
    }

@app.get("/api/resources/{username}")
async def get_resources(username: str):
    """Get all resources for user from PostgreSQL"""
    try:
        resources = db_client.get_user_resources(username)
        
        # Convert datetime objects to ISO strings for JSON serialization
        for resource in resources:
            if 'uploaded_at' in resource and resource['uploaded_at']:
                resource['uploaded_at'] = resource['uploaded_at'].isoformat()
        
        return {"resources": resources}
    except Exception as e:
        logger.error(f"Error fetching resources for {username}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching resources")

@app.post("/api/session/start")
async def start_session(request: SessionStartRequest):
    """Start learning session with AI-generated content using PostgreSQL"""
    logger.info(f"Starting session {request.session_id} for user: {request.username}")
    
    # Get plans from PostgreSQL
    plans = db_client.get_user_plans(request.username)
    session_data = None
    
    for plan_row in plans:
        plan = plan_row.get('plan_data', plan_row)
        if plan:
            for session in plan.get("sessions", []):
                if session["id"] == request.session_id:
                    session_data = session
                    break
            if session_data:
                break
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    topic = session_data["topic"]
    
    top_chunks = retrieve_top_k(topic, username=request.username, k=5)
    
    context = "\n\n".join([chunk[0][:400] for chunk in top_chunks]) if top_chunks else ""
    
    prompt = f"""Create a comprehensive study lesson for: {topic}

Context from student's materials:
{context}

Provide:
1. A clear 3-point summary
2. 2 detailed examples or practice problems
3. One practice question for the student

Format as clear sections."""
    
    messages = [
        {"role": "system", "content": "You are an expert tutor. Create engaging, educational content."},
        {"role": "user", "content": prompt}
    ]
    
    lesson_content = llm_client.chat_completion(messages, max_tokens=800)
    
    videos = find_best_videos_for_topic(topic, max_videos=2)
    
    citations = [
        {"resource_id": chunk[2], "text": chunk[0][:150], "score": round(chunk[1], 3)}
        for chunk in top_chunks
    ]
    
    return {
        "session_id": request.session_id,
        "topic": topic,
        "lesson_content": lesson_content,
        "videos": videos,
        "citations": citations,
        "resources_used": len(top_chunks)
    }

@app.post("/api/rag_query")
async def query_rag(request: RAGQueryRequest):
    """RAG-powered Q&A"""
    result = rag_query(
        request.query,
        username=request.username,
        use_only_my_materials=request.use_only_my_materials
    )
    return result

@app.post("/api/generate_quiz")
async def create_quiz(request: GenerateQuizRequest):
    """Generate quiz using AI with PostgreSQL storage"""
    logger.info(f"Generating quiz for user: {request.username}, topic: {request.topic}")
    quiz_data = generate_quiz(
        request.username,
        request.topic,
        request.num_questions,
        request.difficulty
    )
    
    # Store quiz in PostgreSQL
    db_client.store_quiz(
        quiz_id=quiz_data['quiz_id'],
        username=request.username,
        topic=request.topic,
        quiz_data=quiz_data
    )
    
    return quiz_data

@app.post("/api/submit_quiz")
async def submit_quiz(request: SubmitQuizRequest):
    """Grade quiz and update progress using PostgreSQL"""
    # Get quiz from PostgreSQL
    quiz_row = db_client.get_quiz(request.quiz_id)
    
    if not quiz_row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # SECURITY: Validate quiz ownership
    if quiz_row.get('username') != request.username:
        raise HTTPException(status_code=403, detail="Unauthorized access to quiz")
    
    quiz_data = quiz_row.get('quiz_data', quiz_row)
    
    # Grade the quiz
    result = grade_quiz(request.quiz_id, quiz_data, request.answers, request.username)
    
    # Update user XP using PostgreSQL
    db_client.update_user_xp(request.username, result["xp_earned"])
    
    # Update progress using PostgreSQL
    db_client.update_progress(
        username=request.username,
        weak_topics=result["weak_topics"],
        history_entry={
            "date": datetime.now().isoformat(),
            "action": "quiz",
            "quiz_id": request.quiz_id,
            "score": result["score"]
        }
    )
    
    # Create flashcards for incorrect answers
    for question_result in result["results"]:
        if not question_result["is_correct"]:
            quiz_questions = quiz_data.get("questions", [])
            for q in quiz_questions:
                if q.get("id") == question_result["question_id"]:
                    create_flashcard(
                        request.username,
                        q.get("stem", ""),
                        q.get("explanation", ""),
                        source=f"Quiz {request.quiz_id}"
                    )
    
    return result

@app.post("/api/generate_revision_pack")
async def create_revision_pack(request: GenerateRevisionPackRequest):
    """Generate exam revision pack"""
    logger.info(f"Revision pack requested for user: {request.username}")
    result = generate_revision_pack(request.username, request.options or {})
    return result

@app.post("/api/find_videos_for_topic")
async def find_videos(request: FindVideosRequest):
    """Find YouTube videos for topic"""
    videos = find_best_videos_for_topic(request.topic, max_videos=3)
    return {"topic": request.topic, "videos": videos}

@app.post("/api/run_due_reviews")
async def run_due_reviews(username: str):
    """Get due flashcards for review"""
    due_cards = get_due_cards(username)
    return {
        "username": username,
        "due_count": len(due_cards),
        "cards": due_cards
    }

@app.post("/api/review_card")
async def review_flashcard(request: ReviewCardRequest):
    """Review a flashcard"""
    result = review_card(request.username, request.card_id, request.quality)
    return result

@app.get("/api/progress/{username}")
async def get_progress(username: str):
    """Get user progress and analytics from PostgreSQL"""
    # Get progress from PostgreSQL
    progress = db_client.get_progress(username)
    
    # Get user from PostgreSQL
    user = db_client.get_user(username) or {}
    
    # Get quiz count from PostgreSQL
    quizzes = db_client.get_user_quizzes(username)
    total_quizzes = len(quizzes)
    
    # Convert datetime fields if needed
    history = progress.get("history", [])
    if isinstance(history, str):
        import json
        history = json.loads(history) if history else []
    
    return {
        "xp": user.get("xp", 0),
        "level": user.get("level", 1),
        "streak": user.get("streak", 0),
        "total_quizzes": total_quizzes,
        "weak_topics": progress.get("weak_topics", []),
        "completed_topics": progress.get("completed_topics", []),
        "recent_history": history[-10:] if isinstance(history, list) else []
    }

@app.post("/api/export")
async def export_data(username: str, export_type: str):
    """Export user data (plan, revision, etc.) from PostgreSQL"""
    import os
    os.makedirs("exports", exist_ok=True)
    
    if export_type == "plan":
        plans = db_client.get_user_plans(username)
        if not plans:
            raise HTTPException(status_code=404, detail="No plans found")
        
        plan_row = plans[0]
        plan = plan_row.get('plan_data', plan_row)
        
        filename = f"{username}_plan_{datetime.now().strftime('%Y%m%d')}.md"
        filepath = f"exports/{filename}"
        
        with open(filepath, 'w') as f:
            f.write(f"# Study Plan for {plan.get('subject', 'Unknown')}\n\n")
            f.write(f"**Exam Date:** {plan.get('exam_date', 'Not set')}\n\n")
            f.write(f"**Total Sessions:** {len(plan.get('sessions', []))}\n\n")
            
            for session in plan.get('sessions', []):
                f.write(f"### {session.get('topic', 'Topic')}\n")
                f.write(f"- Date: {session.get('date', '')}\n")
                f.write(f"- Duration: {session.get('duration_min', 0)} minutes\n\n")
        
        return {"download_url": f"/exports/{filename}"}
    
    raise HTTPException(status_code=400, detail="Invalid export type")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
