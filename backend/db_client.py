"""
PostgreSQL database client for StudyBuddy with proper schema and storage.

Uses PostgreSQL for permanent data storage with tables for users, resources,
chunks, embeddings, plans, quizzes, and spaced repetition cards.
"""

import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import Any, Optional, List, Dict, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PostgreSQLClient:
    """PostgreSQL database client with schema management"""
    
    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL environment variable not set")
        
        self._init_schema()
        logger.info("✓ PostgreSQL client initialized")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize database schema with all required tables"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Users table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        username VARCHAR(255) PRIMARY KEY,
                        name VARCHAR(255),
                        prefs JSONB DEFAULT '{}',
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        streak INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Resources table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS resources (
                        resource_id VARCHAR(255) PRIMARY KEY,
                        filename VARCHAR(512),
                        path VARCHAR(1024),
                        type VARCHAR(50),
                        uploader VARCHAR(255),
                        indexed BOOLEAN DEFAULT FALSE,
                        chunks INTEGER DEFAULT 0,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Chunks table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS chunks (
                        id SERIAL PRIMARY KEY,
                        resource_id VARCHAR(255) REFERENCES resources(resource_id) ON DELETE CASCADE,
                        chunk_id VARCHAR(255),
                        text TEXT,
                        start_pos INTEGER,
                        end_pos INTEGER,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(resource_id, chunk_id)
                    )
                """)
                
                # Embeddings table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id SERIAL PRIMARY KEY,
                        resource_id VARCHAR(255),
                        chunk_id VARCHAR(255),
                        vector JSONB,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(resource_id, chunk_id)
                    )
                """)
                
                # Plans table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS plans (
                        plan_id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255),
                        subject VARCHAR(255),
                        exam_date DATE,
                        plan_data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Quizzes table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS quizzes (
                        quiz_id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255),
                        topic VARCHAR(255),
                        quiz_data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Progress table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS progress (
                        username VARCHAR(255) PRIMARY KEY,
                        completed_topics JSONB DEFAULT '[]',
                        weak_topics JSONB DEFAULT '[]',
                        history JSONB DEFAULT '[]',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Spaced repetition cards table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sr_cards (
                        card_id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255),
                        front TEXT,
                        back TEXT,
                        source VARCHAR(255),
                        easiness FLOAT DEFAULT 2.5,
                        interval INTEGER DEFAULT 1,
                        repetitions INTEGER DEFAULT 0,
                        due_date DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Revision packs table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS revision_packs (
                        pack_id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255),
                        content JSONB,
                        file_path VARCHAR(1024),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Plan questions table (generated practice questions per topic)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS plan_questions (
                        id SERIAL PRIMARY KEY,
                        plan_id VARCHAR(255),
                        topic VARCHAR(255),
                        questions JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(plan_id, topic)
                    )
                """)
                
                # Plan important questions table (top questions for exam prep)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS plan_important_questions (
                        id SERIAL PRIMARY KEY,
                        plan_id VARCHAR(255) UNIQUE,
                        questions JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                logger.info("Database schema initialized")
    
    # User operations
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cur.fetchone()
                return dict(row) if row else None
    
    def create_user(self, username: str, name: str, prefs: Dict = None) -> Dict:
        """Create a new user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO users (username, name, prefs)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO UPDATE SET name = EXCLUDED.name
                    RETURNING *
                """, (username, name, Json(prefs or {})))
                return dict(cur.fetchone())
    
    def update_user_xp(self, username: str, xp_delta: int) -> None:
        """Update user XP and level"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users 
                    SET xp = xp + %s, level = 1 + ((xp + %s) / 100)
                    WHERE username = %s
                """, (xp_delta, xp_delta, username))
    
    # Resource operations
    def store_resource(self, resource_id: str, filename: str, path: str, 
                      type: str, uploader: str, chunks: int) -> None:
        """Store resource metadata"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO resources (resource_id, filename, path, type, uploader, indexed, chunks)
                    VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                    ON CONFLICT (resource_id) DO UPDATE SET indexed = TRUE, chunks = EXCLUDED.chunks
                """, (resource_id, filename, path, type, uploader, chunks))
    
    def get_user_resources(self, username: str) -> List[Dict]:
        """Get all resources for a user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM resources WHERE uploader = %s ORDER BY uploaded_at DESC", (username,))
                return [dict(row) for row in cur.fetchall()]
    
    def get_all_resources(self) -> List[Dict]:
        """Get all resources in the system"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM resources ORDER BY uploaded_at DESC")
                return [dict(row) for row in cur.fetchall()]
    
    # Chunk operations
    def store_chunk(self, resource_id: str, chunk_id: str, text: str, 
                   start_pos: int, end_pos: int, metadata: Dict = None) -> None:
        """Store text chunk"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO chunks (resource_id, chunk_id, text, start_pos, end_pos, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (resource_id, chunk_id) DO UPDATE SET text = EXCLUDED.text
                """, (resource_id, chunk_id, text, start_pos, end_pos, Json(metadata or {})))
    
    def get_resource_chunks(self, resource_id: str) -> List[Dict]:
        """Get all chunks for a resource"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM chunks WHERE resource_id = %s ORDER BY start_pos", (resource_id,))
                return [dict(row) for row in cur.fetchall()]
    
    # Embedding operations
    def store_embedding(self, resource_id: str, chunk_id: str, vector: List[float], 
                       metadata: Dict = None) -> None:
        """Store embedding vector"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO embeddings (resource_id, chunk_id, vector, metadata)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (resource_id, chunk_id) DO UPDATE SET vector = EXCLUDED.vector
                """, (resource_id, chunk_id, Json(vector), Json(metadata or {})))
    
    def get_all_embeddings(self, username: Optional[str] = None) -> List[Tuple[str, List[float], Dict]]:
        """Get all embeddings, optionally filtered by user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if username:
                    cur.execute("""
                        SELECT e.resource_id, e.chunk_id, e.vector, e.metadata, c.text
                        FROM embeddings e
                        JOIN chunks c ON e.resource_id = c.resource_id AND e.chunk_id = c.chunk_id
                        JOIN resources r ON e.resource_id = r.resource_id
                        WHERE r.uploader = %s
                    """, (username,))
                else:
                    cur.execute("""
                        SELECT e.resource_id, e.chunk_id, e.vector, e.metadata, c.text
                        FROM embeddings e
                        JOIN chunks c ON e.resource_id = c.resource_id AND e.chunk_id = c.chunk_id
                    """)
                
                results = []
                for row in cur.fetchall():
                    results.append((
                        f"{row['resource_id']}:{row['chunk_id']}",
                        row['vector'],
                        {**dict(row['metadata']), 'text': row['text']}
                    ))
                return results
    
    # Plan operations
    def store_plan(self, plan_id: str, username: str, subject: str, 
                  exam_date: str, plan_data: Dict) -> None:
        """Store study plan"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO plans (plan_id, username, subject, exam_date, plan_data)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (plan_id) DO UPDATE SET plan_data = EXCLUDED.plan_data
                """, (plan_id, username, subject, exam_date, Json(plan_data)))
    
    def get_user_plans(self, username: str) -> List[Dict]:
        """Get all plans for a user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM plans WHERE username = %s ORDER BY created_at DESC", (username,))
                return [dict(row) for row in cur.fetchall()]
    
    def get_plan(self, plan_id: str) -> Optional[Dict]:
        """Get specific plan"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM plans WHERE plan_id = %s", (plan_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    
    # Quiz operations
    def store_quiz(self, quiz_id: str, username: str, topic: str, quiz_data: Dict) -> None:
        """Store quiz"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO quizzes (quiz_id, username, topic, quiz_data)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (quiz_id) DO UPDATE SET quiz_data = EXCLUDED.quiz_data
                """, (quiz_id, username, topic, Json(quiz_data)))
    
    def get_quiz(self, quiz_id: str) -> Optional[Dict]:
        """Get quiz by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM quizzes WHERE quiz_id = %s", (quiz_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    
    def get_user_quizzes(self, username: str) -> List[Dict]:
        """Get all quizzes for a user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM quizzes WHERE username = %s ORDER BY created_at DESC", (username,))
                return [dict(row) for row in cur.fetchall()]
    
    # Progress operations
    def get_progress(self, username: str) -> Dict:
        """Get user progress"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM progress WHERE username = %s", (username,))
                row = cur.fetchone()
                if row:
                    return dict(row)
                else:
                    # Initialize progress
                    cur.execute("""
                        INSERT INTO progress (username)
                        VALUES (%s)
                        RETURNING *
                    """, (username,))
                    return dict(cur.fetchone())
    
    def update_progress(self, username: str, weak_topics: List[str] = None, 
                       history_entry: Dict = None) -> None:
        """Update user progress"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if weak_topics is not None:
                    cur.execute("""
                        UPDATE progress
                        SET weak_topics = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE username = %s
                    """, (Json(weak_topics), username))
                
                if history_entry:
                    cur.execute("""
                        UPDATE progress
                        SET history = history || %s::jsonb, updated_at = CURRENT_TIMESTAMP
                        WHERE username = %s
                    """, (Json([history_entry]), username))
    
    # Spaced repetition operations
    def create_sr_card(self, card_id: str, username: str, front: str, back: str, 
                      source: str, due_date: str) -> None:
        """Create spaced repetition card"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sr_cards (card_id, username, front, back, source, due_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (card_id) DO NOTHING
                """, (card_id, username, front, back, source, due_date))
    
    def update_sr_card(self, card_id: str, easiness: float, interval: int, 
                      repetitions: int, due_date: str) -> None:
        """Update SR card after review"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE sr_cards
                    SET easiness = %s, interval = %s, repetitions = %s, 
                        due_date = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE card_id = %s
                """, (easiness, interval, repetitions, due_date, card_id))
    
    def get_due_cards(self, username: str) -> List[Dict]:
        """Get due SR cards for user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM sr_cards 
                    WHERE username = %s AND due_date <= CURRENT_DATE
                    ORDER BY due_date
                """, (username,))
                return [dict(row) for row in cur.fetchall()]
    
    def get_sr_card(self, card_id: str) -> Optional[Dict]:
        """Get specific SR card"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM sr_cards WHERE card_id = %s", (card_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    
    # Revision pack operations
    def store_revision_pack(self, pack_id: str, username: str, content: Dict, 
                           file_path: str) -> None:
        """Store revision pack"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO revision_packs (pack_id, username, content, file_path)
                    VALUES (%s, %s, %s, %s)
                """, (pack_id, username, Json(content), file_path))
    
    # Plan questions operations
    def store_plan_questions(self, plan_id: str, topic: str, questions: List[Dict]) -> None:
        """Store generated questions for a specific topic in a plan"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO plan_questions (plan_id, topic, questions)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (plan_id, topic) DO UPDATE SET questions = EXCLUDED.questions
                """, (plan_id, topic, Json(questions)))
    
    def get_plan_questions(self, plan_id: str, topic: str = None) -> Dict[str, List[Dict]]:
        """Get questions for a plan (optionally filtered by topic)"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if topic:
                    cur.execute(
                        "SELECT topic, questions FROM plan_questions WHERE plan_id = %s AND topic = %s",
                        (plan_id, topic)
                    )
                    row = cur.fetchone()
                    if row:
                        return {row['topic']: row['questions']}
                    return {}
                else:
                    cur.execute(
                        "SELECT topic, questions FROM plan_questions WHERE plan_id = %s",
                        (plan_id,)
                    )
                    result = {}
                    for row in cur.fetchall():
                        result[row['topic']] = row['questions']
                    return result
    
    def store_important_questions(self, plan_id: str, questions: List[Dict]) -> None:
        """Store important questions for a plan"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO plan_important_questions (plan_id, questions)
                    VALUES (%s, %s)
                    ON CONFLICT (plan_id) DO UPDATE SET questions = EXCLUDED.questions
                """, (plan_id, Json(questions)))
    
    def get_important_questions(self, plan_id: str) -> List[Dict]:
        """Get important questions for a plan"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT questions FROM plan_important_questions WHERE plan_id = %s",
                    (plan_id,)
                )
                row = cur.fetchone()
                return row['questions'] if row else []
    
    # Legacy compatibility methods (for existing code)
    def get(self, key: str) -> Optional[Any]:
        """Legacy get method - maps keys to appropriate table queries"""
        parts = key.split(':')
        if len(parts) < 2:
            return None
        
        table_type = parts[0]
        
        try:
            if table_type == 'user':
                return self.get_user(parts[1])
            elif table_type == 'plan' and len(parts) >= 3:
                plan = self.get_plan(parts[2])
                return plan['plan_data'] if plan else None
            elif table_type == 'quiz' and len(parts) >= 3:
                quiz = self.get_quiz(parts[2])
                return quiz['quiz_data'] if quiz else None
            elif table_type == 'progress':
                return self.get_progress(parts[1])
            elif table_type == 'resource':
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("SELECT * FROM resources WHERE resource_id = %s", (parts[1],))
                        row = cur.fetchone()
                        return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error in legacy get for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Legacy set method - maps keys to appropriate table inserts"""
        parts = key.split(':')
        if len(parts) < 2:
            return
        
        table_type = parts[0]
        
        try:
            if table_type == 'user':
                self.create_user(parts[1], value.get('name', parts[1]), value.get('prefs', {}))
            elif table_type == 'resource':
                self.store_resource(
                    parts[1],
                    value.get('filename', ''),
                    value.get('path', ''),
                    value.get('type', ''),
                    value.get('uploader', ''),
                    value.get('chunks', 0)
                )
        except Exception as e:
            logger.error(f"Error in legacy set for key {key}: {e}")
    
    def keys(self, prefix: str = "") -> List[str]:
        """Legacy keys method - returns keys based on prefix"""
        parts = prefix.split(':')
        if not parts:
            return []
        
        table_type = parts[0]
        result_keys = []
        
        try:
            if table_type == 'plan' and len(parts) >= 2:
                plans = self.get_user_plans(parts[1])
                result_keys = [f"plan:{p['username']}:{p['plan_id']}" for p in plans]
            elif table_type == 'quiz' and len(parts) >= 2:
                quizzes = self.get_user_quizzes(parts[1])
                result_keys = [f"quiz:{q['username']}:{q['quiz_id']}" for q in quizzes]
            elif table_type == 'resource':
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT resource_id FROM resources")
                        result_keys = [f"resource:{row[0]}" for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error in legacy keys for prefix {prefix}: {e}")
        
        return result_keys


# Global client instance
db_client = PostgreSQLClient()
