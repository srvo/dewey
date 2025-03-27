import logging

logger = logging.getLogger(__name__)

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
    """Get the current schema version.
    
    Args:
        local_only: Whether to only check the local database
        
    Returns:
        Current schema version number
    """
    try:
        result = self.execute_query("""
            SELECT MAX(version) FROM schema_versions
            WHERE status = 'success'
        """, local_only=local_only)
        
        return result[0][0] if result and result[0][0] else 0
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to get schema version: {e}")
