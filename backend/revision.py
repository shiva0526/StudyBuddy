import json
import uuid
from datetime import datetime
from typing import Dict, List
from backend.llm_client import llm_client
from backend.db_client import db_client
from backend.embeddings import retrieve_top_k

def generate_revision_pack(username: str, options: Dict = None) -> Dict:
    """
    Generate exam revision pack with short notes and flashcards using PostgreSQL
    Returns {revision_pack_id, short_notes, flashcards, mnemonics, download_url}
    """
    if options is None:
        options = {}
    
    max_flashcards = options.get("max_flashcards", 20)
    concise = options.get("concise", True)
    
    revision_id = str(uuid.uuid4())[:8]
    
    # Get progress from PostgreSQL
    progress = db_client.get_progress(username)
    weak_topics = progress.get("weak_topics", [])
    
    all_topics = weak_topics[:5] if weak_topics else ["General Review"]
    
    context_chunks = []
    for topic in all_topics:
        chunks = retrieve_top_k(topic, username=username, k=2)
        context_chunks.extend([c[0][:300] for c in chunks])
    
    context = "\n\n".join(context_chunks[:10]) if context_chunks else "No materials available"
    
    prompt = f"""Create a comprehensive revision pack for exam preparation.

Topics to focus on: {', '.join(all_topics)}

Context from study materials:
{context}

Generate a JSON response with:
{{
  "short_notes": ["Concise bullet point 1", "Concise bullet point 2", ...],
  "flashcards": [
    {{"front": "Question or term", "back": "Answer or definition"}},
    ...
  ],
  "mnemonics": ["Memory aid 1", "Memory aid 2", ...]
}}

Create {max_flashcards} flashcards maximum.
Short notes should be {'very concise' if concise else 'detailed'}.
Focus on the most important concepts."""
    
    messages = [
        {"role": "system", "content": "You are an expert at creating study materials. Always return valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    response = llm_client.chat_completion(messages, temperature=0.7, max_tokens=2000)
    
    try:
        revision_data = json.loads(response)
        short_notes = revision_data.get("short_notes", [])
        flashcards = revision_data.get("flashcards", [])
        mnemonics = revision_data.get("mnemonics", [])
    except:
        short_notes = ["Review key concepts", "Practice problems", "Memorize formulas"]
        flashcards = [{"front": "Key term", "back": "Definition"}]
        mnemonics = ["Use memory aids to remember better"]
    
    pack_data = {
        "revision_pack_id": revision_id,
        "username": username,
        "created_at": datetime.now().isoformat(),
        "topics": all_topics,
        "short_notes": short_notes,
        "flashcards": flashcards[:max_flashcards],
        "mnemonics": mnemonics
    }
    
    # Generate markdown export
    markdown_content = generate_markdown_export(pack_data)
    file_path = f"exports/{username}_revision_{revision_id}.md"
    
    # Ensure exports directory exists
    import os
    os.makedirs("exports", exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        download_url = f"/exports/{username}_revision_{revision_id}.md"
    except Exception as e:
        print(f"Error writing revision pack: {e}")
        download_url = None
    
    # Store in PostgreSQL
    db_client.store_revision_pack(
        pack_id=revision_id,
        username=username,
        content=pack_data,
        file_path=file_path
    )
    
    return {
        "revision_pack_id": revision_id,
        "short_notes": short_notes,
        "flashcards": flashcards,
        "mnemonics": mnemonics,
        "download_url": download_url
    }

def generate_markdown_export(pack_data: Dict) -> str:
    """Generate markdown export of revision pack"""
    md = f"# Revision Pack - {pack_data.get('created_at', '')}\n\n"
    md += f"**Topics:** {', '.join(pack_data.get('topics', []))}\n\n"
    
    md += "## Short Notes\n\n"
    for note in pack_data.get('short_notes', []):
        md += f"- {note}\n"
    
    md += "\n## Flashcards\n\n"
    for i, card in enumerate(pack_data.get('flashcards', []), 1):
        md += f"**{i}. {card.get('front', '')}**\n"
        md += f"   - {card.get('back', '')}\n\n"
    
    md += "## Memory Aids\n\n"
    for mnemonic in pack_data.get('mnemonics', []):
        md += f"- {mnemonic}\n"
    
    return md
