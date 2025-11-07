from typing import List, Dict, Tuple
import numpy as np
from backend.llm_client import llm_client
from backend.db_client import db_client

def get_embedding(text: str) -> List[float]:
    """Get embedding vector for text"""
    return llm_client.get_embedding(text)

def store_chunk_embedding(resource_id: str, chunk_id: int, text: str, metadata: Dict = None):
    """Create and store embedding for a chunk"""
    embedding = get_embedding(text)
    
    embed_key = f"embed:{resource_id}:{chunk_id}"
    db_client.set(embed_key, {
        "vector": embedding,
        "metadata": metadata or {},
        "text": text[:200]
    })
    
    chunk_key = f"chunk:{resource_id}:{chunk_id}"
    db_client.set(chunk_key, {
        "text": text,
        "start": metadata.get("start", 0) if metadata else 0,
        "end": metadata.get("end", len(text)) if metadata else len(text)
    })

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))

def retrieve_top_k(query: str, username: str = None, k: int = 5) -> List[Tuple[str, float, str]]:
    """
    Retrieve top-k most similar chunks for a query
    Returns list of (chunk_text, similarity_score, resource_id)
    """
    query_embedding = get_embedding(query)
    
    if username:
        embed_keys = db_client.keys(f"embed:")
        user_resources = db_client.keys(f"resource:")
        user_resource_ids = [key.split(":")[-1] for key in user_resources 
                            if db_client.get(key) and db_client.get(key).get("uploader") == username]
        embed_keys = [key for key in embed_keys 
                     if any(rid in key for rid in user_resource_ids)]
    else:
        embed_keys = db_client.keys(f"embed:")
    
    results = []
    
    for embed_key in embed_keys:
        embed_data = db_client.get(embed_key)
        if not embed_data or "vector" not in embed_data:
            continue
        
        similarity = cosine_similarity(query_embedding, embed_data["vector"])
        
        parts = embed_key.split(":")
        if len(parts) >= 3:
            resource_id = parts[1]
            chunk_id = parts[2]
            chunk_key = f"chunk:{resource_id}:{chunk_id}"
            chunk_data = db_client.get(chunk_key)
            
            if chunk_data:
                results.append((
                    chunk_data.get("text", ""),
                    similarity,
                    resource_id
                ))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:k]
