from typing import List, Dict
from backend.embeddings import retrieve_top_k
from backend.llm_client import llm_client

def rag_query(query: str, username: str = None, use_only_my_materials: bool = False) -> Dict:
    """
    RAG query: retrieve relevant chunks and generate answer
    Returns {answer, citations, used_chunks}
    """
    k = 5
    if use_only_my_materials and not username:
        return {
            "answer": "Cannot use 'my materials only' without username",
            "citations": [],
            "used_chunks": []
        }
    
    search_username = username if use_only_my_materials else None
    top_chunks = retrieve_top_k(query, username=search_username, k=k)
    
    if not top_chunks:
        return {
            "answer": "No relevant materials found. Please upload study materials first.",
            "citations": [],
            "used_chunks": []
        }
    
    context = "\n\n".join([
        f"[Source {i+1}]: {chunk[0][:500]}"
        for i, chunk in enumerate(top_chunks)
    ])
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful study tutor. Answer questions based on the provided context. Always cite your sources using [Source N] notation."
        },
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}\n\nProvide a clear answer with citations."
        }
    ]
    
    answer = llm_client.chat_completion(messages, max_tokens=500)
    
    citations = [
        {
            "source_id": i+1,
            "text": chunk[0][:200],
            "similarity": round(chunk[1], 3),
            "resource_id": chunk[2]
        }
        for i, chunk in enumerate(top_chunks)
    ]
    
    return {
        "answer": answer,
        "citations": citations,
        "used_chunks": len(top_chunks)
    }
