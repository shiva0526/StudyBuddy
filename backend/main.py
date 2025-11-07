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
    """Get or create user profile"""
    user_key = f"user:{username}"
    user = db_client.get(user_key)
    
    if not user:
        user = {
            "username": username,
            "name": username,
            "prefs": {
                "daily_minutes": 60,
                "session_length": 45,
                "preferred_times": ["morning", "evening"]
            },
            "xp": 0,
            "level": 1,
            "streak": 0,
            "created_at": datetime.now().isoformat()
        }
        db_client.set(user_key, user)
    
    return user

@app.post("/api/create_plan")
async def create_plan(request: CreatePlanRequest):
    """Create personalized study plan"""
    logger.info(f"Creating study plan for user: {request.username}, subject: {request.subject}")
    result = generate_plan(
        request.username,
        request.subject,
        request.topics,
        request.exam_date,
        request.prefs
    )
    
    plan_key = f"plan:{request.username}:{result['plan_id']}"
    db_client.set(plan_key, result['plan'])
    
    return result

@app.get("/api/plan/{username}/{plan_id}")
async def get_plan(username: str, plan_id: str):
    """Get study plan"""
    plan_key = f"plan:{username}:{plan_id}"
    plan = db_client.get(plan_key)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return plan

@app.post("/api/upload_resource")
async def upload_resource(
    username: str = Form(...),
    type: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload and index study resource"""
    logger.info(f"Upload request from user: {username}")
    resource_id = str(uuid.uuid4())[:8]
    filename = file.filename or "upload.txt"
    file_ext = filename.split('.')[-1] if '.' in filename else 'txt'
    file_path = f"uploads/{resource_id}.{file_ext}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    text = extract_text(file_path, file_type=file_ext)
    
    chunks = chunk_text(text)
    
    for chunk in chunks:
        store_chunk_embedding(
            resource_id,
            chunk["id"],
            chunk["text"],
            metadata={"start": chunk["start"], "end": chunk["end"]}
        )
    
    resource_key = f"resource:{resource_id}"
    db_client.set(resource_key, {
        "resource_id": resource_id,
        "filename": file.filename,
        "path": file_path,
        "type": type,
        "uploader": username,
        "indexed": True,
        "chunks": len(chunks),
        "uploaded_at": datetime.now().isoformat()
    })
    
    return {
        "resource_id": resource_id,
        "filename": file.filename,
        "chunks_indexed": len(chunks),
        "status": "success"
    }

@app.get("/api/resources/{username}")
async def get_resources(username: str):
    """Get all resources for user"""
    resource_keys = db_client.keys("resource:")
    resources = []
    
    for key in resource_keys:
        resource = db_client.get(key)
        if resource and resource.get("uploader") == username:
            resources.append(resource)
    
    return {"resources": resources}

@app.post("/api/session/start")
async def start_session(request: SessionStartRequest):
    """Start learning session with AI-generated content"""
    logger.info(f"Starting session {request.session_id} for user: {request.username}")
    plan_keys = db_client.keys(f"plan:{request.username}:")
    session_data = None
    
    for plan_key in plan_keys:
        plan = db_client.get(plan_key)
        if plan:
            for session in plan.get("sessions", []):
                if session["id"] == request.session_id:
                    session_data = session
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
    """Generate quiz using AI"""
    logger.info(f"Generating quiz for user: {request.username}, topic: {request.topic}")
    quiz_data = generate_quiz(
        request.username,
        request.topic,
        request.num_questions,
        request.difficulty
    )
    
    quiz_key = f"quiz:{request.username}:{quiz_data['quiz_id']}"
    db_client.set(quiz_key, quiz_data)
    
    return quiz_data

@app.post("/api/submit_quiz")
async def submit_quiz(request: SubmitQuizRequest):
    """Grade quiz and update progress"""
    quiz_key = f"quiz:{request.username}:{request.quiz_id}"
    quiz_data = db_client.get(quiz_key)
    
    if not quiz_data:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    result = grade_quiz(request.quiz_id, quiz_data, request.answers, request.username)
    
    user_key = f"user:{request.username}"
    user = db_client.get(user_key)
    if user:
        user["xp"] = user.get("xp", 0) + result["xp_earned"]
        user["level"] = 1 + (user["xp"] // 100)
        db_client.set(user_key, user)
    
    progress_key = f"progress:{request.username}"
    progress = db_client.get(progress_key) or {"completed_topics": [], "weak_topics": [], "history": []}
    
    progress["weak_topics"] = list(set(progress.get("weak_topics", []) + result["weak_topics"]))[:10]
    progress["history"].append({
        "date": datetime.now().isoformat(),
        "action": "quiz",
        "quiz_id": request.quiz_id,
        "score": result["score"]
    })
    
    db_client.set(progress_key, progress)
    
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
    """Get user progress and analytics"""
    progress_key = f"progress:{username}"
    progress = db_client.get(progress_key) or {
        "completed_topics": [],
        "weak_topics": [],
        "history": []
    }
    
    user_key = f"user:{username}"
    user = db_client.get(user_key) or {}
    
    quiz_keys = db_client.keys(f"quiz:{username}:")
    total_quizzes = len(quiz_keys)
    
    return {
        "xp": user.get("xp", 0),
        "level": user.get("level", 1),
        "streak": user.get("streak", 0),
        "total_quizzes": total_quizzes,
        "weak_topics": progress.get("weak_topics", []),
        "completed_topics": progress.get("completed_topics", []),
        "recent_history": progress.get("history", [])[-10:]
    }

@app.post("/api/export")
async def export_data(username: str, export_type: str):
    """Export user data (plan, revision, etc.)"""
    if export_type == "plan":
        plan_keys = db_client.keys(f"plan:{username}:")
        if not plan_keys:
            raise HTTPException(status_code=404, detail="No plans found")
        
        plan = db_client.get(plan_keys[0])
        if not plan:
            raise HTTPException(status_code=404, detail="Plan data not found")
        
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
