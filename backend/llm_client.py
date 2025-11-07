"""
LLM Helper Module for StudyBuddy

Provides an abstraction layer for OpenAI API calls with automatic fallback to
deterministic mock responses when OPENAI_API_KEY is not available. 

Features:
- Real OpenAI API calls with exponential backoff retry logic
- Deterministic mock responses for testing without API costs
- JSON extraction and parsing utilities
- Comprehensive logging for debugging and monitoring
"""

import os
import json
import time
import hashlib
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def is_api_available() -> bool:
    """
    Check if OpenAI API key is available.
    
    Returns:
        bool: True if OPENAI_API_KEY environment variable is set and non-empty
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    return bool(api_key and api_key.strip())


def get_embedding(text: str) -> List[float]:
    """
    Get text embedding vector from OpenAI or deterministic mock.
    
    Args:
        text: Input text to embed
        
    Returns:
        List[float]: Embedding vector (1536 dimensions for text-embedding-3-small)
    """
    start_time = time.time()
    
    if is_api_available():
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # Retry logic: 2 retries with exponential backoff
            for attempt in range(3):
                try:
                    model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
                    response = client.embeddings.create(
                        model=model,
                        input=text
                    )
                    embedding = response.data[0].embedding
                    latency = time.time() - start_time
                    logger.info(f"Embedding API call succeeded (attempt {attempt + 1}, {latency:.2f}s)")
                    return embedding
                except Exception as e:
                    if attempt < 2:
                        wait_time = 2 ** attempt
                        logger.warning(f"Embedding attempt {attempt + 1} failed: {e}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Embedding API failed after 3 attempts: {e}")
                        raise
        except Exception as e:
            logger.warning(f"Falling back to mock embedding due to error: {e}")
            return _mock_embedding(text)
    else:
        logger.info("Using mock embedding (no API key)")
        return _mock_embedding(text)


def _mock_embedding(text: str) -> List[float]:
    """
    Generate deterministic mock embedding from text hash.
    
    Creates a 1536-dimensional vector by repeatedly hashing the input text
    and converting bytes to normalized floats.
    
    Args:
        text: Input text
        
    Returns:
        List[float]: Deterministic 1536-dim vector
    """
    dimension = 1536
    vector = []
    
    # Generate deterministic values from repeated hashing
    seed = text.encode('utf-8')
    for i in range(dimension):
        hash_input = seed + str(i).encode('utf-8')
        hash_bytes = hashlib.sha256(hash_input).digest()
        # Convert first 8 bytes to float and normalize to [-1, 1]
        value = int.from_bytes(hash_bytes[:8], 'big') / (2 ** 64)
        vector.append(value * 2 - 1)
    
    # Normalize to unit length for cosine similarity
    magnitude = sum(v ** 2 for v in vector) ** 0.5
    if magnitude > 0:
        vector = [v / magnitude for v in vector]
    
    return vector


def safe_json_from_text(text: str) -> Any:
    """
    Extract and parse JSON from LLM response text.
    
    Handles cases where JSON is wrapped in markdown code blocks or
    has extraneous text before/after.
    
    Args:
        text: Raw LLM response text
        
    Returns:
        Parsed JSON object or None if parsing fails
    """
    if not text:
        return None
    
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try extracting from code blocks
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass
    
    # Try extracting from generic code blocks
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass
    
    # Try finding JSON object boundaries
    for start_char in ['{', '[']:
        start_idx = text.find(start_char)
        if start_idx != -1:
            # Find matching closing bracket
            end_char = '}' if start_char == '{' else ']'
            bracket_count = 0
            for i in range(start_idx, len(text)):
                if text[i] == start_char:
                    bracket_count += 1
                elif text[i] == end_char:
                    bracket_count -= 1
                    if bracket_count == 0:
                        try:
                            return json.loads(text[start_idx:i + 1])
                        except json.JSONDecodeError:
                            break
    
    logger.warning("Failed to extract JSON from text")
    return None


def generate_completion(prompt: str, mode: str = "chat", structured: bool = False) -> Any:
    """
    Generate LLM completion with retry logic and structured output support.
    
    Args:
        prompt: Text prompt for the LLM
        mode: One of "chat", "plan", "quiz", "session", "grade", "revision"
        structured: If True, return parsed JSON object instead of raw text
        
    Returns:
        String response or parsed JSON object (depending on structured flag)
    """
    start_time = time.time()
    
    if is_api_available():
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # Retry logic: 2 retries with exponential backoff
            for attempt in range(3):
                try:
                    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
                    
                    # Build messages
                    messages = [
                        {"role": "system", "content": _get_system_prompt(mode)},
                        {"role": "user", "content": prompt}
                    ]
                    
                    # Create completion
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2000
                    )
                    
                    content = response.choices[0].message.content
                    latency = time.time() - start_time
                    logger.info(f"LLM completion succeeded (mode={mode}, attempt={attempt + 1}, {latency:.2f}s)")
                    
                    if structured:
                        parsed = safe_json_from_text(content)
                        if parsed is None:
                            logger.error(f"Failed to parse JSON from LLM response in mode={mode}")
                            return _mock_completion(mode, structured=True)
                        return parsed
                    
                    return content
                    
                except Exception as e:
                    if attempt < 2:
                        wait_time = 2 ** attempt
                        logger.warning(f"LLM attempt {attempt + 1} failed: {e}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"LLM API failed after 3 attempts: {e}")
                        raise
                        
        except Exception as e:
            logger.warning(f"Falling back to mock completion due to error: {e}")
            return _mock_completion(mode, structured)
    else:
        logger.info(f"Using mock completion (mode={mode}, no API key)")
        return _mock_completion(mode, structured)


def _get_system_prompt(mode: str) -> str:
    """Get appropriate system prompt for each mode."""
    prompts = {
        "plan": "You are a study planning assistant. Generate structured study plans with sessions.",
        "session": "You are an expert tutor. Create clear, educational lesson content.",
        "quiz": "You are a quiz generator. Create valid MCQ questions in JSON format.",
        "grade": "You are a grading assistant. Provide constructive feedback on answers.",
        "revision": "You are a revision materials creator. Generate concise notes and flashcards.",
        "chat": "You are a helpful AI assistant for students."
    }
    return prompts.get(mode, prompts["chat"])


def _mock_completion(mode: str, structured: bool = False) -> Any:
    """
    Generate deterministic mock responses for testing.
    
    Args:
        mode: Response mode
        structured: Return parsed object if True
        
    Returns:
        Mock response appropriate for the mode
    """
    responses = {
        "plan": {
            "plan_id": "plan-demo",
            "summary": "Demo 7-day plan generated in mock mode",
            "sessions": [
                {
                    "id": "s1",
                    "topic": "Introduction to the subject",
                    "date": "2025-11-10",
                    "duration_min": 45
                },
                {
                    "id": "s2",
                    "topic": "Advanced concepts",
                    "date": "2025-11-11",
                    "duration_min": 45
                }
            ],
            "next_session": {
                "id": "s1",
                "topic": "Introduction to the subject",
                "date": "2025-11-10",
                "duration_min": 45
            }
        },
        "session": {
            "summary": "Demo summary: This topic covers key concepts A, B, and C with practical applications.",
            "examples": [
                "Example 1: Demonstrating the basic principle",
                "Example 2: Advanced application of the concept"
            ],
            "practice_question": {
                "id": "q1",
                "type": "mcq",
                "stem": "Which of the following best describes this concept?",
                "choices": ["Option A", "Option B", "Option C", "Option D"],
                "answer_index": 1
            },
            "citations": []
        },
        "quiz": {
            "quiz_id": "quiz-demo",
            "questions": [
                {
                    "id": 1,
                    "type": "mcq",
                    "stem": "What is 2 + 2?",
                    "choices": ["3", "4", "5", "6"],
                    "correct_index": 1,
                    "explanation": "Basic arithmetic: 2 + 2 = 4"
                },
                {
                    "id": 2,
                    "type": "mcq",
                    "stem": "Which is a primary color?",
                    "choices": ["Green", "Red", "Purple", "Orange"],
                    "correct_index": 1,
                    "explanation": "Red is a primary color along with blue and yellow"
                },
                {
                    "id": 3,
                    "type": "mcq",
                    "stem": "What is the capital of France?",
                    "choices": ["London", "Berlin", "Paris", "Madrid"],
                    "correct_index": 2,
                    "explanation": "Paris is the capital city of France"
                }
            ]
        },
        "grade": {
            "score": 3,
            "max_score": 5,
            "feedback": "Demo feedback: Good effort! Remember to review the key concepts and practice more problems."
        },
        "revision": {
            "short_notes": [
                {
                    "topic": "Key Concept 1",
                    "points": [
                        "Important definition and core principle",
                        "Main formula or relationship",
                        "Common applications"
                    ]
                },
                {
                    "topic": "Key Concept 2",
                    "points": [
                        "Secondary principle",
                        "Related theorems"
                    ]
                }
            ],
            "flashcards": [
                {
                    "question": "What is the main principle?",
                    "answer": "The core concept that defines the foundation"
                },
                {
                    "question": "How do you apply this?",
                    "answer": "Follow the step-by-step procedure outlined"
                }
            ],
            "mnemonics": ["SAMPLE: Simple Acronym for Memory Practice Learning Example"]
        },
        "chat": "Demo reply: I'm running in mock mode. Set OPENAI_API_KEY to enable real AI responses."
    }
    
    response = responses.get(mode, responses["chat"])
    
    if structured and isinstance(response, dict):
        return response
    elif structured:
        return {"message": response}
    elif isinstance(response, dict):
        return json.dumps(response, indent=2)
    else:
        return response


class LLMClient:
    """Legacy compatibility wrapper for existing code."""
    
    def __init__(self):
        self.mock_mode = not is_api_available()
        if not self.mock_mode:
            logger.info("✓ OpenAI client initialized")
        else:
            logger.info("Running in mock mode (no OPENAI_API_KEY)")
    
    def chat_completion(self, messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 1000,
                       response_format: Optional[Dict] = None) -> str:
        """Legacy method for chat completion."""
        # Extract user message
        user_msg = messages[-1].get("content", "") if messages else ""
        
        # Determine mode from content
        mode = "chat"
        if "quiz" in user_msg.lower():
            mode = "quiz"
        elif "revision" in user_msg.lower() or "flashcard" in user_msg.lower():
            mode = "revision"
        elif "plan" in user_msg.lower():
            mode = "plan"
        elif "grade" in user_msg.lower():
            mode = "grade"
        
        structured = response_format is not None
        return generate_completion(user_msg, mode=mode, structured=structured)
    
    def get_embedding(self, text: str) -> List[float]:
        """Legacy method for embeddings."""
        return get_embedding(text)


# Singleton instance for backwards compatibility
llm_client = LLMClient()


if __name__ == "__main__":
    """Quick manual test suite"""
    print("=== LLM Client Test Suite ===\n")
    
    print(f"1. API Available: {is_api_available()}")
    print()
    
    print("2. Testing embedding:")
    embedding = get_embedding("hello world")
    print(f"   Embedding dimension: {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")
    print()
    
    print("3. Testing completion modes:")
    for mode in ["plan", "session", "quiz", "grade", "revision", "chat"]:
        result = generate_completion(f"Generate a test {mode}", mode=mode, structured=True)
        print(f"   {mode}: {type(result).__name__} - {str(result)[:80]}...")
    print()
    
    print("4. JSON extraction test:")
    test_text = '```json\n{"test": "value"}\n```'
    parsed = safe_json_from_text(test_text)
    print(f"   Extracted: {parsed}")
    print()
    
    print("=== Tests Complete ===")
