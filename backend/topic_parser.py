"""
Topic parsing utilities for StudyBuddy.
Handles CSV parsing, text parsing, and topic deduplication.
"""
import csv
import io
import logging
from typing import List, Set

logger = logging.getLogger(__name__)


def parse_topics_from_csv(file_content: bytes, filename: str) -> List[str]:
    """
    Parse topics from CSV file.
    Supports:
    - CSV with 'topic' header
    - Single-column CSV without header
    - Newline-separated .txt files
    
    Args:
        file_content: Raw file bytes
        filename: Original filename for type detection
        
    Returns:
        List of topic strings
    """
    topics = []
    
    try:
        # Decode content
        text = file_content.decode('utf-8')
        
        # Handle .txt files (newline-separated)
        if filename.endswith('.txt'):
            topics = [line.strip() for line in text.split('\n') if line.strip()]
            logger.info(f"Parsed {len(topics)} topics from TXT file")
            return topics
        
        # Handle CSV files
        reader = csv.DictReader(io.StringIO(text))
        
        # Check if 'topic' column exists
        if 'topic' in [h.lower() if h else '' for h in reader.fieldnames or []]:
            for row in reader:
                # Find the topic column (case-insensitive)
                topic_value = None
                for key, value in row.items():
                    if key and key.lower() == 'topic':
                        topic_value = value
                        break
                
                if topic_value and topic_value.strip():
                    topics.append(topic_value.strip())
        else:
            # No header, treat first column as topics
            text_io = io.StringIO(text)
            reader = csv.reader(text_io)
            
            for row in reader:
                if row and row[0].strip():
                    topics.append(row[0].strip())
        
        logger.info(f"Parsed {len(topics)} topics from CSV file")
        
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        raise ValueError(f"Failed to parse CSV file: {str(e)}")
    
    return topics


def parse_topics_from_text(text: str) -> List[str]:
    """
    Parse topics from multiline text input.
    Each line is treated as a separate topic.
    
    Args:
        text: Multiline text string
        
    Returns:
        List of topic strings
    """
    if not text:
        return []
    
    topics = [line.strip() for line in text.split('\n') if line.strip()]
    logger.info(f"Parsed {len(topics)} topics from text input")
    return topics


def merge_and_deduplicate_topics(
    typed_topics: List[str] = None,
    csv_topics: List[str] = None
) -> List[str]:
    """
    Merge topics from multiple sources and remove duplicates.
    Case-insensitive deduplication with original case preserved for first occurrence.
    
    Args:
        typed_topics: Topics entered manually
        csv_topics: Topics from CSV upload
        
    Returns:
        Deduplicated list of topics
    """
    all_topics = []
    seen_lower: Set[str] = set()
    
    # Process typed topics first (they take precedence)
    if typed_topics:
        for topic in typed_topics:
            topic_clean = topic.strip()
            if topic_clean and topic_clean.lower() not in seen_lower:
                all_topics.append(topic_clean)
                seen_lower.add(topic_clean.lower())
    
    # Process CSV topics
    if csv_topics:
        for topic in csv_topics:
            topic_clean = topic.strip()
            if topic_clean and topic_clean.lower() not in seen_lower:
                all_topics.append(topic_clean)
                seen_lower.add(topic_clean.lower())
    
    logger.info(f"Merged and deduplicated to {len(all_topics)} unique topics")
    return all_topics
