"""
Question generation module for StudyBuddy.
Generates practice questions per topic and ranks important questions for exam prep.
"""
import json
import logging
from typing import List, Dict, Tuple
from collections import Counter
import re

logger = logging.getLogger(__name__)


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks"""
    try:
        # Try direct JSON parse first
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to find any JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        logger.error(f"No JSON found in response: {text[:200]}")
        return {}


def generate_topic_questions(
    llm_client,
    topic: str,
    context_chunks: List[str],
    num_questions: int = 5
) -> List[Dict]:
    """
    Generate practice questions for a specific topic using LLM.
    
    Args:
        llm_client: LLM client instance
        topic: Topic name
        context_chunks: Relevant text snippets from notes/papers
        num_questions: Number of questions to generate
        
    Returns:
        List of question objects
    """
    # Build context from chunks (limit to top 3 for prompt size)
    context_text = "\n\n".join([f"Snippet {i+1}: {chunk[:500]}" 
                                for i, chunk in enumerate(context_chunks[:3])])
    
    prompt = f"""You are StudyBuddy, an expert exam tutor. Given the topic name and the following context snippets from the student's notes and past papers, generate {num_questions} practice questions for the topic.

Topic: {topic}

Context:
{context_text}

For each question output a JSON object with fields:
{{
  "id": "<unique id like q1, q2, etc>",
  "type": "mcq" | "short",
  "stem": "Question text",
  "choices": ["A","B","C","D"],  // only for mcq
  "answer_index": 1,  // only for mcq (0-indexed)
  "model_answer": "full answer for short questions",
  "explanation": "short explanation"
}}

Return the entire payload as valid JSON: {{"topic":"{topic}","questions":[...]}}

Generate exactly {num_questions} questions. Mix MCQ and short-answer types."""
    
    try:
        response = llm_client.generate_completion(prompt)
        logger.info(f"LLM response for topic '{topic}': {response[:200]}")
        
        # Parse JSON from response
        data = extract_json_from_response(response)
        
        questions = data.get('questions', [])
        
        # Validate and clean questions
        validated_questions = []
        for q in questions:
            if 'stem' in q and 'type' in q:
                validated_questions.append(q)
        
        logger.info(f"Generated {len(validated_questions)} questions for topic '{topic}'")
        return validated_questions
        
    except Exception as e:
        logger.error(f"Error generating questions for topic '{topic}': {e}")
        # Return mock questions as fallback
        return generate_mock_questions(topic, num_questions)


def generate_mock_questions(topic: str, num_questions: int = 5) -> List[Dict]:
    """Generate mock questions for testing/fallback"""
    questions = []
    for i in range(num_questions):
        if i % 2 == 0:
            # MCQ
            questions.append({
                "id": f"q{i+1}",
                "type": "mcq",
                "stem": f"Sample MCQ question about {topic}?",
                "choices": ["Option A", "Option B", "Option C", "Option D"],
                "answer_index": 0,
                "explanation": "This is a sample question for testing."
            })
        else:
            # Short answer
            questions.append({
                "id": f"q{i+1}",
                "type": "short",
                "stem": f"Explain the key concept in {topic}.",
                "model_answer": f"Sample answer about {topic}.",
                "explanation": "This is a sample question for testing."
            })
    return questions


def compute_topic_frequency(
    topic: str,
    resource_chunks: Dict[str, List[Dict]]
) -> float:
    """
    Compute frequency score for a topic based on past paper mentions.
    
    Args:
        topic: Topic name
        resource_chunks: Dictionary mapping resource_id to chunks
        
    Returns:
        Frequency score (0-1 normalized)
    """
    topic_lower = topic.lower()
    mentions = 0
    total_chunks = 0
    
    for resource_id, chunks in resource_chunks.items():
        for chunk in chunks:
            total_chunks += 1
            chunk_text = chunk.get('text', '').lower()
            if topic_lower in chunk_text:
                mentions += 1
    
    if total_chunks == 0:
        return 0.0
    
    return min(mentions / max(total_chunks / 10, 1), 1.0)  # Normalize


def generate_important_questions(
    llm_client,
    topics: List[str],
    all_questions: Dict[str, List[Dict]],
    topic_frequencies: Dict[str, float],
    top_n: int = 10
) -> List[Dict]:
    """
    Generate ranked list of important questions for exam prep.
    
    Args:
        llm_client: LLM client instance
        topics: List of all topics
        all_questions: All generated questions by topic
        topic_frequencies: Frequency scores per topic
        top_n: Number of important questions to select
        
    Returns:
        List of important question objects with rankings
    """
    # Build prompt with topic summary
    topic_summary = "\n".join([
        f"- {topic} (frequency: {topic_frequencies.get(topic, 0.0):.2f})"
        for topic in topics
    ])
    
    # Sample questions from each topic
    sample_questions = []
    for topic, questions in all_questions.items():
        for q in questions[:2]:  # Top 2 per topic
            sample_questions.append({
                'topic': topic,
                'stem': q['stem'],
                'freq': topic_frequencies.get(topic, 0.0)
            })
    
    questions_text = "\n\n".join([
        f"Topic: {q['topic']} (freq: {q['freq']:.2f})\nQ: {q['stem']}"
        for q in sample_questions[:20]  # Limit for prompt size
    ])
    
    prompt = f"""You are StudyBuddy. Using the combined input: topics list, sample questions from practice sets, and topic frequency scores (based on past paper analysis), return a JSON array of the top {top_n} "Important Questions" students should practice before the exam.

