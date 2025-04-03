#!/usr/bin/env python3
"""
Gmail Email Fetcher and Database Repopulator
===========================================

This script:
1. Connects to Gmail API using OAuth credentials
2. Fetches all emails from the user's account
3. Drops the existing emails table in MotherDuck
4. Creates a new emails table with the current schema
5. Populates the table with emails fetched from Gmail
"""

import base64
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import uuid

import duckdb
from tqdm import tqdm  # For progress bars

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_motherduck_connection
from dewey.core.crm.enrichment.gmail_utils import GmailAPIClient


class GmailFetcherAndRepopulator(BaseScript):
    """Fetches emails from Gmail API and repopulates the emails table."""

    def __init__(self) -> None:
        """Initialize the fetcher with configurations."""
        super().__init__(
            name="GmailFetcherAndRepopulator",
            description="Fetches emails from Gmail API and repopulates the database.",
            config_section="gmail_repopulator",
            requires_db=True,
        )
        self.batch_size = self.get_config_value("batch_size", 100)
        self.max_emails = self.get_config_value("max_emails", 0)  # 0 means no limit
        self.gmail_client = GmailAPIClient(self.config)

    def execute(self) -> None:
        """Execute the email fetching and database repopulation process."""
        try:
            # Verify connection to Gmail API
            self.logger.info("Verifying connection to Gmail API...")
            if not self._verify_gmail_connection():
                self.logger.error("Failed to connect to Gmail API. Exiting.")
                return

            # Connect to MotherDuck
            self.logger.info("Connecting to MotherDuck database...")
            with get_motherduck_connection() as conn:
                # Confirm before dropping the existing table
                self.logger.warning("This will DROP the existing emails table and recreate it.")
                confirm = input("Are you sure you want to continue? (y/n): ")
                if confirm.lower() != 'y':
                    self.logger.info("Operation cancelled.")
                    return

                # Drop and recreate the emails table
                self._recreate_emails_table(conn)
                
                # Fetch and store emails
                self._fetch_and_store_emails(conn)
                
            self.logger.info("Email fetching and database repopulation completed successfully.")
            
        except KeyboardInterrupt:
            self.logger.info("Process interrupted by user.")
        except Exception as e:
            self.logger.error(f"Error in Gmail fetching process: {e}", exc_info=True)
            raise

    def _verify_gmail_connection(self) -> bool:
        """Verify connection to Gmail API.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Attempt to list a single message to verify connection
            service = self.gmail_client.service
            results = service.users().messages().list(userId='me', maxResults=1).execute()
            messages = results.get('messages', [])
            if messages:
                self.logger.info(f"Successfully connected to Gmail API. Found at least {len(messages)} message(s).")
                return True
            else:
                self.logger.warning("Connected to Gmail API but no messages found.")
                return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Gmail API: {e}")
            return False

    def _recreate_emails_table(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Drop and recreate the emails table.
        
        Args:
            conn: DuckDB connection
        """
        try:
            # Drop existing table if it exists
            self.logger.info("Dropping existing emails table...")
            conn.execute("DROP TABLE IF EXISTS emails")
            
            # Create fresh emails table with updated schema
            self.logger.info("Creating new emails table...")
            conn.execute("""
            CREATE TABLE emails (
                msg_id VARCHAR PRIMARY KEY,
                thread_id VARCHAR,
                subject VARCHAR,
                from_address VARCHAR,
                analysis_date TIMESTAMP,
                raw_analysis JSON,
                automation_score FLOAT,
                content_value FLOAT,
                human_interaction FLOAT,
                time_value FLOAT,
                business_impact FLOAT,
                uncertainty_score FLOAT,
                metadata JSON,
                priority INTEGER,
                label_ids JSON,
                snippet VARCHAR,
                internal_date BIGINT,
                size_estimate INTEGER,
                message_parts JSON,
                draft_id VARCHAR,
                draft_message JSON,
                attachments JSON,
                status VARCHAR DEFAULT 'new',
                error_message VARCHAR,
                batch_id VARCHAR,
                import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Create indexes for performance
            self.logger.info("Creating indexes...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id)",
                "CREATE INDEX IF NOT EXISTS idx_emails_from_address ON emails(from_address)",
                "CREATE INDEX IF NOT EXISTS idx_emails_internal_date ON emails(internal_date)",
                "CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status)",
                "CREATE INDEX IF NOT EXISTS idx_emails_import_timestamp ON emails(import_timestamp)"
            ]
            
            for idx in indexes:
                conn.execute(idx)
                
            self.logger.info("Emails table recreated successfully.")
        except Exception as e:
            self.logger.error(f"Error recreating emails table: {e}")
            raise

    def _fetch_and_store_emails(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Fetch all emails from Gmail API and store them in the database.
        
        Args:
            conn: DuckDB connection
        """
        try:
            service = self.gmail_client.service
            
            # Get total count of messages for progress reporting
            self.logger.info("Getting total message count...")
            results = service.users().messages().list(userId='me', maxResults=1).execute()
            total_messages = int(results.get('resultSizeEstimate', 0))
            
            if self.max_emails > 0 and self.max_emails < total_messages:
                total_messages = self.max_emails
                
            self.logger.info(f"Starting to fetch {total_messages} messages from Gmail...")
            
            # Use a unique batch ID for this import
            batch_id = str(uuid.uuid4())
            
            # Set up variables for pagination
            next_page_token = None
            processed_count = 0
            
            # Process messages in batches
            with tqdm(total=total_messages, desc="Fetching emails") as pbar:
                while True:
                    # Check if we've reached the maximum emails to process
                    if self.max_emails > 0 and processed_count >= self.max_emails:
                        self.logger.info(f"Reached maximum emails limit ({self.max_emails})")
                        break
                        
                    # Get list of message IDs
                    results = service.users().messages().list(
                        userId='me', 
                        pageToken=next_page_token,
                        maxResults=min(self.batch_size, 500)  # API limit is 500
                    ).execute()
                    
                    messages = results.get('messages', [])
                    if not messages:
                        self.logger.info("No more messages to fetch.")
                        break
                        
                    # Update next page token for pagination
                    next_page_token = results.get('nextPageToken')
                    
                    # Process this batch of messages
                    email_batch = []
                    for message_ref in messages:
                        try:
                            msg_id = message_ref['id']
                            
                            # Fetch full message
                            message = self.gmail_client.fetch_message(msg_id)
                            if not message:
                                self.logger.warning(f"Failed to fetch message {msg_id}, skipping")
                                continue
                                
                            # Parse message into structured data
                            email_data = self._parse_message(message)
                            email_batch.append(email_data)
                            
                            # Update progress
                            processed_count += 1
                            pbar.update(1)
                            
                            # Check if we've reached the maximum emails after each message
                            if self.max_emails > 0 and processed_count >= self.max_emails:
                                break
                                
                        except Exception as e:
                            self.logger.error(f"Error processing message {message_ref.get('id')}: {e}")
                            continue
                    
                    # Store batch in database
                    if email_batch:
                        self._store_email_batch(conn, email_batch, batch_id)
                        self.logger.info(f"Stored {len(email_batch)} emails in database")
                    
                    # Break if no more pages
                    if not next_page_token:
                        break
                        
                    # Add a small delay to avoid rate limiting
                    time.sleep(0.1)
            
            self.logger.info(f"Successfully fetched and stored {processed_count} emails.")
            
        except Exception as e:
            self.logger.error(f"Error fetching and storing emails: {e}")
            raise

    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Gmail message into a structured dictionary for database storage.
        
        Args:
            message: Gmail message object
            
        Returns:
            Structured email data
        """
        # Extract headers
        headers = {
            header['name'].lower(): header['value'] 
            for header in message.get('payload', {}).get('headers', [])
        }
        
        # Parse date
        date_str = headers.get('date', '')
        received_date = datetime.now()
        if date_str:
            try:
                # Simple parsing, could be improved
                import email.utils
                received_date = datetime.fromtimestamp(
                    email.utils.mktime_tz(email.utils.parsedate_tz(date_str))
                )
            except Exception as e:
                self.logger.warning(f"Failed to parse date '{date_str}': {e}")
        
        # Extract from email and name
        from_str = headers.get('from', '')
        from_name = ''
        from_email = ''
        
        if '<' in from_str and '>' in from_str:
            # Format: "Name <email@example.com>"
            from_name = from_str.split('<')[0].strip(' "\'')
            from_email = from_str.split('<')[1].split('>')[0].strip()
        else:
            # Just email address
            from_email = from_str.strip()
        
        # Extract body
        plain_body, html_body = self.gmail_client.extract_body(message)
        
        # Extract attachments
        attachments = self._extract_attachments(message.get('payload', {}))
        
        # Prepare data for insertion
        email_data = {
            'msg_id': message['id'],
            'thread_id': message.get('threadId', ''),
            'subject': headers.get('subject', ''),
            'from_address': from_email,
            'analysis_date': datetime.now().isoformat(),
            'raw_analysis': json.dumps(message),
            'automation_score': 0.0,  # Will be set by enrichment
            'content_value': 0.0,     # Will be set by enrichment
            'human_interaction': 0.0,  # Will be set by enrichment
            'time_value': 0.0,        # Will be set by enrichment
            'business_impact': 0.0,    # Will be set by enrichment
            'uncertainty_score': 0.0,  # Will be set by enrichment
            'metadata': json.dumps({
                'from_name': from_name,
                'to_addresses': [addr.strip() for addr in headers.get('to', '').split(',') if addr.strip()],
                'cc_addresses': [addr.strip() for addr in headers.get('cc', '').split(',') if addr.strip()],
                'bcc_addresses': [addr.strip() for addr in headers.get('bcc', '').split(',') if addr.strip()],
                'received_date': received_date.isoformat(),
                'body_text': plain_body,
                'body_html': html_body
            }),
            'priority': 0,  # Will be set by enrichment
            'label_ids': json.dumps(message.get('labelIds', [])),
            'snippet': message.get('snippet', ''),
            'internal_date': int(message.get('internalDate', 0)),
            'size_estimate': message.get('sizeEstimate', 0),
            'message_parts': json.dumps(message.get('payload', {})),
            'draft_id': None,  # Will be set if this is a draft
            'draft_message': None,  # Will be set if this is a draft
            'attachments': json.dumps(attachments),
            'status': 'new',
            'error_message': None,
            'batch_id': None,  # Will be set during batch insertion
            'import_timestamp': datetime.now().isoformat(),
        }
        
        return email_data

    def _extract_attachments(self, payload: Dict) -> List[Dict[str, Any]]:
        """Extract attachments from the message payload.
        
        Args:
            payload: Gmail message payload
            
        Returns:
            List of attachment metadata
        """
        attachments = []
        
        if not payload:
            return attachments
        
        # Check if this part is an attachment
        if 'filename' in payload and payload['filename']:
            attachments.append({
                'filename': payload['filename'],
                'mimeType': payload.get('mimeType', ''),
                'size': payload.get('body', {}).get('size', 0),
                'attachmentId': payload.get('body', {}).get('attachmentId', '')
            })
        
        # Check for multipart
        if 'parts' in payload:
            for part in payload['parts']:
                attachments.extend(self._extract_attachments(part))
        
        return attachments

    def _store_email_batch(self, conn: duckdb.DuckDBPyConnection, email_batch: List[Dict[str, Any]], batch_id: str) -> None:
        """Store a batch of emails in the database.
        
        Args:
            conn: DuckDB connection
            email_batch: List of email data dictionaries
            batch_id: Batch identifier
        """
        if not email_batch:
            return
            
        try:
            # Start a transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Prepare SQL for batch insert
            placeholders = []
            params = []
            
            for email_data in email_batch:
                # Add batch_id to each email
                email_data['batch_id'] = batch_id
                
                # Construct placeholders and parameters
                placeholder_list = []
                current_params = []
                
                for column in [
                    'msg_id', 'thread_id', 'subject', 'from_address', 'analysis_date',
                    'raw_analysis', 'automation_score', 'content_value', 'human_interaction',
                    'time_value', 'business_impact', 'uncertainty_score', 'metadata',
                    'priority', 'label_ids', 'snippet', 'internal_date', 'size_estimate',
                    'message_parts', 'draft_id', 'draft_message', 'attachments', 'status',
                    'error_message', 'batch_id', 'import_timestamp'
                ]:
                    placeholder_list.append('?')
                    current_params.append(email_data.get(column, None))
                
                placeholders.append(f"({', '.join(placeholder_list)})")
                params.extend(current_params)
            
            # Build the SQL query
            columns = [
                'msg_id', 'thread_id', 'subject', 'from_address', 'analysis_date',
                'raw_analysis', 'automation_score', 'content_value', 'human_interaction',
                'time_value', 'business_impact', 'uncertainty_score', 'metadata',
                'priority', 'label_ids', 'snippet', 'internal_date', 'size_estimate',
                'message_parts', 'draft_id', 'draft_message', 'attachments', 'status',
                'error_message', 'batch_id', 'import_timestamp'
            ]
            
            sql = f"""
            INSERT INTO emails ({', '.join(columns)})
            VALUES {', '.join(placeholders)}
            """
            
            # Execute the query
            conn.execute(sql, params)
            
            # Commit the transaction
            conn.execute("COMMIT")
            
        except Exception as e:
            # Rollback on error
            conn.execute("ROLLBACK")
            self.logger.error(f"Error storing email batch: {e}")
            raise


if __name__ == "__main__":
    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    fetcher = GmailFetcherAndRepopulator()
    fetcher.execute() 