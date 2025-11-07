import json
import os
from typing import Any, Optional

class ReplitDB:
    """Simple key-value database client using Replit DB"""
    
    def __init__(self):
        try:
            from replit import db
            self.db = db
            self.use_replit = True
        except ImportError:
            self.db = {}
            self.use_replit = False
            print("Warning: Replit DB not available, using in-memory dict")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        try:
            if self.use_replit:
                value = self.db.get(key)
                if value:
                    return json.loads(value) if isinstance(value, str) else value
            else:
                return self.db.get(key)
        except Exception as e:
            print(f"Error getting key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any):
        """Set value by key"""
        try:
            if self.use_replit:
                self.db[key] = json.dumps(value)
            else:
                self.db[key] = value
        except Exception as e:
            print(f"Error setting key {key}: {e}")
    
    def delete(self, key: str):
        """Delete key"""
        try:
            if self.use_replit:
                del self.db[key]
            else:
                self.db.pop(key, None)
        except Exception as e:
            print(f"Error deleting key {key}: {e}")
    
    def keys(self, prefix: str = "") -> list:
        """Get all keys with optional prefix filter"""
        try:
            if self.use_replit:
                all_keys = list(self.db.keys())
            else:
                all_keys = list(self.db.keys())
            
            if prefix:
                return [k for k in all_keys if k.startswith(prefix)]
            return all_keys
        except Exception as e:
            print(f"Error getting keys: {e}")
            return []

db_client = ReplitDB()