Topics:
{topic_summary}

Sample Questions:
{questions_text}

For each item return:
{{
  "q_id": "unique_id",
  "topic": "topic name",
  "stem": "question text",
  "importance_score": 0.0-1.0,
  "reason": "one-line justification",
  "source": "generated"
}}

Return exactly {top_n} questions as a JSON array: [{{"q_id": "...", ...}}]

Prioritize questions from high-frequency topics and questions that test core concepts."""
    
    try:
        response = llm_client.generate_completion(prompt)
        logger.info(f"LLM response for important questions: {response[:200]}")
        
        # Parse JSON array from response
        data = extract_json_from_response(response)
        
        # Handle both array and object with 'questions' field
        if isinstance(data, list):
            important_qs = data
        elif isinstance(data, dict) and 'questions' in data:
            important_qs = data['questions']
        else:
            important_qs = []
        
        # Validate
        validated = []
        for q in important_qs:
            if 'topic' in q and 'stem' in q:
                validated.append(q)
        
        logger.info(f"Generated {len(validated)} important questions")
        return validated[:top_n]
        
    except Exception as e:
        logger.error(f"Error generating important questions: {e}")
        # Fallback: select top questions based on frequency
        return select_important_questions_heuristic(
            all_questions, topic_frequencies, top_n
        )


def select_important_questions_heuristic(
    all_questions: Dict[str, List[Dict]],
    topic_frequencies: Dict[str, float],
    top_n: int = 10
) -> List[Dict]:
    """
    Heuristic selection of important questions based on topic frequency.
    Fallback when LLM is unavailable.
    """
    ranked_questions = []
    
    for topic, questions in all_questions.items():
        freq = topic_frequencies.get(topic, 0.0)
        
        for i, q in enumerate(questions):
            # Score = frequency + question position (first questions are often more important)
            score = freq + (len(questions) - i) / (len(questions) * 10)
            
            ranked_questions.append({
                'q_id': f"{topic}_{q.get('id', i)}",
                'topic': topic,
                'stem': q['stem'],
                'importance_score': round(score, 2),
                'reason': f"High-frequency topic ({freq:.2f})",
                'source': 'generated'
            })
    
    # Sort by score and take top N
    ranked_questions.sort(key=lambda x: x['importance_score'], reverse=True)
    
    logger.info(f"Selected {min(top_n, len(ranked_questions))} important questions via heuristic")
    return ranked_questions[:top_n]
