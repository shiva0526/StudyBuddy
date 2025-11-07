"""
Spaced repetition module using SM-2 algorithm with PostgreSQL storage.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List
import uuid
import logging
from backend.db_client import db_client

logger = logging.getLogger(__name__)


def sm2_update(card: Dict, quality: int) -> tuple:
    """
    Update flashcard using SM-2 algorithm
    quality: 0-5 (0=complete blackout, 5=perfect recall)
    Returns (easiness, interval, repetitions, due_date_str)
    """
    easiness = card.get("easiness", 2.5)
    repetitions = card.get("repetitions", 0)
    interval = card.get("interval", 1)
    
    if quality < 3:
        # Failed - reset to beginning
        repetitions = 0
        interval = 1
    else:
        # Success - increase interval
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * easiness)
        
        repetitions += 1
    
    # Update easiness factor
    easiness = max(1.3, easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    
    # Calculate next due date
    due_date = date.today() + timedelta(days=interval)
    
    return easiness, interval, repetitions, due_date.isoformat()


def create_flashcard(username: str, front: str, back: str, source: str = "") -> str:
    """Create a new flashcard in PostgreSQL and return card_id"""
    try:
        card_id = str(uuid.uuid4())[:8]
        due_date = date.today().isoformat()
        
        # Store in PostgreSQL
        db_client.create_sr_card(
            card_id=card_id,
            username=username,
            front=front,
            back=back,
            source=source,
            due_date=due_date
        )
        
        logger.info(f"Created flashcard {card_id} for user {username}")
        return card_id
        
    except Exception as e:
        logger.error(f"Error creating flashcard: {e}")
        raise


def get_due_cards(username: str) -> List[Dict]:
    """Get all flashcards due for review from PostgreSQL"""
    try:
        due_cards = db_client.get_due_cards(username)
        
        # Convert datetime objects to ISO strings
        for card in due_cards:
            if 'due_date' in card and card['due_date']:
                card['due'] = card['due_date'].isoformat()
            if 'created_at' in card and card['created_at']:
                card['created_at'] = card['created_at'].isoformat()
            if 'updated_at' in card and card['updated_at']:
                card['updated_at'] = card['updated_at'].isoformat()
        
        logger.info(f"Retrieved {len(due_cards)} due cards for {username}")
        return due_cards
        
    except Exception as e:
        logger.error(f"Error getting due cards: {e}")
        return []


def review_card(username: str, card_id: str, quality: int) -> Dict:
    """Review a flashcard and update using SM-2 algorithm in PostgreSQL"""
    try:
        # Get card from PostgreSQL
        card = db_client.get_sr_card(card_id)
        
        if not card:
            return {"error": "Card not found"}
        
        # Verify ownership
        if card.get('username') != username:
            return {"error": "Unauthorized"}
        
        # Apply SM-2 algorithm
        easiness, interval, repetitions, due_date = sm2_update(card, quality)
        
        # Update in PostgreSQL
        db_client.update_sr_card(
            card_id=card_id,
            easiness=easiness,
            interval=interval,
            repetitions=repetitions,
            due_date=due_date
        )
        
        logger.info(f"Reviewed card {card_id}, next review in {interval} days")
        
        return {
            "card_id": card_id,
            "next_review": due_date,
            "interval_days": interval,
            "quality": quality
        }
        
    except Exception as e:
        logger.error(f"Error reviewing card: {e}")
        return {"error": str(e)}
