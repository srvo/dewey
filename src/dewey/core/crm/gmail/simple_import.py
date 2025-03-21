#!/usr/bin/env python3
"""
Simple Gmail Email Import Script
===============================

This script imports emails from Gmail using gcloud CLI authentication.
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import google.auth
from dateutil import parser as date_parser
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection

# from dewey.core.db.utils import create_table_if_not_exists # Removed direct schema operations
# from dewey.llm.llm_utils import call_llm # Removed direct LLM calls

# Disable file cache warning
class MemoryCache(Cache):
    _CACHE = {}

    def get(self, url):
        return MemoryCache._CACHE.get(url)

    def set(self, url, content):
        MemoryCache._CACHE[url] = content


class GmailImporter(BaseScript):
    """Gmail email importer script."""

    def __init__(self) -> None:
        """Initialize GmailImporter with configurations."""
        super().__init__(
            name="GmailImporter",
            description="Imports emails from Gmail into a database.",
            config_section="gmail_importer",
            requires_db=True,
        )
        self.credentials_dir = Path(self.get_config_value("paths.credentials_dir"))
        self.credentials_path = self.credentials_dir / self.get_config_value("settings.gmail_credentials_file")
        self.token_path = self.credentials_dir / self.get_config_value("settings.gmail_token_file")
        self.scopes = self.get_config_value("settings.gmail_scopes") or [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        self.oauth_token_uri = self.get_config_value("settings.oauth_token_uri") or 'https://oauth2.googleapis.com/token'

    def _create_emails_table(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Creates the emails table in the database if it doesn't exist.

        Args:
            conn: DuckDB connection object.
        """
        try:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS emails (
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
                snippet TEXT,
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
            self.logger.info("Verified emails table exists with correct schema")
            
            # Create indexes if they don't exist
            for idx in [
                "CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id)",
                "CREATE INDEX IF NOT EXISTS idx_emails_from_address ON emails(from_address)",
                "CREATE INDEX IF NOT EXISTS idx_emails_internal_date ON emails(internal_date)",
                "CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status)",
                "CREATE INDEX IF NOT EXISTS idx_emails_batch_id ON emails(batch_id)",
                "CREATE INDEX IF NOT EXISTS idx_emails_import_timestamp ON emails(import_timestamp)"
            ]:
                try:
                    conn.execute(idx)
                except Exception as e:
                    self.logger.warning(f"Failed to create index: {e}")
        except Exception as e:
            self.logger.error(f"Error creating emails table: {e}")
            raise

    def build_gmail_service(self, user_email: Optional[str] = None):
        """Build the Gmail API service.
        
        Args:
            user_email: Email address to impersonate (for domain-wide delegation)
            
        Returns:
            Gmail API service
        """
        try:
            credentials = None
            
            # Check if we have a token file
            if os.path.exists(self.token_path):
                self.logger.info(f"Using token from {self.token_path}")
                credentials = Credentials.from_authorized_user_file(self.token_path, self.scopes)
            
            # If no valid credentials, and we have a credentials file
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    self.logger.info("Refreshing expired credentials")
                    credentials.refresh(Request())
                elif os.path.exists(self.credentials_path):
                    self.logger.info(f"Using credentials from {self.credentials_path}")
                    
                    # Load the raw JSON to inspect its format
                    try:
                        with open(self.credentials_path, 'r') as f:
                            creds_data = json.load(f)
                            
                        self.logger.info(f"Credentials file format: {list(creds_data.keys())}")
                        
                        # Check if it's a token file (has 'access_token' field)
                        if 'access_token' in creds_data:
                            self.logger.info("Using access token from credentials file")
                            
                            # Create credentials from the token
                            credentials = Credentials(
                                token=creds_data.get('access_token'),
                                refresh_token=creds_data.get('refresh_token'),
                                token_uri=self.oauth_token_uri,
                                client_id=creds_data.get('client_id', ''),
                                client_secret=creds_data.get('client_secret', '')
                            )
                            
                        # Check if it's an API key
                        elif 'api_key' in creds_data:
                            self.logger.info("Using API key from credentials file")
                            # Use API key authentication
                            return build('gmail', 'v1', developerKey=creds_data['api_key'], cache=MemoryCache())
                            
                        # Check if it's a service account key file
                        elif 'type' in creds_data and creds_data['type'] == 'service_account':
                            self.logger.info("Using service account from credentials file")
                            credentials = service_account.Credentials.from_service_account_info(
                                creds_data,
                                scopes=self.scopes
                            )
                            
                            # If user_email is provided, use domain-wide delegation
                            if user_email and hasattr(credentials, 'with_subject'):
                                credentials = credentials.with_subject(user_email)
                                
                        # Check if it's an OAuth client credentials file
                        elif 'installed' in creds_data or 'web' in creds_data:
                            self.logger.info("Using OAuth client credentials from credentials file")
                            
                            # Create a flow from the credentials file
                            flow = InstalledAppFlow.from_client_secrets_file(
                                self.credentials_path,
                                self.scopes
                            )
                            
                            # Run the OAuth flow to get credentials
                            credentials = flow.run_local_server(port=0)
                            
                            # Save the credentials for future use
                            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
                            with open(self.token_path, 'w') as token:
                                token.write(credentials.to_json())
                                self.logger.info(f"Saved token to {self.token_path}")
                                
                        else:
                            self.logger.warning("Unknown credentials format, falling back to application default credentials")
                            credentials, _ = google.auth.default(
                                scopes=self.scopes + ['https://www.googleapis.com/auth/cloud-platform']
                            )
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to parse credentials file: {e}")
                        self.logger.info("Using application default credentials")
                        credentials, _ = google.auth.default(
                            scopes=self.scopes + ['https://www.googleapis.com/auth/cloud-platform']
                        )
                else:
                    self.logger.warning(f"Credentials file not found at {self.credentials_path}")
                    self.logger.info("Using application default credentials")
                    # Use application default credentials from gcloud CLI
                    credentials, _ = google.auth.default(
                        scopes=self.scopes + ['https://www.googleapis.com/auth/cloud-platform']
                    )
            
            # Build the service with memory cache
            return build('gmail', 'v1', credentials=credentials, cache=MemoryCache())
        except Exception as e:
            self.logger.error(f"Failed to build Gmail service: {e}")
            raise

    def fetch_emails(self, service, conn, days_back=7, max_emails=100, user_id="me", historical=False, include_sent=True):
        """Fetch emails from Gmail API that don't exist in MotherDuck.
        
        Args:
            service: Gmail API service
            conn: Existing database connection
            days_back: Number of days to look back (ignored if historical=True)
            max_emails: Maximum number of emails to fetch per batch
            user_id: User ID to fetch emails for (default: "me")
            historical: If True, fetch all emails regardless of date
            include_sent: If True, include sent emails
            
        Returns:
            List of email IDs
        """
        try:
            # Calculate date range if not historical
            if not historical:
                end_date = datetime.now().replace(tzinfo=None)
                start_date = end_date - timedelta(days=days_back)
                
                # Format dates for Gmail query
                start_date_str = start_date.strftime('%Y/%m/%d')
                end_date_str = end_date.strftime('%Y/%m/%d')
                
                self.logger.info(f"Importing emails from {start_date_str} to {end_date_str}")
            else:
                self.logger.info("Importing all historical emails")
            
            # Prepare query for sent items if needed
            query = None
            if include_sent:
                self.logger.info("Including sent emails")
            
            # Get existing email IDs from MotherDuck
            try:
                count_result = conn.execute("""
                    SELECT COUNT(*) FROM emails
                """).fetchone()
                existing_count = count_result[0] if count_result else 0
                
                existing_ids = set(row[0] for row in conn.execute("""
                    SELECT msg_id FROM emails
                """).fetchall())
                self.logger.info(f"Found {existing_count} existing emails in MotherDuck ({len(existing_ids)} IDs loaded)")
            except Exception as e:
                self.logger.error(f"Error getting existing emails: {e}")
                existing_ids = set()
            
            # Fetch all messages in batches
            all_messages = []
            page_token = None
            total_fetched = 0
            max_retries = 5
            base_delay = 30  # Increased base delay
            batch_size = 50  # Reduced batch size
            
            while True:
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        # Fetch a batch of messages
                        results = service.users().messages().list(
                            userId=user_id,
                            maxResults=batch_size,  # Using smaller batch size
                            pageToken=page_token,
                            q=query
                        ).execute()
                        
                        messages = results.get('messages', [])
                        if not messages:
                            break
                        
                        # Filter out existing messages
                        new_messages = [msg for msg in messages if msg['id'] not in existing_ids]
                        all_messages.extend(new_messages)
                        total_fetched += len(messages)
                        
                        self.logger.info(f"Fetched {len(messages)} messages, {len(new_messages)} new, total new: {len(all_messages)}")
                        
                        # Check if we've reached the max
                        if not historical and len(all_messages) >= max_emails:
                            all_messages = all_messages[:max_emails]
                            return [msg['id'] for msg in all_messages]
                        
                        # Get the next page token
                        page_token = results.get('nextPageToken')
                        if not page_token:
                            return [msg['id'] for msg in all_messages]
                        
                        # Add a delay between successful requests
                        time.sleep(2)  # Increased delay between requests
                        break  # Break retry loop on success
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
                            retry_count += 1
                            if retry_count < max_retries:
                                # Extract retry time from error message
                                import re
                                retry_time_match = re.search(r"Retry after ([^Z]+Z)", error_msg)
                                
                                if retry_time_match:
                                    try:
                                        from dateutil import parser
                                        retry_time = parser.parse(retry_time_match.group(1))
                                        now = datetime.now(retry_time.tzinfo)
                                        delay = max((retry_time - now).total_seconds() + 5, base_delay * (2 ** (retry_count - 1)))
                                    except Exception as parse_error:
                                        self.logger.warning(f"Failed to parse retry time: {parse_error}")
                                        delay = base_delay * (2 ** (retry_count - 1))
                                else:
                                    delay = base_delay * (2 ** (retry_count - 1))
                                
                                self.logger.info(f"Rate limit exceeded. Waiting {delay:.2f} seconds before retry {retry_count}/{max_retries}...")
                                time.sleep(delay)
                                continue
                        
                        self.logger.error(f"Error fetching messages: {e}")
                        if retry_count == max_retries - 1:
                            return [msg['id'] for msg in all_messages]
                        retry_count += 1
                        time.sleep(base_delay)
                
                if retry_count == max_retries:
                    self.logger.warning(f"Max retries ({max_retries}) reached. Moving on with collected messages.")
                    break
            
            if not all_messages:
                self.logger.info("No new emails found.")
                return []
            
            self.logger.info(f"Found {len(all_messages)} new emails to process")
            return [msg['id'] for msg in all_messages]
                
        except Exception as e:
            self.logger.error(f"Error fetching emails: {e}")
            return []

    def fetch_email(self, service, msg_id, user_id='me'):
        """Fetch a single email message from Gmail API.
        
        Args:
            service: Gmail API service instance
            msg_id: ID of message to fetch
            user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
            
        Returns:
            A dict containing the email data, or None if the fetch failed
        """
        try:
            # Get the email message
            message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
            return message
        except Exception as e:
            self.logger.error(f"Error fetching message {msg_id}: {e}")
            return None

    def parse_email(self, message: Dict) -> Dict[str, Any]:
        """Parse a Gmail message into a structured dictionary.
        
        Args:
            message: Gmail message object
            
        Returns:
            Structured email data
        """
        headers = {header['name'].lower(): header['value'] 
                  for header in message.get('payload', {}).get('headers', [])}
        
        # Extract body
        body = self.extract_body(message.get('payload', {}))
        
        # Extract email data
        email_data = {
            'id': message['id'],
            'threadId': message['threadId'],
            'subject': headers.get('subject', ''),
            'from': headers.get('from', ''),
            'to': headers.get('to', ''),
            'cc': headers.get('cc', ''),
            'date': headers.get('date', ''),
            'snippet': message.get('snippet', ''),
            'labelIds': message.get('labelIds', []),
            'internalDate': message.get('internalDate', ''),
            'sizeEstimate': message.get('sizeEstimate', 0),
            'body': {
                'text': body['text'],
                'html': body['html']
            },
            'attachments': self.extract_attachments(message.get('payload', {}))
        }
        
        return email_data

    def extract_body(self, payload: Dict) -> Dict[str, str]:
        """Extract the email body from the payload.
        
        Args:
            payload: Gmail message payload
            
        Returns:
            Dictionary with 'text' and 'html' versions of the body
        """
        result = {'text': '', 'html': ''}
        
        if not payload:
            return result
        
        def decode_part(part):
            if 'body' in part and 'data' in part['body']:
                try:
                    data = part['body']['data']
                    return base64.urlsafe_b64decode(data).decode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Failed to decode email part: {e}")
                    return ''
            return ''
        
        def process_part(part):
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                if not result['text']:  # Only set if not already set
                    result['text'] = decode_part(part)
            elif mime_type == 'text/html':
                if not result['html']:  # Only set if not already set
                    result['html'] = decode_part(part)
            elif 'parts' in part:
                for subpart in part['parts']:
                    process_part(subpart)
        
        # Process the main payload
        process_part(payload)
        
        return result

    def extract_attachments(self, payload: Dict) -> List[Dict[str, Any]]:
        """Extract attachments from the payload.
        
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
                attachments.extend(self.extract_attachments(part))
        
        return attachments

    def store_emails_batch(self, conn, email_batch, batch_id: str):
        """Store a batch of emails with improved error handling and batching.

        Args:
            conn: DuckDB connection
            email_batch: List of email data dictionaries
            batch_id: Unique identifier for this batch

        Returns:
            tuple: (success_count, error_count)
        """
        success_count = 0
        error_count = 0
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                # Begin transaction for the entire batch
                conn.execute("BEGIN TRANSACTION")
                
                # Process emails in smaller sub-batches
                sub_batch_size = 100
                for i in range(0, len(email_batch), sub_batch_size):
                    sub_batch = email_batch[i:i + sub_batch_size]
                    
                    for email_data in sub_batch:
                        try:
                            if self.store_email(conn, email_data, batch_id):
                                success_count += 1
                            else:
                                error_count += 1
                        except Exception as e:
                            self.logger.error(f"Error storing email: {e}")
                            error_count += 1
                            continue
                    
                    # Commit each sub-batch
                    conn.execute("COMMIT")
                    conn.execute("BEGIN TRANSACTION")
                    
                    self.logger.info(f"Processed sub-batch {i//sub_batch_size + 1}, "
                              f"Success: {success_count}, Errors: {error_count}")
                
                # Final commit
                conn.execute("COMMIT")
                break
                
            except Exception as e:
                retry_count += 1
                conn.execute("ROLLBACK")
                
                if retry_count < max_retries:
                    wait_time = retry_count * 5  # Exponential backoff
                    self.logger.warning(f"Batch failed, retrying in {wait_time} seconds... ({retry_count}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to process batch after {max_retries} attempts")
                    raise
        
        return success_count, error_count

    def store_email(self, conn, email_data, batch_id: str):
        """Store a single email with improved error handling.

        Args:
            conn: DuckDB connection
            email_data: Dictionary containing email data
            batch_id: Unique identifier for this import batch

        Returns:
            bool: True if email was stored successfully
        """
        try:
            # Debug logging
            self.logger.info(f"Email data type: {type(email_data)}")
            if isinstance(email_data, dict):
                self.logger.info(f"Email data keys: {list(email_data.keys())}")
                if 'payload' in email_data:
                    self.logger.info(f"Payload type: {type(email_data['payload'])}")
            
            # Handle string input
            if isinstance(email_data, str):
                try:
                    self.logger.info(f"Attempting to parse string email data: {email_data[:100]}...")
                    email_data = json.loads(email_data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse email_data string as JSON: {e}")
                    return False
            
            if not isinstance(email_data, dict):
                self.logger.error(f"Invalid email data type: {type(email_data)}")
                return False
            
            # Extract and validate required fields
            msg_id = email_data.get('id')
            if not msg_id:
                self.logger.error("Missing required field: id")
                return False
                
            # Extract headers
            payload = email_data.get('payload')
            if not isinstance(payload, dict):
                self.logger.error(f"Invalid payload type: {type(payload)}")
                return False
                
            headers = {
                header['name'].lower(): header['value']
                for header in payload.get('headers', [])
            }
            
            # Parse addresses
            from_str = headers.get('from', '')
            if '<' in from_str:
                from_name = from_str.split('<')[0].strip(' "\'')
                from_email = from_str.split('<')[1].split('>')[0].strip()
            else:
                from_name = ''
                from_email = from_str.strip()
            
            # Check if email already exists
            result = conn.execute(
                "SELECT msg_id FROM emails WHERE msg_id = ?", 
                [msg_id]
            ).fetchone()
            
            if result:
                self.logger.info(f"Email {msg_id} already exists, skipping")
                return False
            
            # Extract body and attachments
            body = self.extract_body(payload)  # Now returns a dict with 'text' and 'html'
            attachments = self.extract_attachments(payload)
            
            # Parse email date
            try:
                received_date = self.parse_email_date(headers.get('date', ''))
            except ValueError as e:
                self.logger.warning(f"Failed to parse date for email {msg_id}: {e}")
                received_date = datetime.fromtimestamp(int(email_data.get('internalDate', '0'))/1000)
            
            # Prepare data for insertion
            insert_data = {
                'msg_id': msg_id,
                'thread_id': email_data.get('threadId'),
                'subject': headers.get('subject', ''),
                'from_address': from_email,
                'analysis_date': datetime.now().isoformat(),
                'raw_analysis': json.dumps(email_data),
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
                    'body_text': body['text'],
                    'body_html': body['html']
                }),
                'priority': 0,  # Will be set by enrichment
                'label_ids': json.dumps(email_data.get('labelIds', [])),
                'snippet': email_data.get('snippet', ''),
                'internal_date': int(email_data.get('internalDate', 0)),
                'size_estimate': email_data.get('sizeEstimate', 0),
                'message_parts': json.dumps(payload),
                'draft_id': None,  # Will be set if this is a draft
                'draft_message': None,  # Will be set if this is a draft
                'attachments': json.dumps(attachments),
                'status': 'new',
                'error_message': None,
                'batch_id': batch_id,
                'import_timestamp': datetime.now().isoformat()
            }
            
            # Insert the email
            placeholders = ', '.join(['?' for _ in insert_data])
            columns = ', '.join(insert_data.keys())
            
            conn.execute(f"""
            INSERT INTO emails ({columns})
            VALUES ({placeholders})
            """, list(insert_data.values()))
            
            self.logger.info(f"Stored email {msg_id} successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing email {email_data.get('id', 'unknown')}: {e}")
            return False

    def parse_email_date(self, date_str):
        """Parse email date string to datetime object.
        
        Args:
            date_str: Date string from email header
            
        Returns:
            datetime object
        """
        # Try various date formats
        for date_format in [
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 2822 format
            '%a, %d %b %Y %H:%M:%S %Z',  # RFC 2822 with timezone name
            '%d %b %Y %H:%M:%S %z',      # Without day of week
            '%a, %d %b %Y %H:%M:%S',     # Without timezone
        ]:
            try:
                return datetime.strptime(date_str, date_format)
            except ValueError:
                continue
            
        # If all formats fail, use dateutil parser as fallback
        try:
            # Remove parenthetical timezone names like (UTC), (EDT) etc
            cleaned_date_str = ' '.join([part for part in date_str.split(' ') if not (part.startswith('(') and part.endswith(')'))])
            return date_parser.parse(cleaned_date_str)
        except Exception as e:
            raise ValueError(f"Could not parse date string: {date_str}") from e

    def run(self) -> None:
        """Main execution method."""
        try:
            # Access command-line arguments
            args = self.parse_args()

            # Build Gmail service
            service = self.build_gmail_service(args.user_email)

            # Get database connection
            if self.db_conn is None:
                raise ValueError("Database connection not initialized.")
            
            # Create emails table
            self._create_emails_table(self.db_conn)

            # Fetch emails
            days_back = args.days_back
            max_emails = args.max_emails
            historical = args.historical
            include_sent = args.include_sent

            self.logger.info(f"Starting email import for the past {days_back} days")
            email_ids = self.fetch_emails(
                service,
                self.db_conn,
                days_back=days_back,
                max_emails=max_emails,
                user_id="me",
                historical=historical,
                include_sent=include_sent
            )

            # Fetch and store emails
            batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            email_batch = []
            for msg_id in email_ids:
                email = self.fetch_email(service, msg_id)
                if email:
                    email_batch.append(email)

            # Store emails in batch
            if email_batch:
                success_count, error_count = self.store_emails_batch(self.db_conn, email_batch, batch_id)
                self.logger.info(f"Successfully stored {success_count} emails, {error_count} errors.")
            else:
                self.logger.info("No new emails to store.")

            self.logger.info("Email import completed")

        except Exception as e:
            self.logger.error(f"Error in run method: {e}")
            raise

def main():
    """Main entry point for the script."""
    importer = GmailImporter()
    importer.execute()

if __name__ == "__main__":
    main()
