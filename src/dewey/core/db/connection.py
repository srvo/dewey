import logging
import os
from typing import Any, List, Optional, Tuple

from dewey.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Main database connection class handling both local and MotherDuck connections."""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._init_connections()

    def _init_connections(self):
        """Initialize database connections using config."""
        import duckdb
        
        # Get MotherDuck token from environment
        md_token = os.getenv("MOTHERDUCK_TOKEN")
        if not md_token:
            raise DatabaseConnectionError("MOTHERDUCK_TOKEN not found in environment")

        # Initialize local DuckDB connection
        self.local_conn = duckdb.connect(self.config.get("local_db_path", ":memory:"))
        
        # Initialize MotherDuck connection using DuckDB's native method
        self.md_conn = duckdb.connect(
            database='md:',
            config={
                'motherduck_token': md_token,
                'allow_unsigned_extensions': 'true'
            }
        )
        
        # Set up schema if needed
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure required schema exists."""
        self.md_conn.execute("CREATE SCHEMA IF NOT EXISTS main")
        
    def get_connection(self, for_write: bool = False, local_only: bool = False) -> 'DatabaseConnection':
        """Get a database connection."""
        return self.md_conn if not local_only else self.local_conn

    def close(self) -> None:
        """Close all database connections."""
        if self.local_conn:
            self.local_conn.close()
        if self.md_conn:
            self.md_conn.close()
        
    def execute(self, query: str) -> None:
        """Execute a SQL statement on the appropriate database."""
        conn = self.get_connection(local_only=False)  # Use MotherDuck by default
        conn.execute(query)

    def execute_query(self, query: str, params: Optional[List[Any]] = None, 
                     for_write: bool = False, local_only: bool = False) -> List[Tuple]:
        """Execute a SQL query and return results."""
        conn = self.get_connection(local_only=local_only)
        if params:
            return conn.execute(query, params).fetchall()
        return conn.execute(query).fetchall()
        
    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        try:
            result = self.md_conn.execute("SHOW TABLES").fetchall()
            return [row[0] for row in result] if result else []
        except Exception as e:
            self.logger.error(f"Error listing tables: {e}")
            return []
        
    def get_schema(self, table_name: str) -> dict:
        """Get schema for a specific table."""
        try:
            result = self.md_conn.execute(f"DESCRIBE {table_name}").fetchall()
            return {row[0]: row[1] for row in result} if result else {}
        except Exception as e:
            self.logger.error(f"Error getting schema for {table_name}: {e}")
            return {}
        
    def sync_to_motherduck(self):
        """Synchronize the local database to MotherDuck with schema checks."""
        try:
            # Check schema versions first
            local_version = self.get_current_version(local_only=True)
            md_version = self.get_current_version(local_only=False)
        
            if local_version != md_version:
                self.logger.warning(f"Schema version mismatch - Local: {local_version}, MotherDuck: {md_version}")
                self._sync_schema_versions(local_version, md_version)

            # Get changes since last sync
            last_sync = self.execute_query("""
                SELECT MAX(sync_time) FROM sync_status 
                WHERE status = 'success'
            """, local_only=True)
        
            # Add schema-aware sync logic
            self._sync_with_schema_validation()
        
            # Add feedback table sync
            self._sync_feedback_tables()
        
            # Record sync success
            self.execute_query("""
                INSERT INTO sync_status (status, message)
                VALUES ('success', 'Sync completed successfully')
            """, for_write=True, local_only=False)
        
        except Exception as e:
            self.logger.error(f"Sync failed: {e}")
            self.execute_query("""
                INSERT INTO sync_status (status, message, details)
                VALUES ('failed', ?, ?)
            """, [str(e), str(e)], for_write=True, local_only=False)
            raise

    def _sync_schema_versions(self, local_version, md_version):
        """Handle schema version synchronization."""
        if local_version > md_version:
            self.logger.info("Pushing local schema changes to MotherDuck")
            self.execute_query("CALL motherduck_push_schema()", for_write=True)
        elif md_version > local_version:
            self.logger.info("Pulling MotherDuck schema changes")
            self.execute_query("CALL motherduck_pull_schema()", for_write=True)

    def _sync_with_schema_validation(self):
        """Perform schema-validated sync with conflict resolution."""
        self.execute_query("""
            CREATE OR REPLACE TABLE local_changes AS
            SELECT * EXCLUDE (__rowid__), 'local' as source_db
            FROM (SELECT * FROM EXCLUDE_CHANGES('*'))
        """, for_write=True, local_only=True)
        
        self.execute_query("""
            CREATE OR REPLACE TABLE motherduck_changes AS
            SELECT * EXCLUDE (__rowid__), 'motherduck' as source_db
            FROM (SELECT * FROM EXCLUDE_CHANGES('*'))
        """, for_write=True, local_only=False)
        
        self.execute_query("""
            INSERT INTO motherduck.main.sync_conflicts
            SELECT 
                lc.*,
                'schema_mismatch' as conflict_type,
                CURRENT_TIMESTAMP as detected_at
            FROM local_changes lc
            FULL OUTER JOIN motherduck_changes mc 
                ON lc.table_name = mc.table_id
                AND lc.record_id = mc.record_id
            WHERE lc != mc
        """, for_write=True)

    def _sync_feedback_tables(self):
        """Special handling for feedback-related tables."""
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS motherduck.main.ai_feedback (
                id VARCHAR PRIMARY KEY,
                source_table VARCHAR NOT NULL,
                source_id VARCHAR NOT NULL,
                feedback_type VARCHAR NOT NULL,
                feedback_content JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolution_details JSON,
                resolution_status VARCHAR DEFAULT 'pending'
            )
        """, for_write=True)
        
        self.execute_query("""
            SYNC motherduck.main.ai_feedback
        """, for_write=True)

    def get_current_version(self, local_only: bool = False) -> int:
        """Get the current schema version."""
        try:
            result = self.execute_query("""
                SELECT MAX(version) FROM schema_versions
                WHERE status = 'success'
            """, local_only=local_only)
            
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to get schema version: {e}")

# Singleton instance used by the system
db_manager = DatabaseConnection(config={})
