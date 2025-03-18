"""Gmail Sync Manager
==================

A consolidated manager for Gmail synchronization that handles both historical
and incremental syncs with robust error handling and consistency checking.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import duckdb
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ...db import initialize_crm_database
from ...db.errors import DatabaseError, SyncError
from .email_processor import EmailProcessor

logger = logging.getLogger(__name__)

class GmailSyncManager:
    """Manages Gmail synchronization with local and MotherDuck databases."""
    
    def __init__(
        self,
        db_path: str = "~/dewey_emails.duckdb",
        motherduck_db: str = "dewey_emails",
        batch_size: int = 50,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """Initialize the sync manager.
        
        Args:
            db_path: Path to local database
            motherduck_db: MotherDuck database name
            batch_size: Number of emails per batch
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.db_path = os.path.expanduser(db_path)
        self.motherduck_db = motherduck_db
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.email_processor = EmailProcessor()
        self.service = self._build_gmail_service()
        self.db_conn = self._initialize_database()
        
    def _build_gmail_service(self):
        """Build the Gmail API service with proper authentication."""
        try:
            credentials, _ = google.auth.default(
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )
            return build('gmail', 'v1', credentials=credentials)
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            raise SyncError(f"Gmail service initialization failed: {e}")
            
    def _initialize_database(self) -> duckdb.DuckDBPyConnection:
        """Initialize the database connection."""
        try:
            conn = initialize_crm_database(
                database_path=self.db_path,
                motherduck_db=self.motherduck_db
            )
            
            # Ensure all necessary tables exist
            self._create_tables(conn)
            return conn
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
            
    def _create_tables(self, conn: duckdb.DuckDBPyConnection):
        """Create necessary database tables if they don't exist."""
        try:
            # Sync status table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY,
                    sync_type VARCHAR,  -- 'historical' or 'incremental'
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    status VARCHAR,  -- 'success', 'failed', 'in_progress'
                    emails_processed INTEGER,
                    emails_failed INTEGER,
                    error_details JSON,
                    last_message_id VARCHAR
                )
            """)
            
            # Email consistency table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_consistency (
                    message_id VARCHAR PRIMARY KEY,
                    gmail_timestamp TIMESTAMP,
                    local_status VARCHAR,  -- 'present', 'missing', 'different'
                    motherduck_status VARCHAR,  -- 'present', 'missing', 'different'
                    last_checked TIMESTAMP,
                    needs_sync BOOLEAN,
                    error_count INTEGER DEFAULT 0,
                    last_error JSON
                )
            """)
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise DatabaseError(f"Table creation failed: {e}")
            
    def check_consistency(self, days_back: int = 7) -> Dict[str, int]:
        """Check consistency between Gmail, local DB, and MotherDuck.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Dictionary with consistency statistics
        """
        try:
            stats = {
                'total_checked': 0,
                'inconsistent': 0,
                'missing_local': 0,
                'missing_motherduck': 0,
                'needs_sync': 0
            }
            
            # Get list of emails from Gmail
            query = f'newer_than:{days_back}d'
            gmail_messages = self._list_messages(query)
            
            for msg in gmail_messages:
                stats['total_checked'] += 1
                message_id = msg['id']
                
                # Check local database
                local_exists = self._check_local_email(message_id)
                
                # Check MotherDuck
                motherduck_exists = self._check_motherduck_email(message_id)
                
                if not local_exists:
                    stats['missing_local'] += 1
                    
                if not motherduck_exists:
                    stats['missing_motherduck'] += 1
                    
                if not local_exists or not motherduck_exists:
                    stats['inconsistent'] += 1
                    self._mark_for_sync(message_id)
                    stats['needs_sync'] += 1
                    
            return stats
            
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            raise SyncError(f"Consistency check failed: {e}")
            
    def sync_emails(
        self,
        historical: bool = False,
        days_back: Optional[int] = None,
        max_emails: Optional[int] = None
    ) -> Dict[str, Any]:
        """Sync emails from Gmail to local and MotherDuck databases.
        
        Args:
            historical: Whether to perform a historical sync
            days_back: Number of days to look back
            max_emails: Maximum number of emails to sync
            
        Returns:
            Dictionary with sync statistics
        """
        try:
            sync_id = self._start_sync(
                sync_type='historical' if historical else 'incremental'
            )
            
            stats = {
                'processed': 0,
                'failed': 0,
                'skipped': 0,
                'total': 0
            }
            
            # Build query
            query = []
            if days_back:
                query.append(f'newer_than:{days_back}d')
            if not historical:
                # For incremental sync, only get emails we need to sync
                needs_sync = self._get_needs_sync()
                if needs_sync:
                    query.extend([f'id:{msg_id}' for msg_id in needs_sync])
                    
            query_str = ' OR '.join(query) if query else ''
            
            # Fetch and process emails
            messages = self._list_messages(query_str, max_results=max_emails)
            stats['total'] = len(messages)
            
            for batch in self._batch_messages(messages):
                try:
                    with self.db_conn.cursor() as cursor:
                        cursor.execute("BEGIN TRANSACTION")
                        
                        for msg in batch:
                            try:
                                self._process_message(msg['id'], cursor)
                                stats['processed'] += 1
                            except Exception as e:
                                logger.error(f"Failed to process message {msg['id']}: {e}")
                                stats['failed'] += 1
                                self._record_error(msg['id'], str(e))
                                
                        cursor.execute("COMMIT")
                except Exception as e:
                    logger.error(f"Batch processing failed: {e}")
                    self.db_conn.execute("ROLLBACK")
                    raise
                    
            self._finish_sync(sync_id, stats)
            return stats
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            if sync_id:
                self._fail_sync(sync_id, str(e))
            raise SyncError(f"Sync failed: {e}")
            
    def _list_messages(
        self,
        query: str = '',
        max_results: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """List messages from Gmail API with retry logic."""
        messages = []
        page_token = None
        
        while True:
            try:
                for attempt in range(self.max_retries):
                    try:
                        results = self.service.users().messages().list(
                            userId='me',
                            q=query,
                            pageToken=page_token,
                            maxResults=min(self.batch_size, max_results - len(messages))
                            if max_results else self.batch_size
                        ).execute()
                        
                        messages.extend(results.get('messages', []))
                        
                        if not results.get('nextPageToken') or (
                            max_results and len(messages) >= max_results
                        ):
                            return messages
                            
                        page_token = results.get('nextPageToken')
                        break
                        
                    except HttpError as e:
                        if attempt == self.max_retries - 1:
                            raise
                        time.sleep(self.retry_delay * (attempt + 1))
                        
            except Exception as e:
                logger.error(f"Failed to list messages: {e}")
                raise
                
    def _batch_messages(self, messages: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        """Split messages into batches."""
        for i in range(0, len(messages), self.batch_size):
            yield messages[i:i + self.batch_size]
            
    def _process_message(self, message_id: str, cursor) -> None:
        """Process a single message with error handling and retries."""
        for attempt in range(self.max_retries):
            try:
                # Fetch full message
                message = self.service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()
                
                # Process and store email
                email_data = self.email_processor.process_email(message)
                if email_data:
                    self._store_email(email_data, cursor)
                    self._update_consistency(message_id, 'present', 'present')
                return
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))
                
    def _store_email(self, email_data: Dict[str, Any], cursor) -> None:
        """Store email in both local and MotherDuck databases."""
        # Implementation depends on your specific schema
        pass
        
    def _start_sync(self, sync_type: str) -> int:
        """Record the start of a sync operation."""
        result = self.db_conn.execute("""
            INSERT INTO sync_status (
                sync_type, start_time, status, 
                emails_processed, emails_failed
            ) VALUES (?, CURRENT_TIMESTAMP, 'in_progress', 0, 0)
            RETURNING id
        """, [sync_type]).fetchone()
        
        return result[0]
        
    def _finish_sync(self, sync_id: int, stats: Dict[str, int]) -> None:
        """Record the successful completion of a sync operation."""
        self.db_conn.execute("""
            UPDATE sync_status 
            SET status = 'success',
                end_time = CURRENT_TIMESTAMP,
                emails_processed = ?,
                emails_failed = ?
            WHERE id = ?
        """, [stats['processed'], stats['failed'], sync_id])
        
    def _fail_sync(self, sync_id: int, error: str) -> None:
        """Record a failed sync operation."""
        self.db_conn.execute("""
            UPDATE sync_status 
            SET status = 'failed',
                end_time = CURRENT_TIMESTAMP,
                error_details = ?
            WHERE id = ?
        """, [{'error': error}, sync_id])
        
    def _check_local_email(self, message_id: str) -> bool:
        """Check if email exists in local database."""
        result = self.db_conn.execute(
            "SELECT 1 FROM emails WHERE id = ?", [message_id]
        ).fetchone()
        return bool(result)
        
    def _check_motherduck_email(self, message_id: str) -> bool:
        """Check if email exists in MotherDuck database."""
        try:
            result = self.db_conn.execute(f"""
                SELECT 1 FROM md:{self.motherduck_db}.emails 
                WHERE id = ?
            """, [message_id]).fetchone()
            return bool(result)
        except Exception:
            return False
            
    def _mark_for_sync(self, message_id: str) -> None:
        """Mark a message as needing synchronization."""
        self.db_conn.execute("""
            INSERT INTO email_consistency (
                message_id, needs_sync, last_checked
            ) VALUES (?, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (message_id) DO UPDATE 
            SET needs_sync = TRUE,
                last_checked = CURRENT_TIMESTAMP
        """, [message_id])
        
    def _get_needs_sync(self) -> List[str]:
        """Get list of message IDs that need synchronization."""
        results = self.db_conn.execute("""
            SELECT message_id FROM email_consistency
            WHERE needs_sync = TRUE
            AND error_count < ?
        """, [self.max_retries]).fetchall()
        
        return [r[0] for r in results]
        
    def _record_error(self, message_id: str, error: str) -> None:
        """Record an error for a message."""
        self.db_conn.execute("""
            INSERT INTO email_consistency (
                message_id, error_count, last_error, last_checked
            ) VALUES (?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (message_id) DO UPDATE 
            SET error_count = email_consistency.error_count + 1,
                last_error = ?,
                last_checked = CURRENT_TIMESTAMP
        """, [message_id, {'error': error}, {'error': error}]) 