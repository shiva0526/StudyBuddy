import json
import uuid
from datetime import datetime
from typing import List, Dict
from backend.llm_client import llm_client
from backend.embeddings import retrieve_top_k

def generate_quiz(username: str, topic: str, num_questions: int = 5, 
                 difficulty: str = "medium") -> Dict:
    """
    Generate quiz using LLM
    Returns {quiz_id, questions: [{id, type, stem, choices, correct_index, explanation}]}
    """
    quiz_id = str(uuid.uuid4())[:8]
    
    top_chunks = retrieve_top_k(topic, username=username, k=3)
    context = "\n".join([chunk[0][:300] for chunk in top_chunks]) if top_chunks else ""
    
    prompt = f"""Generate {num_questions} multiple choice questions about: {topic}

Difficulty: {difficulty}

Context (if available):
{context}

Return a JSON object with this exact structure:
{{
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "stem": "Question text here?",
      "choices": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "Why this answer is correct"
    }}
  ]
}}

Make questions educational and clear."""
    
    messages = [
        {"role": "system", "content": "You are a quiz generator. Always return valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    response = llm_client.chat_completion(messages, temperature=0.8, max_tokens=1500)
    
    try:
        quiz_data = json.loads(response)
        questions = quiz_data.get("questions", [])
    except:
        questions = [{
            "id": 1,
            "type": "mcq",
            "stem": f"What is a key concept in {topic}?",
            "choices": ["Concept A", "Concept B", "Concept C", "Concept D"],
            "correct_index": 0,
            "explanation": "This is the correct answer"
        }]
    
    return {
        "quiz_id": quiz_id,
        "topic": topic,
        "questions": questions,
        "created_at": datetime.now().isoformat()
    }

def grade_quiz(quiz_id: str, quiz_data: Dict, answers: List[int], username: str) -> Dict:
    """
    Grade quiz answers
    Returns {score, feedback, weak_topics, xp_earned, results}
    """
    questions = quiz_data.get("questions", [])
    results = []
    correct_count = 0
    weak_topics = []
    
    for i, question in enumerate(questions):
        user_answer = answers[i] if i < len(answers) else -1
        correct_answer = question.get("correct_index", 0)
        is_correct = user_answer == correct_answer
        
        if is_correct:
            correct_count += 1
        else:
            weak_topics.append(question.get("stem", "")[:50])
        
        results.append({
            "question_id": question.get("id"),
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": question.get("explanation", "")
        })
    
    score = round((correct_count / len(questions)) * 100, 1) if questions else 0
    xp_earned = correct_count * 10
    
    feedback = []
    if score >= 90:
        feedback.append("Excellent work! You've mastered this topic.")
    elif score >= 70:
        feedback.append("Good job! Keep practicing to improve.")
    elif score >= 50:
        feedback.append("You're making progress. Review the weak areas.")
    else:
        feedback.append("Keep studying. Focus on understanding the concepts.")
    
    return {
        "score": score,
        "correct": correct_count,
        "total": len(questions),
        "feedback": feedback,
        "weak_topics": list(set(weak_topics))[:3],
        "xp_earned": xp_earned,
        "results": results
    }
