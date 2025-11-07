"""
Embeddings module for StudyBuddy - handles vector storage and retrieval using PostgreSQL.
"""

from typing import List, Dict, Tuple
import numpy as np
import logging
from backend.llm_client import get_embedding as llm_get_embedding
from backend.db_client import db_client

logger = logging.getLogger(__name__)


def get_embedding(text: str) -> List[float]:
    """Get embedding vector for text"""
    return llm_get_embedding(text)


def store_chunk_embedding(resource_id: str, chunk_id: str, text: str, metadata: Dict = None):
    """Create and store embedding for a chunk with PostgreSQL storage"""
    try:
        # Get embedding vector
        embedding = get_embedding(text)
        
        # Store chunk in PostgreSQL
        db_client.store_chunk(
            resource_id=resource_id,
            chunk_id=str(chunk_id),
            text=text,
            start_pos=metadata.get("start", 0) if metadata else 0,
            end_pos=metadata.get("end", len(text)) if metadata else len(text),
            metadata=metadata or {}
        )
        
        # Store embedding in PostgreSQL
        db_client.store_embedding(
            resource_id=resource_id,
            chunk_id=str(chunk_id),
            vector=embedding,
            metadata={**metadata, "preview": text[:200]} if metadata else {"preview": text[:200]}
        )
        
        logger.info(f"Stored embedding for {resource_id}:{chunk_id}")
        
    except Exception as e:
        logger.error(f"Error storing chunk embedding: {e}")
        raise


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    try:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        return 0.0


def retrieve_top_k(query: str, username: str = None, k: int = 5) -> List[Tuple[str, float, str]]:
    """
    Retrieve top-k most similar chunks for a query using PostgreSQL storage.
    Returns list of (chunk_text, similarity_score, resource_id)
    """
    try:
        # Get query embedding
        query_embedding = get_embedding(query)
        
        # Retrieve all embeddings from PostgreSQL (filtered by user if specified)
        embeddings_data = db_client.get_all_embeddings(username=username)
        
        if not embeddings_data:
            logger.warning(f"No embeddings found for query: {query}")
            return []
        
        results = []
        
        for key, vector, metadata in embeddings_data:
            # Calculate similarity
            similarity = cosine_similarity(query_embedding, vector)
            
            # Extract resource_id from key
            parts = key.split(":")
            resource_id = parts[0] if parts else "unknown"
            
            # Get text from metadata
            text = metadata.get("text", metadata.get("preview", ""))
            
            results.append((text, similarity, resource_id))
        
        # Sort by similarity (descending) and return top-k
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Retrieved {len(results[:k])} chunks for query")
        return results[:k]
        
    except Exception as e:
        logger.error(f"Error retrieving top-k chunks: {e}")
        # Fallback to keyword search if embedding retrieval fails
        return keyword_fallback_search(query, username, k)


def keyword_fallback_search(query: str, username: str = None, k: int = 5) -> List[Tuple[str, float, str]]:
    """
    Fallback keyword search when embeddings are unavailable.
    Simple keyword matching with basic scoring.
    """
    try:
        logger.info(f"Using keyword fallback search for: {query}")
        
        # Get user resources if username specified
        if username:
            resources = db_client.get_user_resources(username)
        else:
            resources = db_client.get_all_resources()
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        results = []
        
        for resource in resources:
            chunks = db_client.get_resource_chunks(resource['resource_id'])
            
            for chunk in chunks:
                text = chunk.get('text', '')
                text_lower = text.lower()
                
                # Simple keyword matching score
                matches = sum(1 for word in query_words if word in text_lower)
                score = matches / len(query_words) if query_words else 0
                
                if score > 0:
                    results.append((text, score, resource['resource_id']))
        
        # Sort by score and return top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]
        
    except Exception as e:
        logger.error(f"Error in keyword fallback search: {e}")
        return []
