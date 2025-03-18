#!/usr/bin/env python3
"""
Simple Gmail Email Import Script
===============================

This script imports emails from Gmail using gcloud CLI authentication,
without depending on the email_classifier module.
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache
import duckdb
from dateutil import parser as date_parser

from dewey.core.db.config import get_db_config, validate_config
from dewey.utils import get_logger

# Disable file cache warning
class MemoryCache(Cache):
    _CACHE = {}

    def get(self, url):
        return MemoryCache._CACHE.get(url)

    def set(self, url, content):
        MemoryCache._CACHE[url] = content

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"gmail_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("gmail_import")

# Email analysis table schema
EMAIL_ANALYSES_SCHEMA = """
CREATE TABLE IF NOT EXISTS email_analyses (
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
    attachments JSON
)
"""


def get_db_connection(db_path: str, max_retries: int = 3, retry_delay: int = 5) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB/MotherDuck connection with retry logic.
    
    Args:
        db_path: Path to the database file or MotherDuck connection string
        max_retries: Maximum number of connection attempts
        retry_delay: Delay in seconds between retries
        
    Returns:
        A DuckDB connection
        
    Raises:
        ValueError: If MOTHERDUCK_TOKEN is not set when using MotherDuck
        Exception: If connection fails after max retries
    """
    for attempt in range(max_retries):
        try:
            # Check if using MotherDuck
            if db_path.startswith('md:'):
                logger.info(f"Connecting to MotherDuck database: {db_path}")
                # Get token from environment variable
                token = os.getenv('MOTHERDUCK_TOKEN')
                if not token:
                    raise ValueError(
                        "MOTHERDUCK_TOKEN environment variable not set. "
                        "Please set it using: export MOTHERDUCK_TOKEN='your_token'"
                    )
                
                if token.strip() == '':
                    raise ValueError("MOTHERDUCK_TOKEN environment variable is empty")
                    
                # Set up MotherDuck connection with token validation
                try:
                    conn = duckdb.connect(db_path, config={'motherduck_token': token})
                    # Test the connection
                    conn.execute("SELECT 1")
                    logger.info("Successfully connected to MotherDuck")
                except Exception as e:
                    if "token" in str(e).lower():
                        raise ValueError(
                            f"Invalid MotherDuck token. Please check your token is correct. Error: {e}"
                        )
                    raise
            else:
                # Local DuckDB connection
                logger.info(f"Connecting to local database: {db_path}")
                os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
                conn = duckdb.connect(db_path)
            
            # Drop and recreate email_analyses table
            try:
                conn.execute("DROP TABLE IF EXISTS email_analyses")
                logger.info("Dropped existing email_analyses table")
            except Exception as e:
                logger.warning(f"Failed to drop table: {e}")
            
            # Create email_analyses table with correct schema
            conn.execute("""
            CREATE TABLE IF NOT EXISTS email_analyses (
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
            logger.info("Created email_analyses table with updated schema")
            
            # Create indexes
            for idx in [
                "CREATE INDEX IF NOT EXISTS idx_email_analyses_thread_id ON email_analyses(thread_id)",
                "CREATE INDEX IF NOT EXISTS idx_email_analyses_from_address ON email_analyses(from_address)",
                "CREATE INDEX IF NOT EXISTS idx_email_analyses_internal_date ON email_analyses(internal_date)",
                "CREATE INDEX IF NOT EXISTS idx_email_analyses_status ON email_analyses(status)",
                "CREATE INDEX IF NOT EXISTS idx_email_analyses_batch_id ON email_analyses(batch_id)",
                "CREATE INDEX IF NOT EXISTS idx_email_analyses_import_timestamp ON email_analyses(import_timestamp)"
            ]:
                try:
                    conn.execute(idx)
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")
            
            return conn
            
        except Exception as e:
            if "Conflicting lock" in str(e):
                if attempt < max_retries - 1:
                    logger.warning(f"Database lock conflict, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
            raise
            
    raise Exception(f"Failed to connect to database after {max_retries} attempts")


def build_gmail_service(user_email: Optional[str] = None):
    """Build the Gmail API service.
    
    Args:
        user_email: Email address to impersonate (for domain-wide delegation)
        
    Returns:
        Gmail API service
    """
    try:
        # Define the scopes
        SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',
            # We no longer need just metadata since we're fetching full messages
            # 'https://www.googleapis.com/auth/gmail.metadata'
        ]
        
        # Path to credentials file - use absolute path
        credentials_path = os.path.expanduser("~/dewey/credentials.json")
        token_path = os.path.expanduser("~/dewey/token.json")
        
        credentials = None
        
        # Check if we have a token file
        if os.path.exists(token_path):
            logger.info(f"Using token from {token_path}")
            credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # If no valid credentials, and we have a credentials file
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                logger.info("Refreshing expired credentials")
                credentials.refresh(Request())
            elif os.path.exists(credentials_path):
                logger.info(f"Using credentials from {credentials_path}")
                
                # Load the raw JSON to inspect its format
                try:
                    with open(credentials_path, 'r') as f:
                        creds_data = json.load(f)
                        
                    logger.info(f"Credentials file format: {list(creds_data.keys())}")
                    
                    # Check if it's a token file (has 'access_token' field)
                    if 'access_token' in creds_data:
                        logger.info("Using access token from credentials file")
                        
                        # Create credentials from the token
                        credentials = Credentials(
                            token=creds_data.get('access_token'),
                            refresh_token=creds_data.get('refresh_token'),
                            token_uri=creds_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                            client_id=creds_data.get('client_id', ''),
                            client_secret=creds_data.get('client_secret', '')
                        )
                        
                    # Check if it's an API key
                    elif 'api_key' in creds_data:
                        logger.info("Using API key from credentials file")
                        # Use API key authentication
                        return build('gmail', 'v1', developerKey=creds_data['api_key'], cache=MemoryCache())
                        
                    # Check if it's a service account key file
                    elif 'type' in creds_data and creds_data['type'] == 'service_account':
                        logger.info("Using service account from credentials file")
                        credentials = service_account.Credentials.from_service_account_info(
                            creds_data,
                            scopes=SCOPES
                        )
                        
                        # If user_email is provided, use domain-wide delegation
                        if user_email and hasattr(credentials, 'with_subject'):
                            credentials = credentials.with_subject(user_email)
                            
                    # Check if it's an OAuth client credentials file
                    elif 'installed' in creds_data or 'web' in creds_data:
                        logger.info("Using OAuth client credentials from credentials file")
                        
                        # Create a flow from the credentials file
                        flow = InstalledAppFlow.from_client_secrets_file(
                            credentials_path,
                            SCOPES
                        )
                        
                        # Run the OAuth flow to get credentials
                        credentials = flow.run_local_server(port=0)
                        
                        # Save the credentials for future use
                        with open(token_path, 'w') as token:
                            token.write(credentials.to_json())
                            logger.info(f"Saved token to {token_path}")
                            
                    else:
                        logger.warning("Unknown credentials format, falling back to application default credentials")
                        credentials, _ = google.auth.default(
                            scopes=SCOPES + ['https://www.googleapis.com/auth/cloud-platform']
                        )
                        
                except Exception as e:
                    logger.warning(f"Failed to parse credentials file: {e}")
                    logger.info("Using application default credentials")
                    credentials, _ = google.auth.default(
                        scopes=SCOPES + ['https://www.googleapis.com/auth/cloud-platform']
                    )
            else:
                logger.warning(f"Credentials file not found at {credentials_path}")
                logger.info("Using application default credentials")
                # Use application default credentials from gcloud CLI
                credentials, _ = google.auth.default(
                    scopes=SCOPES + ['https://www.googleapis.com/auth/cloud-platform']
                )
        
        # Build the service with memory cache
        return build('gmail', 'v1', credentials=credentials, cache=MemoryCache())
    except Exception as e:
        logger.error(f"Failed to build Gmail service: {e}")
        raise


def fetch_emails(service, days_back=7, max_emails=100, user_id="me", historical=False, include_sent=True):
    """Fetch emails from Gmail API.
    
    Args:
        service: Gmail API service
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
            
            logger.info(f"Importing emails from {start_date_str} to {end_date_str}")
        else:
            logger.info("Importing all historical emails")
        
        # Prepare query for sent items if needed
        query = None
        if include_sent:
            logger.info("Including sent emails")
        
        # Fetch all messages in batches
        all_messages = []
        page_token = None
        total_fetched = 0
        
        while True:
            try:
                # Fetch a batch of messages
                results = service.users().messages().list(
                    userId=user_id,
                    maxResults=min(max_emails, 500),  # API limit is 500
                    pageToken=page_token,
                    q=query
                ).execute()
                
                messages = results.get('messages', [])
                if not messages:
                    break
                    
                all_messages.extend(messages)
                total_fetched += len(messages)
                
                logger.info(f"Fetched {len(messages)} messages, total: {total_fetched}")
                
                # Check if we've reached the max
                if not historical and total_fetched >= max_emails:
                    break
                    
                # Get the next page token
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
                # Add a small delay to avoid rate limiting
                time.sleep(0.5)  # Increased delay to avoid rate limiting
            except Exception as e:
                logger.warning(f"Error fetching batch of messages: {e}")
                # If we hit a rate limit or other temporary error, wait and retry
                if "Rate Limit Exceeded" in str(e) or "quota" in str(e).lower():
                    wait_time = 60  # Wait 60 seconds before retrying
                    logger.info(f"Rate limit exceeded. Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    # For other errors, log and continue with what we have
                    logger.error(f"Error fetching messages: {e}")
                    break
        
        if not all_messages:
            logger.info("No emails found.")
            return []
            
        logger.info(f"Found {len(all_messages)} emails, fetching details...")
        
        # Get full message details and filter by date if needed
        email_ids = []
        processed_count = 0
        
        for message in all_messages:
            processed_count += 1
            if processed_count % 10 == 0:
                logger.info(f"Processing message {processed_count}/{len(all_messages)}")
                
            msg_id = message['id']
            
            # If we're not doing a historical import, we need to check the date
            if not historical:
                try:
                    # Fetch the message to get headers
                    msg = fetch_email(service, msg_id, user_id)
                    if not msg:
                        continue
                    
                    # Extract date from headers
                    date_header = None
                    for header in msg['payload']['headers']:
                        if header['name'].lower() == 'date':
                            date_header = header['value']
                            break
                            
                    if date_header:
                        try:
                            # Parse the date (handling various formats)
                            email_date = parse_email_date(date_header)
                            
                            # Remove timezone info for comparison
                            if email_date.tzinfo:
                                email_date = email_date.replace(tzinfo=None)
                            
                            # Check if the email is within our date range
                            if start_date <= email_date <= end_date:
                                email_ids.append(msg_id)
                                
                            if len(email_ids) >= max_emails:
                                break
                        except Exception as e:
                            logger.warning(f"Failed to parse date '{date_header}': {e}")
                            # Include the email if we can't parse the date
                            email_ids.append(msg_id)
                    else:
                        # Include the email if we can't find the date header
                        email_ids.append(msg_id)
                except Exception as e:
                    logger.warning(f"Error processing message {msg_id}: {e}")
                    # If we hit a rate limit, wait and retry
                    if "Rate Limit Exceeded" in str(e) or "quota" in str(e).lower():
                        wait_time = 60  # Wait 60 seconds before retrying
                        logger.info(f"Rate limit exceeded. Waiting {wait_time} seconds before retrying...")
                        time.sleep(wait_time)
                        # Try again with this message
                        try:
                            msg = fetch_email(service, msg_id, user_id)
                            if msg:
                                email_ids.append(msg_id)
                        except:
                            # If it fails again, skip this message
                            pass
            else:
                # For historical import, include all emails
                email_ids.append(msg_id)
                
            # Check if we've reached the max
            if not historical and len(email_ids) >= max_emails:
                break
                
            # Add a small delay to avoid rate limiting
            time.sleep(0.2)
                
        return email_ids
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return []


def fetch_email(service, msg_id, user_id='me'):
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
        logger.error(f"Error fetching message {msg_id}: {e}")
        return None


def parse_email(message: Dict) -> Dict[str, Any]:
    """Parse a Gmail message into a structured dictionary.
    
    Args:
        message: Gmail message object
        
    Returns:
        Structured email data
    """
    headers = {header['name'].lower(): header['value'] 
              for header in message.get('payload', {}).get('headers', [])}
    
    # Extract body
    body = extract_body(message.get('payload', {}))
    
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
        'attachments': extract_attachments(message.get('payload', {}))
    }
    
    return email_data


def extract_body(payload: Dict) -> Dict[str, str]:
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
                logger.warning(f"Failed to decode email part: {e}")
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


def extract_attachments(payload: Dict) -> List[Dict[str, Any]]:
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
            attachments.extend(extract_attachments(part))
    
    return attachments


def store_emails_batch(conn, email_batch, batch_id: str):
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
                        if store_email(conn, email_data, batch_id):
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        logger.error(f"Error storing email: {e}")
                        error_count += 1
                        continue
                
                # Commit each sub-batch
                conn.execute("COMMIT")
                conn.execute("BEGIN TRANSACTION")
                
                logger.info(f"Processed sub-batch {i//sub_batch_size + 1}, "
                          f"Success: {success_count}, Errors: {error_count}")
            
            # Final commit
            conn.execute("COMMIT")
            break
            
        except Exception as e:
            retry_count += 1
            conn.execute("ROLLBACK")
            
            if retry_count < max_retries:
                wait_time = retry_count * 5  # Exponential backoff
                logger.warning(f"Batch failed, retrying in {wait_time} seconds... ({retry_count}/{max_retries})")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to process batch after {max_retries} attempts")
                raise
    
    return success_count, error_count


def store_email(conn, email_data, batch_id: str):
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
        logger.info(f"Email data type: {type(email_data)}")
        if isinstance(email_data, dict):
            logger.info(f"Email data keys: {list(email_data.keys())}")
            if 'payload' in email_data:
                logger.info(f"Payload type: {type(email_data['payload'])}")
        
        # Handle string input
        if isinstance(email_data, str):
            try:
                logger.info(f"Attempting to parse string email data: {email_data[:100]}...")
                email_data = json.loads(email_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse email_data string as JSON: {e}")
                return False
        
        if not isinstance(email_data, dict):
            logger.error(f"Invalid email data type: {type(email_data)}")
            return False
        
        # Extract and validate required fields
        msg_id = email_data.get('id')
        if not msg_id:
            logger.error("Missing required field: id")
            return False
            
        # Extract headers
        payload = email_data.get('payload')
        if not isinstance(payload, dict):
            logger.error(f"Invalid payload type: {type(payload)}")
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
            "SELECT msg_id FROM email_analyses WHERE msg_id = ?", 
            [msg_id]
        ).fetchone()
        
        if result:
            logger.info(f"Email {msg_id} already exists, skipping")
            return False
        
        # Extract body and attachments
        body = extract_body(payload)  # Now returns a dict with 'text' and 'html'
        attachments = extract_attachments(payload)
        
        # Parse email date
        try:
            received_date = parse_email_date(headers.get('date', ''))
        except ValueError as e:
            logger.warning(f"Failed to parse date for email {msg_id}: {e}")
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
        INSERT INTO email_analyses ({columns})
        VALUES ({placeholders})
        """, list(insert_data.values()))
        
        logger.info(f"Stored email {msg_id} successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error storing email {email_data.get('id', 'unknown')}: {e}")
        return False


def parse_email_date(date_str):
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


def main(args):
    """Run the Gmail import process with improved error handling."""
    try:
        # Get database configuration
        db_config = get_db_config()
        if not validate_config():
            logger.error("Invalid database configuration")
            sys.exit(1)

        # Use MotherDuck connection string if available
        db_path = args.db or db_config.get('motherduck_db') or db_config['local_db_path']
        if not db_path.startswith('md:'):
            db_path = os.path.expanduser(db_path)

        # Connect to database with retry logic
        conn = get_db_connection(db_path)
        logger.info(f"Connected to database at {db_path}")
        
        # Generate unique batch ID
        batch_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
        
        try:
            # Rest of the main function remains similar, but pass batch_id to store_emails_batch
            service = build_gmail_service(args.user)
            email_ids = fetch_emails(
                service, 
                days_back=args.days, 
                max_emails=args.max, 
                user_id=args.user_id,
                historical=args.historical,
                include_sent=not args.no_sent
            )
            
            total_emails = len(email_ids)
            logger.info(f"Found {total_emails} emails to process")
            
            # Process in batches
            start_idx = args.start_from
            while start_idx < total_emails:
                end_idx = min(start_idx + args.batch_size, total_emails)
                batch = email_ids[start_idx:end_idx]
                
                # Fetch emails for this batch
                email_batch = []
                for email_id in batch:
                    try:
                        msg = fetch_email(service, email_id, args.user_id)
                        if msg:
                            email_batch.append(msg)
                        time.sleep(0.2)  # Rate limiting
                    except Exception as e:
                        logger.error(f"Error fetching email {email_id}: {e}")
                        if "Rate Limit Exceeded" in str(e):
                            time.sleep(60)  # Wait longer on rate limit
                
                # Store the batch
                if email_batch:
                    success_count, error_count = store_emails_batch(conn, email_batch, batch_id)
                    logger.info(f"Batch {start_idx}-{end_idx}: Success={success_count}, Errors={error_count}")
                
                start_idx = end_idx
                
                # Add delay between batches
                if start_idx < total_emails:
                    time.sleep(5)
            
            logger.info(f"Import batch {batch_id} completed successfully")
            
        finally:
            # Always close the connection
            conn.close()
            logger.info("Database connection closed")
        
    except Exception as e:
        logger.error(f"Gmail import failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import emails from Gmail")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--max", type=int, default=1000, help="Maximum number of emails to import")
    parser.add_argument("--user", type=str, help="User email to impersonate (for domain-wide delegation)")
    parser.add_argument("--user-id", type=str, default="me", help="User ID to fetch emails for (default: 'me')")
    parser.add_argument("--db", type=str, help="Path to the database file (overrides central config)")
    parser.add_argument("--historical", action="store_true", help="Import all historical emails")
    parser.add_argument("--no-sent", action="store_true", help="Exclude sent emails")
    parser.add_argument("--checkpoint", action="store_true", help="Use checkpoint to resume interrupted imports")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of emails to process in each batch")
    parser.add_argument("--start-from", type=int, default=0, help="Start processing from this index")
    
    args = parser.parse_args()
    
    main(args) 