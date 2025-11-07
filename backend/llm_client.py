import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI

class LLMClient:
    """OpenAI LLM client with fallback for missing API key"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.mock_mode = False
        
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                print("✓ OpenAI client initialized")
            except Exception as e:
                print(f"Warning: OpenAI init failed: {e}")
                self.mock_mode = True
        else:
            print("Warning: OPENAI_API_KEY not set, using mock mode")
            self.mock_mode = True
    
    def chat_completion(self, messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 1000,
                       response_format: Optional[Dict] = None) -> str:
        """Get chat completion from OpenAI or mock"""
        if self.mock_mode or not self.client:
            return self._mock_completion(messages)
        
        try:
            kwargs = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if response_format:
                kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM error: {e}")
            return self._mock_completion(messages)
    
    def get_embedding(self, text: str) -> List[float]:
        """Get text embedding from OpenAI or mock"""
        if self.mock_mode or not self.client:
            return self._mock_embedding(text)
        
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return self._mock_embedding(text)
    
    def _mock_completion(self, messages: List[Dict[str, str]]) -> str:
        """Mock completion for testing without API key"""
        last_msg = messages[-1].get("content", "")
        
        if "quiz" in last_msg.lower():
            return json.dumps({
                "questions": [
                    {
                        "id": 1,
                        "type": "mcq",
                        "stem": "What is the derivative of x²?",
                        "choices": ["x", "2x", "x³", "2"],
                        "correct_index": 1,
                        "explanation": "Using the power rule: d/dx(x²) = 2x"
                    }
                ]
            })
        elif "revision" in last_msg.lower() or "flashcard" in last_msg.lower():
            return json.dumps({
                "short_notes": ["Key concept 1: Important definition", "Key concept 2: Main formula"],
                "flashcards": [{"front": "What is calculus?", "back": "The study of continuous change"}],
                "mnemonics": ["SOH-CAH-TOA for trigonometry"]
            })
        elif "summary" in last_msg.lower() or "lesson" in last_msg.lower():
            return "This is a comprehensive summary of the topic with key concepts and examples."
        else:
            return "This is a mock AI response. Set OPENAI_API_KEY for real completions."
    
    def _mock_embedding(self, text: str) -> List[float]:
        """Mock embedding (1536-dim for compatibility)"""
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        import random
        random.seed(hash_val)
        return [random.random() for _ in range(1536)]

llm_client = LLMClient()
