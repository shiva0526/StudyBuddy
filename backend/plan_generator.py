from datetime import datetime, timedelta
from typing import List, Dict
import uuid
import math

def generate_plan(username: str, subject: str, topics: List[str], 
                 exam_date: str, prefs: Dict) -> Dict:
    """
    Generate personalized study plan based on exam date and preferences
    Returns {plan_id, summary, sessions, next_session}
    """
    plan_id = str(uuid.uuid4())[:8]
    
    exam_dt = datetime.fromisoformat(exam_date.replace('Z', '+00:00'))
    today = datetime.now()
    days_until_exam = max(1, (exam_dt - today).days)
    
    daily_minutes = prefs.get("daily_minutes", 60)
    session_length = prefs.get("session_length", 45)
    
    total_minutes = days_until_exam * daily_minutes
    
    alpha, beta, gamma = 3, 1, 2
    topic_scores = {}
    
    for topic in topics:
        past_freq = 0.5
        note_size = 0.5
        baseline = 0.5
        
        raw_score = alpha * past_freq + beta * note_size + gamma * baseline
        topic_scores[topic] = raw_score
    
    total_score = sum(topic_scores.values())
    
    sessions = []
    session_id = 0
    current_date = today
    
    for topic, score in topic_scores.items():
        minutes_alloc = round(total_minutes * (score / total_score))
        num_sessions = max(1, math.ceil(minutes_alloc / session_length))
        
        for i in range(num_sessions):
            session_date = current_date + timedelta(days=(session_id % days_until_exam))
            
            sessions.append({
                "id": f"{plan_id}_s{session_id}",
                "topic": topic,
                "objective": f"Master {topic} - Part {i+1}/{num_sessions}",
                "date": session_date.isoformat(),
                "duration_min": session_length,
                "status": "pending",
                "resources": []
            })
            session_id += 1
    
    sessions.sort(key=lambda x: x["date"])
    
    plan = {
        "plan_id": plan_id,
        "username": username,
        "subject": subject,
        "topics": topics,
        "exam_date": exam_date,
        "created_at": today.isoformat(),
        "sessions": sessions,
        "meta": {
            "total_sessions": len(sessions),
            "days_until_exam": days_until_exam,
            "total_study_hours": round(total_minutes / 60, 1)
        }
    }
    
    next_session = sessions[0] if sessions else None
    
    return {
        "plan_id": plan_id,
        "summary": f"Created {len(sessions)} study sessions over {days_until_exam} days for {subject}",
        "plan": plan,
        "next_session": next_session
    }
