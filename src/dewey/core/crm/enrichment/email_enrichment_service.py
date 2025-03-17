#!/usr/bin/env python3
"""
Email Enrichment Service

This module provides functionality to enrich email content by fetching full message bodies
from Gmail and extracting relevant metadata.
"""

import os
import json
import logging
import time
import structlog
import duckdb
import uuid
from typing import Dict, List, Optional, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

class Email:
    """Class representing an email with enrichment capabilities."""
    
    def __init__(self, id=None, gmail_id=None, subject=None, from_email=None, 
                 plain_body=None, html_body=None, importance=None, email_metadata=None):
        self.id = id
        self.gmail_id = gmail_id
        self.subject = subject
        self.from_email = from_email
        self.plain_body = plain_body
        self.html_body = html_body
        self.importance = importance or 0
        self.email_metadata = email_metadata or {}

def get_gmail_service():
    """Get an authenticated Gmail API service."""
    try:
        # Load credentials from the token file
        token_path = os.path.expanduser("~/dewey/config/gmail_token.json")
        if not os.path.exists(token_path):
            logger.error(f"Token file not found at {token_path}")
            return None
            
        credentials = Credentials.from_authorized_user_info(
            json.load(open(token_path))
        )
        
        # Build the Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        return service
    except Exception as e:
        logger.error(f"Error creating Gmail service: {str(e)}")
        return None

