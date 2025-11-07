from datetime import datetime, timedelta
from typing import Dict, List
from backend.db_client import db_client

def sm2_update(card: Dict, quality: int) -> Dict:
    """
    Update flashcard using SM-2 algorithm
    quality: 0-5 (0=complete blackout, 5=perfect recall)
    Returns updated card
    """
    easiness = card.get("easiness", 2.5)
    repetitions = card.get("repetitions", 0)
    interval = card.get("interval", 1)
    
    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * easiness)
        
        repetitions += 1
    
    easiness = max(1.3, easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    
    due_date = datetime.now() + timedelta(days=interval)
    
    card.update({
        "easiness": easiness,
        "repetitions": repetitions,
        "interval": interval,
        "due": due_date.isoformat(),
        "last_reviewed": datetime.now().isoformat()
    })
    
    return card

def create_flashcard(username: str, front: str, back: str, source: str = "") -> str:
    """Create a new flashcard and return card_id"""
    import uuid
    card_id = str(uuid.uuid4())[:8]
    
    card = {
        "card_id": card_id,
        "front": front,
        "back": back,
        "source": source,
        "easiness": 2.5,
        "repetitions": 0,
        "interval": 1,
        "due": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat()
    }
    
    key = f"sr:{username}:{card_id}"
    db_client.set(key, card)
    
    return card_id

def get_due_cards(username: str) -> List[Dict]:
    """Get all flashcards due for review"""
    card_keys = db_client.keys(f"sr:{username}:")
    due_cards = []
    now = datetime.now()
    
    for key in card_keys:
        card = db_client.get(key)
        if card:
            due_date = datetime.fromisoformat(card.get("due", now.isoformat()))
            if due_date <= now:
                due_cards.append(card)
    
    return due_cards

def review_card(username: str, card_id: str, quality: int) -> Dict:
    """Review a flashcard and update using SM-2"""
    key = f"sr:{username}:{card_id}"
    card = db_client.get(key)
    
    if not card:
        return {"error": "Card not found"}
    
    updated_card = sm2_update(card, quality)
    db_client.set(key, updated_card)
    
    return {
        "card_id": card_id,
        "next_review": updated_card["due"],
        "interval_days": updated_card["interval"]
    }
