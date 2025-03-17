"""Gmail Service for CRM
===================

Provides Gmail integration for CRM using gcloud CLI authentication.
"""

import base64
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import google.auth
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Update imports to use the new database module
from ...db import initialize_crm_database, store_email, store_contact
from ..email_classifier.email_classifier import EmailClassifier

logger = logging.getLogger(__name__)


class GmailService:
    """Gmail service using gcloud CLI authentication for CRM.
    
    This service provides functionality to:
    1. Authenticate with Gmail API using gcloud CLI credentials
    2. Email fetching and processing
    3. Contact extraction and enrichment
    4. Email classification and prioritization
    
    Example:
        ```python
        service = GmailService()
        service.import_emails(days=7)  # Import last 7 days of emails
        ```
    """
    
    def __init__(
        self,
        user_email: Optional[str] = None,
        checkpoint_file: str = "gmail_checkpoint.json",
        batch_size: int = 100,
        database_name: str = "crm.duckdb",
        data_dir: Optional[str] = None,
        existing_db_path: Optional[str] = None
    ):
        """Initialize the Gmail service.
        
        Args:
            user_email: Email address to impersonate (for domain-wide delegation)
            checkpoint_file: Path to checkpoint file
            batch_size: Number of emails to fetch in each batch
            database_name: Name of the database file
            data_dir: Directory to store the database file
            existing_db_path: Path to an existing database file to use
        """
        self.user_email = user_email
        self.checkpoint_file = checkpoint_file
        self.batch_size = batch_size
        self.service = self._build_service()
        self.classifier = EmailClassifier()
        
        # Initialize database connection
        if existing_db_path and os.path.exists(existing_db_path):
            logger.info(f"Using existing database at {existing_db_path}")
            self.db_conn = initialize_crm_database(
                database_name=database_name,
                data_dir=data_dir,
                existing_db_path=existing_db_path
            )
        else:
            self.db_conn = initialize_crm_database(
                database_name=database_name,
                data_dir=data_dir
            )
        
    def _build_service(self):
        """Build the Gmail API service."""
        try:
            # Use application default credentials from gcloud CLI
            credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/gmail.readonly'])
            
            # If user_email is provided, use domain-wide delegation
            if self.user_email and hasattr(credentials, 'with_subject'):
                credentials = credentials.with_subject(self.user_email)
                
            # Refresh credentials if needed
            credentials.refresh(Request())
            
            # Build the service
            return build('gmail', 'v1', credentials=credentials)
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            raise
    
    def authenticate(self) -> None:
        """Authenticate with Gmail API using Application Default Credentials.
        
        This method is called automatically when the service is initialized.
        It uses the gcloud CLI credentials to authenticate with the Gmail API.
        """
        try:
            # Test the connection
            self.service.users().getProfile(userId='me').execute()
            logger.info("Successfully authenticated with Gmail API")
        except Exception as e:
            logger.error(f"Failed to authenticate with Gmail API: {e}")
            raise
    
    def import_emails(self, days: int = 7, max_emails: int = 1000) -> int:
        """Import emails from the last N days.
        
        Args:
            days: Number of days to look back
            max_emails: Maximum number of emails to import
            
        Returns:
            Number of emails imported
        """
        # Calculate the date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format the date range for Gmail API
        date_format = "%Y/%m/%d"
        query = f"after:{start_date.strftime(date_format)} before:{end_date.strftime(date_format)}"
        
        logger.info(f"Importing emails from {start_date.strftime(date_format)} to {end_date.strftime(date_format)}")
        
        # Fetch emails
        try:
            emails = self.fetch_emails(query=query, max_results=max_emails)
            
            # Process and store emails
            imported_count = 0
            for email in emails:
                try:
                    self._process_and_store_email(email)
                    imported_count += 1
                except Exception as e:
                    logger.error(f"Error processing email {email.get('id')}: {e}")
            
            logger.info(f"Imported {imported_count} emails")
            return imported_count
            
        except Exception as e:
            logger.error(f"Error importing emails: {e}")
            return 0
    
    def fetch_emails(self, query: str = "", max_results: int = 100) -> List[Dict[str, Any]]:
        """Fetch emails from Gmail API.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email data dictionaries
        """
        try:
            # Get message IDs
            results = []
            page_token = None
            
            while len(results) < max_results:
                # Fetch a batch of message IDs
                response = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=min(self.batch_size, max_results - len(results)),
                    pageToken=page_token
                ).execute()
                
                messages = response.get('messages', [])
                if not messages:
                    break
                
                # Fetch full message data for each ID
                for message in messages:
                    msg_data = self._fetch_email(message['id'])
                    if msg_data:
                        results.append(msg_data)
                
                # Check if there are more pages
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                
                # Rate limiting
                time.sleep(0.1)
            
            logger.info(f"Fetched {len(results)} emails")
            return results
            
        except HttpError as error:
            logger.error(f"Error fetching emails: {error}")
            return []
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def _fetch_email(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single email by ID.
        
        Args:
            msg_id: Gmail message ID
            
        Returns:
            Parsed email data dictionary or None if error
        """
        try:
            # Fetch the full message
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            
            return self._parse_email(message)
            
        except Exception as e:
            logger.error(f"Error fetching email {msg_id}: {e}")
            return None
    
    def _parse_email(self, message: Dict) -> Dict[str, Any]:
        """Parse a Gmail message into a structured dictionary.
        
        Args:
            message: Gmail message object
            
        Returns:
            Structured email data
        """
        headers = {header['name'].lower(): header['value'] 
                  for header in message.get('payload', {}).get('headers', [])}
        
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
            'body': self._extract_body(message.get('payload', {})),
            'attachments': self._extract_attachments(message.get('payload', {}))
        }
        
        return email_data
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract the email body from the payload.
        
        Args:
            payload: Gmail message payload
            
        Returns:
            Email body as text
        """
        if not payload:
            return ""
        
        # Check if this part has a body
        if 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            text = base64.urlsafe_b64decode(data).decode('utf-8')
            return text
        
        # Check for multipart
        if 'parts' in payload:
            text_parts = []
            for part in payload['parts']:
                # Prefer text/plain parts
                if part.get('mimeType') == 'text/plain':
                    if 'body' in part and 'data' in part['body']:
                        data = part['body']['data']
                        text = base64.urlsafe_b64decode(data).decode('utf-8')
                        text_parts.append(text)
                # Fallback to text/html
                elif part.get('mimeType') == 'text/html':
                    if 'body' in part and 'data' in part['body']:
                        data = part['body']['data']
                        text = base64.urlsafe_b64decode(data).decode('utf-8')
                        text_parts.append(text)
                # Recursive for nested multipart
                elif 'parts' in part:
                    text_parts.append(self._extract_body(part))
            
            return "\n".join(text_parts)
        
        return ""
    
    def _extract_attachments(self, payload: Dict) -> List[Dict[str, Any]]:
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
                attachments.extend(self._extract_attachments(part))
        
        return attachments
    
    def _process_and_store_email(self, email_data: Dict[str, Any]) -> None:
        """Process and store an email in the database.
        
        Args:
            email_data: Parsed email data
        """
        # Extract sender information
        from_email = self._extract_email(email_data.get('from', ''))
        from_name = self._extract_name(email_data.get('from', ''))
        
        # Parse date
        try:
            if email_data.get('internalDate'):
                date = datetime.fromtimestamp(int(email_data['internalDate']) / 1000)
            else:
                # Fallback to header date
                date = datetime.strptime(email_data['date'], '%a, %d %b %Y %H:%M:%S %z')
        except (ValueError, TypeError):
            date = datetime.now()
        
        # Store contact if email is available
        if from_email:
            contact_data = {
                'name': from_name,
                'email': from_email,
                'first_seen': date,
                'last_seen': date
            }
            store_contact(self.db_conn, contact_data)
        
        # Classify email
        priority_score = 0
        if email_data.get('body'):
            classification = self.classifier.classify_email(
                subject=email_data.get('subject', ''),
                body=email_data.get('body', '')
            )
            priority_score = classification.get('priority', 0)
        
        # Prepare email data for storage
        storage_data = {
            'id': email_data['id'],
            'threadId': email_data['threadId'],
            'subject': email_data.get('subject', ''),
            'from': email_data.get('from', ''),
            'analysis_date': datetime.now().isoformat(),
            'priority': priority_score,
            'labelIds': email_data.get('labelIds', []),
            'snippet': email_data.get('snippet', ''),
            'internalDate': email_data.get('internalDate', 0),
            'sizeEstimate': email_data.get('sizeEstimate', 0)
        }
        
        # Store email
        store_email(self.db_conn, storage_data)
    
    def _extract_email(self, address_string: str) -> Optional[str]:
        """Extract email address from a string.
        
        Args:
            address_string: Email address string (e.g., "John Doe <john@example.com>")
            
        Returns:
            Email address or None if not found
        """
        if not address_string:
            return None
        
        # Check for angle brackets format
        import re
        match = re.search(r'<([^>]+)>', address_string)
        if match:
            return match.group(1)
        
        # If no angle brackets, try to find anything that looks like an email
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', address_string)
        if match:
            return match.group(0)
        
        return None
    
    def _extract_name(self, address_string: str) -> Optional[str]:
        """Extract name from an email address string.
        
        Args:
            address_string: Email address string (e.g., "John Doe <john@example.com>")
            
        Returns:
            Name or None if not found
        """
        if not address_string:
            return None
        
        # Check for angle brackets format
        import re
        match = re.search(r'^([^<]+)<', address_string)
        if match:
            return match.group(1).strip()
        
        return None 