def get_duckdb_connection(db_path: Optional[str] = None) -> duckdb.DuckDBPyConnection:
    """Get a connection to the DuckDB database."""
    if db_path is None:
        db_path = os.path.expanduser("~/dewey_emails.duckdb")
    
    try:
        # Try to connect to MotherDuck first
        try:
            conn = duckdb.connect("md:dewey_emails")
            logger.info("Connected to MotherDuck")
            return conn
        except Exception as e:
            logger.warning(f"Failed to connect to MotherDuck: {str(e)}")
            
        # Fall back to local database
        conn = duckdb.connect(db_path)
        logger.info(f"Connected to local database at {db_path}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        # Create a new in-memory database as a last resort
        logger.warning("Creating in-memory database")
        return duckdb.connect(":memory:")

class EmailEnrichmentService:
    """Service for enriching email content."""
    
    def __init__(self):
        """Initialize the email enrichment service."""
        self.gmail_service = get_gmail_service()
        
    def fetch_full_message(self, gmail_id: str) -> Dict[str, Any]:
        """
        Fetch the full message content from Gmail.
        
        Args:
            gmail_id: The Gmail message ID
            
        Returns:
            Dictionary containing the full message content
        """
        if not self.gmail_service:
            logger.error("Gmail service not available")
            return {}
            
        try:
            # Fetch the full message
            message = self.gmail_service.users().messages().get(
                userId='me',
                id=gmail_id,
                format='full'
            ).execute()
            
            return message
        except Exception as e:
            logger.error(f"Error fetching message {gmail_id}: {str(e)}")
            return {}
    
    def extract_message_content(self, message: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract plain text and HTML content from a Gmail message.
        
        Args:
            message: The Gmail message object
            
        Returns:
            Dictionary containing plain_body and html_body
        """
        content = {
            'plain_body': '',
            'html_body': ''
        }
        
        if not message or 'payload' not in message:
            return content
            
        # Extract content from parts
        def extract_parts(parts):
            for part in parts:
                if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                    content['plain_body'] += part['body']['data']
                elif part.get('mimeType') == 'text/html' and 'data' in part.get('body', {}):
                    content['html_body'] += part['body']['data']
                
                # Recursively process nested parts
                if 'parts' in part:
                    extract_parts(part['parts'])
        
        # Start with the payload
        payload = message['payload']
        if 'body' in payload and 'data' in payload['body']:
            if payload.get('mimeType') == 'text/plain':
                content['plain_body'] = payload['body']['data']
            elif payload.get('mimeType') == 'text/html':
                content['html_body'] = payload['body']['data']
        
        # Process parts if available
        if 'parts' in payload:
            extract_parts(payload['parts'])
            
        return content

    def enrich_email(self, email: Email) -> bool:
        """
        Enrich a single email with full content from Gmail.

        Args:
            email: The Email object to enrich

        Returns:
            True if enrichment was successful, False otherwise
        """
        if not email.gmail_id:
            logger.warning(f"Email {email.id} has no Gmail ID")
            return False
            
        try:
            # Fetch the full message
            message = self.fetch_full_message(email.gmail_id)
            if not message:
                logger.warning(f"Failed to fetch message {email.gmail_id}")
                return False
                
            # Extract content
            content = self.extract_message_content(message)
            
            # Update email object
            email.plain_body = content['plain_body']
            email.html_body = content['html_body']
            
            # Update email metadata
            email.email_metadata.update({
                'enriched_at': time.time(),
                'has_attachments': bool(message.get('payload', {}).get('parts', [])),
                'label_ids': message.get('labelIds', [])
            })
            
            # Update database
            conn = get_duckdb_connection()
            conn.execute("""
                UPDATE emails
                SET plain_body = ?,
                    html_body = ?,
                    email_metadata = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, [
                email.plain_body,
                email.html_body,
                json.dumps(email.email_metadata),
                email.id
            ])
            
            logger.info(f"Enriched email {email.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error enriching email {email.id}: {str(e)}")
            return False
    
    def enrich_emails(self, batch_size: int = 50, max_emails: int = 100) -> int:
        """
        Enrich a batch of emails.
        
        Args:
            batch_size: Number of emails to process in each batch
            max_emails: Maximum number of emails to process
            
        Returns:
            Number of emails successfully enriched
        """
        logger.info(f"Starting email enrichment (batch_size={batch_size}, max_emails={max_emails})")
        
        try:
            # Connect to database
            conn = get_duckdb_connection()
            
            # Create enrichment_tasks table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS enrichment_tasks (
                    id VARCHAR PRIMARY KEY,
                    entity_type VARCHAR,
                    entity_id VARCHAR,
                    task_type VARCHAR,
                    status VARCHAR,
                    attempts INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP,
                    result TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Get emails that need enrichment
            conn.execute("""
                CREATE OR REPLACE TEMPORARY VIEW emails_to_enrich AS
                SELECT e.* 
                FROM emails e
                LEFT JOIN enrichment_tasks et ON 
                    e.id = et.entity_id AND 
                    et.entity_type = 'email' AND 
                    et.task_type = 'email_metadata'
                WHERE et.task_id IS NULL
                OR (et.status = 'failed' AND et.updated_at < CURRENT_TIMESTAMP - INTERVAL 1 DAY)
                LIMIT ?
            """, [max_emails])
            
            # Get count
            count = conn.execute("SELECT COUNT(*) FROM emails_to_enrich").fetchone()[0]
            logger.info(f"Found {count} emails to enrich")
            
            if count == 0:
                logger.info("No emails to process")
                return 0
            
            # Process in batches
            enriched_count = 0
            for offset in range(0, count, batch_size):
                batch = conn.execute(f"""
                    SELECT id, gmail_id, subject, from_email, 
                           plain_body, html_body, importance, email_metadata
                    FROM emails_to_enrich
                    LIMIT {batch_size} OFFSET {offset}
                """).fetchall()
                
                logger.info(f"Processing batch of {len(batch)} emails (offset {offset})")
                
                for row in batch:
                    # Create Email object
                    email = Email(
                        id=row[0],
                        gmail_id=row[1],
                        subject=row[2],
                        from_email=row[3],
                        plain_body=row[4],
                        html_body=row[5],
                        importance=row[6],
                        email_metadata=json.loads(row[7]) if row[7] else {}
                    )
                    
                    # Create task
                    task_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO enrichment_tasks (
                            id, entity_type, entity_id, task_type, status
                        ) VALUES (?, ?, ?, ?, 'pending')
                    """, [
                        task_id,
                        'email',
                        email.id,
                        'email_metadata'
                    ])
                    
                    # Enrich email
                    success = self.enrich_email(email)
                    
                    # Update task status
                    if success:
                        conn.execute("""
                            UPDATE enrichment_tasks
                            SET status = 'completed',
                                attempts = attempts + 1,
                                last_attempt = CURRENT_TIMESTAMP,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, [task_id])
                        enriched_count += 1
                    else:
                        conn.execute("""
                            UPDATE enrichment_tasks
                            SET status = 'failed',
                                attempts = attempts + 1,
                                last_attempt = CURRENT_TIMESTAMP,
                                error_message = 'Failed to enrich email',
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, [task_id])
                
                # Commit after each batch
                conn.commit()
                
                # Sleep between batches to avoid rate limiting
                if offset + batch_size < count:
                    time.sleep(1)
            
            logger.info(f"Enriched {enriched_count} emails")
            return enriched_count

        except Exception as e:
            logger.error(f"Error in email enrichment: {str(e)}")
            raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich emails with full content from Gmail")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing emails")
    parser.add_argument("--max-emails", type=int, default=100, help="Maximum number of emails to process")
    
    args = parser.parse_args()
    
    service = EmailEnrichmentService()
    service.enrich_emails(batch_size=args.batch_size, max_emails=args.max_emails)
