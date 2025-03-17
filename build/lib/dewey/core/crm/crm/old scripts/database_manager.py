import sqlite3
from datetime import datetime
import logging
from typing import Optional, List, Tuple, Dict, Any

class DatabaseManager:
    def __init__(self, db_path="api_logs.db"):
        """Initialize the database manager."""
        self.db_path = db_path
        self._init_db()
        self.logger = logging.getLogger(__name__)
        
    def _init_db(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS api_calls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        api_name TEXT,
                        endpoint TEXT,
                        parameters TEXT,
                        response_status INTEGER,
                        response_data TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS prompts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        prompt TEXT,
                        response TEXT,
                        api_name TEXT,
                        metadata TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise

    def log_api_call(self, api_name: str, endpoint: str, parameters: Dict[str, Any], 
                    response_status: int, response_data: Dict[str, Any]) -> None:
        """Log an API call to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO api_calls 
                    (timestamp, api_name, endpoint, parameters, response_status, response_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(),
                    api_name,
                    endpoint,
                    str(parameters),
                    response_status,
                    str(response_data)
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error logging API call: {str(e)}")
            raise

    def log_prompt(self, prompt: str, response: str, api_name: str, 
                  metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a prompt and its response."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO prompts 
                    (timestamp, prompt, response, api_name, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now(),
                    prompt,
                    response,
                    api_name,
                    str(metadata) if metadata else None
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error logging prompt: {str(e)}")
            raise

    def get_api_call_history(self, api_name: Optional[str] = None, 
                           limit: int = 100) -> List[Tuple]:
        """Retrieve API call history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM api_calls"
                params = []
                
                if api_name:
                    query += " WHERE api_name = ?"
                    params.append(api_name)
                    
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error retrieving API call history: {str(e)}")
            raise

    def get_prompt_history(self, api_name: Optional[str] = None, 
                          limit: int = 100) -> List[Tuple]:
        """Retrieve prompt history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM prompts"
                params = []
                
                if api_name:
                    query += " WHERE api_name = ?"
                    params.append(api_name)
                    
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error retrieving prompt history: {str(e)}")
            raise
