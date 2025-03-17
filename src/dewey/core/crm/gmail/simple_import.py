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
from dateutil import parser

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


def get_db_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        A DuckDB connection
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    
    # Connect to the database
    conn = duckdb.connect(db_path)
    
    # Create the table if it doesn't exist
    conn.execute(EMAIL_ANALYSES_SCHEMA)
    
    return conn


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


def fetch_email(service, msg_id, user_id="me"):
    """Fetch a single email from Gmail API.
    
    Args:
        service: Gmail API service
        msg_id: Message ID
        user_id: User ID (default: "me")
        
    Returns:
        Email data dictionary
    """
    try:
        # Request full message format to get content
        message = service.users().messages().get(
            userId=user_id,
            id=msg_id,
            format='full'
        ).execute()
        
        return message
    except Exception as e:
        logger.error(f"Error fetching email {msg_id}: {e}")
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
        'body': extract_body(message.get('payload', {})),
        'attachments': extract_attachments(message.get('payload', {}))
    }
    
    return email_data


def extract_body(payload: Dict) -> str:
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
                text_parts.append(extract_body(part))
        
        return "\n".join(text_parts)
    
    return ""


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


def store_email(conn, email_data):
    """Store email data in DuckDB.
    
    Args:
        conn: DuckDB connection
        email_data: Email data dictionary from Gmail API
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract email metadata
        email_id = email_data.get('id')
        thread_id = email_data.get('threadId')
        
        # Extract headers
        headers = {}
        for header in email_data.get('payload', {}).get('headers', []):
            headers[header['name'].lower()] = header['value']
            
        # Extract basic email fields
        from_email = headers.get('from', '')
        to_email = headers.get('to', '')
        cc_email = headers.get('cc', '')
        bcc_email = headers.get('bcc', '')
        subject = headers.get('subject', '')
        date_str = headers.get('date', '')
        
        # Parse date
        try:
            date = parse_email_date(date_str) if date_str else None
            date_str = date.isoformat() if date else None
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            date_str = None
            
        # Extract labels
        labels = email_data.get('labelIds', [])
        labels_str = ','.join(labels) if labels else None
        
        # Extract message body
        body = extract_body(email_data.get('payload', {}))
        
        # Extract attachments
        attachments = extract_attachments(email_data.get('payload', {}))
        
        # Create emails table if it doesn't exist
        conn.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id VARCHAR PRIMARY KEY,
            thread_id VARCHAR,
            from_email VARCHAR,
            to_email VARCHAR,
            cc_email VARCHAR,
            bcc_email VARCHAR,
            subject VARCHAR,
            date TIMESTAMP,
            labels VARCHAR,
            snippet VARCHAR,
            body TEXT,
            attachments VARCHAR,
            raw_data VARCHAR
        )
        """)
        
        # Check if email already exists
        result = conn.execute(f"SELECT id FROM emails WHERE id = '{email_id}'").fetchone()
        if result:
            logger.info(f"Email {email_id} already exists in database")
            return False
            
        # Insert email data
        conn.execute("""
        INSERT INTO emails (id, thread_id, from_email, to_email, cc_email, bcc_email, subject, date, labels, snippet, body, attachments, raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            email_id,
            thread_id,
            from_email,
            to_email,
            cc_email,
            bcc_email,
            subject,
            date_str,
            labels_str,
            email_data.get('snippet'),
            body,
            json.dumps(attachments),
            json.dumps(email_data)
        ])
        
        logger.info(f"Stored email {email_id} in database")
        return True
    except Exception as e:
        logger.error(f"Error storing email: {e}")
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
    return parser.parse(date_str)


def main():
    """Run the Gmail import process."""
    parser = argparse.ArgumentParser(description="Import emails from Gmail")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--max", type=int, default=1000, help="Maximum number of emails to import")
    parser.add_argument("--user", type=str, help="User email to impersonate (for domain-wide delegation)")
    parser.add_argument("--user-id", type=str, default="me", help="User ID to fetch emails for (default: 'me')")
    parser.add_argument("--db-path", type=str, default="~/input_data/duckdb_files/emails.duckdb", 
                        help="Path to the database file")
    parser.add_argument("--historical", action="store_true", help="Import all historical emails")
    parser.add_argument("--no-sent", action="store_true", help="Exclude sent emails")
    parser.add_argument("--checkpoint", action="store_true", help="Use checkpoint to resume interrupted imports")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of emails to process in each batch")
    parser.add_argument("--start-from", type=int, default=0, help="Start processing from this index")
    
    args = parser.parse_args()
    
    # Expand the database path
    db_path = os.path.expanduser(args.db_path)
    
    if args.historical:
        logger.info(f"Starting historical Gmail import, max {args.max} emails per batch")
    else:
        logger.info(f"Starting Gmail import: looking back {args.days} days, max {args.max} emails")
    
    logger.info(f"Using database: {db_path}")
    
    try:
        # Get database connection
        conn = get_db_connection(db_path)
        
        # Create checkpoint table if using checkpoints
        if args.checkpoint:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS import_checkpoints (
                id INTEGER PRIMARY KEY,
                last_processed_index INTEGER,
                last_import_time TIMESTAMP
            )
            """)
            
            # Get last checkpoint if it exists
            result = conn.execute("SELECT last_processed_index FROM import_checkpoints ORDER BY id DESC LIMIT 1").fetchone()
            if result and args.start_from == 0:  # Only use checkpoint if start_from not specified
                args.start_from = result[0]
                logger.info(f"Resuming from checkpoint: starting at index {args.start_from}")
        
        # Build Gmail service
        service = build_gmail_service(args.user)
        
        # Fetch emails
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
        
        # Process emails in batches
        start_idx = args.start_from
        end_idx = min(start_idx + args.batch_size, total_emails)
        
        while start_idx < total_emails:
            batch = email_ids[start_idx:end_idx]
            logger.info(f"Processing batch of {len(batch)} emails (indices {start_idx}-{end_idx-1})")
            
            # Process and store emails in this batch
            imported_count = 0
            for email_id in batch:
                try:
                    msg = fetch_email(service, email_id, args.user_id)
                    if msg and store_email(conn, msg):
                        imported_count += 1
                        
                        # Log progress every 10 emails
                        if imported_count % 10 == 0:
                            logger.info(f"Imported {imported_count}/{len(batch)} emails in current batch")
                            
                    # Add a small delay to avoid rate limiting
                    time.sleep(0.2)
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    # If we hit a rate limit, wait and retry
                    if "Rate Limit Exceeded" in str(e) or "quota" in str(e).lower():
                        wait_time = 60  # Wait 60 seconds before retrying
                        logger.info(f"Rate limit exceeded. Waiting {wait_time} seconds before retrying...")
                        time.sleep(wait_time)
                        # Try again with this email
                        try:
                            msg = fetch_email(service, email_id, args.user_id)
                            if msg and store_email(conn, msg):
                                imported_count += 1
                        except:
                            # If it fails again, skip this email
                            pass
            
            logger.info(f"Batch complete. Imported {imported_count}/{len(batch)} emails")
            
            # Update checkpoint
            if args.checkpoint:
                conn.execute("""
                INSERT INTO import_checkpoints (last_processed_index, last_import_time)
                VALUES (?, ?)
                """, [end_idx, datetime.now().isoformat()])
                logger.info(f"Updated checkpoint: processed up to index {end_idx}")
            
            # Move to next batch
            start_idx = end_idx
            end_idx = min(start_idx + args.batch_size, total_emails)
            
            # Add a delay between batches to avoid rate limiting
            if start_idx < total_emails:
                logger.info("Waiting 5 seconds before processing next batch...")
                time.sleep(5)
        
        logger.info(f"Gmail import completed successfully. Processed {total_emails} emails.")
        
    except Exception as e:
        logger.error(f"Gmail import failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 