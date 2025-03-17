import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import config
from ..core.exceptions import DatabaseError
from ..core.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Database connection and operations manager."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database with optional custom path."""
        self.db_path = db_path or config.database_uri

    @contextmanager
    def get_connection(self):
        """Create a database connection context manager."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            error_msg = f"Database connection failed: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
        finally:
            conn.close()

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        with self.get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(query, params or {})
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.Error as e:
                error_msg = f"Query execution failed: {str(e)}"
                logger.error(error_msg, extra={"query": query})
                raise DatabaseError(error_msg, query=query)

    def execute_update(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return rowcount."""
        with self.get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(query, params or {})
                return cursor.rowcount
            except sqlite3.Error as e:
                error_msg = f"Update execution failed: {str(e)}"
                logger.error(error_msg, extra={"query": query})
                raise DatabaseError(error_msg, query=query)

    def insert_company(self, company_data: Dict[str, Any]) -> int:
        """Insert a company into the database."""
        query = """
            INSERT INTO companies (
                name, ticker, isin, tick, industry, category, 
                sector, description, last_tick_date, workflow, 
                excluded, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (name) DO UPDATE SET
                ticker=excluded.ticker,
                tick=excluded.tick,
                last_tick_date=excluded.last_tick_date,
                note=excluded.note
            RETURNING id
        """
        with self.get_connection() as conn:
            try:
                return conn.execute(query, company_data).fetchone()[0]
            except sqlite3.Error as e:
                error_msg = f"Failed to insert company: {str(e)}"
                logger.error(error_msg, extra={"company_data": company_data})
                raise DatabaseError(error_msg, query=query)


# For backward compatibility
def get_connection():
    """Legacy function for backward compatibility."""
    db = Database()
    return db.get_connection()
