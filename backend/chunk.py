from typing import List, Dict

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, any]]:
    """
    Chunk text into overlapping segments
    Returns list of dicts with {id, text, start, end}
    """
    if not text:
        return []
    
    chunks = []
    chunk_id = 0
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk_text_content = text[start:end]
        
        if chunk_text_content.strip():
            chunks.append({
                "id": chunk_id,
                "text": chunk_text_content,
                "start": start,
                "end": end
            })
            chunk_id += 1
        
        start += (chunk_size - overlap)
    
    return chunks
