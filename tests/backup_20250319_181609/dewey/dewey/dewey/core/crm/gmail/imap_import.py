#!/usr/bin/env python3
"""
IMAP Email Import Script
=======================

This script imports emails using IMAP, which is more reliable for bulk imports
than the Gmail API.
"""

import argparse
import email
import imaplib
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
from dateutil import parser as date_parser

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dewey.core.db.config import get_db_config, validate_config

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"imap_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("imap_import")

# Reuse the email table schema
EMAIL_ANALYSES_SCHEMA = """
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
"""

def get_db_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """Reuse the database connection logic from simple_import.py"""
    try:
        if db_path.startswith('md:'):
            logger.info(f"Connecting to MotherDuck database: {db_path}")
            token = os.getenv('MOTHERDUCK_TOKEN')
            if not token:
                raise ValueError("MOTHERDUCK_TOKEN environment variable not set")
            conn = duckdb.connect(db_path, config={'motherduck_token': token})
        else:
            logger.info(f"Connecting to local database: {db_path}")
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            conn = duckdb.connect(db_path)

        # Create emails table if it doesn't exist
        conn.execute(EMAIL_ANALYSES_SCHEMA)
        logger.info("Verified emails table exists with correct schema")

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
                logger.warning(f"Failed to create index: {e}")

        return conn

    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def connect_to_gmail(username: str, password: str) -> imaplib.IMAP4_SSL:
    """Connect to Gmail using IMAP.
    
    Args:
        username: Gmail username
        password: App-specific password
        
    Returns:
        IMAP connection
    """
    try:
        # Connect to Gmail's IMAP server
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(username, password)
        return imap
    except Exception as e:
        logger.error(f"Failed to connect to Gmail: {e}")
        raise

def decode_email_header(header: str) -> str:
    """Decode email header properly handling various encodings.
    
    Args:
        header: Raw email header
        
    Returns:
        Decoded header string
    """
    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            try:
                if encoding:
                    decoded_parts.append(part.decode(encoding))
                else:
                    decoded_parts.append(part.decode())
            except:
                decoded_parts.append(part.decode('utf-8', 'ignore'))
        else:
            decoded_parts.append(str(part))
    return ' '.join(decoded_parts)

def parse_email_message(email_data: bytes) -> Dict[str, Any]:
    """Parse email message from IMAP.
    
    Args:
        email_data: Raw email data
        
    Returns:
        Parsed email data dictionary
    """
    try:
        email_message = email.message_from_bytes(email_data)
        
        # Extract headers
        subject = decode_email_header(email_message['subject'] or '')
        from_addr = decode_email_header(email_message['from'] or '')
        date_str = email_message['date'] or ''
        
        # Parse the date
        try:
            date = date_parser.parse(date_str)
            timestamp = int(date.timestamp() * 1000)
        except:
            timestamp = int(time.time() * 1000)
        
        # Extract body and attachments
        body = {'text': '', 'html': ''}
        attachments = []
        
        def process_part(part):
            if part.get_content_maintype() == 'text':
                content = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                try:
                    decoded_content = content.decode(charset)
                except:
                    decoded_content = content.decode('utf-8', 'ignore')
                
                if part.get_content_subtype() == 'plain':
                    body['text'] = decoded_content
                elif part.get_content_subtype() == 'html':
                    body['html'] = decoded_content
            elif part.get_content_maintype() == 'multipart':
                for subpart in part.get_payload():
                    process_part(subpart)
            else:
                # This is an attachment
                filename = part.get_filename()
                if filename:
                    attachments.append({
                        'filename': decode_email_header(filename),
                        'mimeType': part.get_content_type(),
                        'size': len(part.get_payload(decode=True)),
                        'attachmentId': None  # IMAP doesn't have attachment IDs
                    })
        
        if email_message.is_multipart():
            for part in email_message.get_payload():
                process_part(part)
        else:
            content = email_message.get_payload(decode=True)
            charset = email_message.get_content_charset() or 'utf-8'
            try:
                decoded_content = content.decode(charset)
            except:
                decoded_content = content.decode('utf-8', 'ignore')
            
            if email_message.get_content_type() == 'text/plain':
                body['text'] = decoded_content
            elif email_message.get_content_type() == 'text/html':
                body['html'] = decoded_content
        
        # Create a unique message ID if not present
        msg_id = email_message['message-id']
        if not msg_id:
            msg_id = f"<{timestamp}.{hash(subject + from_addr)}@generated>"
        
        # Extract email address from the From field
        from_email = from_addr
        if '<' in from_addr:
            from_email = from_addr.split('<')[1].split('>')[0].strip()
        
        # Create the email data structure
        email_data = {
            'msg_id': msg_id.strip('<>'),
            'thread_id': email_message['references'] or msg_id,  # Use references for threading if available
            'subject': subject,
            'from_address': from_email,
            'analysis_date': datetime.now().isoformat(),
            'raw_analysis': json.dumps({
                'headers': dict(email_message.items()),
                'body': body,
                'attachments': attachments
            }),
            'metadata': json.dumps({
                'from_name': from_addr.split('<')[0].strip() if '<' in from_addr else '',
                'to_addresses': [addr.strip() for addr in (email_message['to'] or '').split(',') if addr.strip()],
                'cc_addresses': [addr.strip() for addr in (email_message['cc'] or '').split(',') if addr.strip()],
                'bcc_addresses': [addr.strip() for addr in (email_message['bcc'] or '').split(',') if addr.strip()],
                'received_date': date.isoformat() if 'date' in locals() else None,
                'body_text': body['text'],
                'body_html': body['html']
            }),
            'snippet': body['text'][:500] if body['text'] else '',
            'internal_date': timestamp,
            'size_estimate': len(email_data),
            'message_parts': json.dumps(body),
            'attachments': json.dumps(attachments),
            'label_ids': json.dumps([]),  # IMAP doesn't have Gmail labels
            'status': 'new'
        }
        
        return email_data
        
    except Exception as e:
        logger.error(f"Error parsing email: {e}")
        raise

def fetch_emails(imap: imaplib.IMAP4_SSL, conn: duckdb.DuckDBPyConnection,
                days_back: int = 7, max_emails: int = 100, batch_size: int = 10,
                historical: bool = False) -> None:
    """Fetch emails from Gmail using IMAP.
    
    Args:
        imap: IMAP connection
        conn: Database connection
        days_back: Number of days back to fetch
        max_emails: Maximum number of emails to fetch
        batch_size: Number of emails to process in each batch
        historical: Whether to fetch all emails or just recent ones
    """
    try:
        # Get existing message IDs from database
        existing_ids = set()
        try:
            result = conn.execute("SELECT msg_id FROM emails").fetchall()
            existing_ids = {str(row[0]) for row in result}
            logger.info(f"Found {len(existing_ids)} existing messages in database")
        except Exception as e:
            logger.error(f"Error getting existing message IDs: {e}")
        
        # Select the All Mail folder
        imap.select('"[Gmail]/All Mail"')
        
        # Search for all emails if historical, otherwise use date range
        if historical:
            _, message_numbers = imap.search(None, 'ALL')
            logger.debug(f"Found {len(message_numbers[0].split())} total messages")
        else:
            date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            _, message_numbers = imap.search(None, f'SINCE {date}')
            logger.debug(f"Found {len(message_numbers[0].split())} messages since {date}")
        
        message_numbers = [int(num) for num in message_numbers[0].split()]
        total_processed = 0
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Process in batches
        for i in range(0, min(len(message_numbers), max_emails), batch_size):
            batch = message_numbers[i:i + batch_size]
            logger.debug(f"Processing batch of {len(batch)} messages: {batch}")
            
            for num in batch:
                try:
                    # First fetch Gmail-specific IDs
                    logger.debug(f"Fetching Gmail IDs for message {num}")
                    _, msg_data = imap.fetch(str(num), "(X-GM-MSGID X-GM-THRID)")
                    logger.debug(f"Raw Gmail ID response: {msg_data}")
                    
                    if not msg_data or not msg_data[0]:
                        logger.error(f"No Gmail ID data for message {num}")
                        continue
                        
                    # Parse Gmail IDs from response
                    response = msg_data[0].decode('utf-8') if isinstance(msg_data[0], bytes) else str(msg_data[0])
                    logger.debug(f"Decoded Gmail ID response: {response}")
                    
                    # Extract Gmail message ID and thread ID using regex
                    import re
                    msgid_match = re.search(r'X-GM-MSGID\s+(\d+)', response)
                    thrid_match = re.search(r'X-GM-THRID\s+(\d+)', response)
                    
                    if not msgid_match or not thrid_match:
                        logger.error(f"Failed to extract Gmail IDs from response: {response}")
                        continue
                        
                    gmail_msgid = msgid_match.group(1)
                    gmail_thrid = thrid_match.group(1)
                    logger.debug(f"Extracted Gmail IDs - Message: {gmail_msgid}, Thread: {gmail_thrid}")
                    
                    # Skip if message already exists in database
                    if gmail_msgid in existing_ids:
                        logger.debug(f"Message {gmail_msgid} already exists in database, skipping")
                        continue
                    
                    # Now fetch the full message
                    logger.debug(f"Fetching full message {num}")
                    _, msg_data = imap.fetch(str(num), "(RFC822)")
                    if not msg_data or not msg_data[0] or not msg_data[0][1]:
                        logger.error(f"No message data for {num}")
                        continue
                        
                    email_data = parse_email_message(msg_data[0][1])
                    email_data['msg_id'] = gmail_msgid
                    email_data['thread_id'] = gmail_thrid
                    
                    if store_email(conn, email_data, batch_id):
                        total_processed += 1
                        
                except Exception as e:
                    logger.error(f"Error processing message {num}: {str(e)}", exc_info=True)
                    continue
            
            logger.info(f"Processed batch of {len(batch)} messages. Total processed: {total_processed}")
            
            if total_processed >= max_emails:
                break
                
            # Small delay between batches
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in fetch_emails: {str(e)}", exc_info=True)
        raise

def store_email(conn: duckdb.DuckDBPyConnection, email_data: Dict[str, Any], batch_id: str) -> bool:
    """Store email in the database.
    
    Args:
        conn: Database connection
        email_data: Parsed email data
        batch_id: Batch identifier
        
    Returns:
        True if successful
    """
    try:
        # Add batch ID to email data
        email_data['batch_id'] = batch_id
        
        # Prepare column names and values
        columns = ', '.join(email_data.keys())
        placeholders = ', '.join(['?' for _ in email_data])
        values = list(email_data.values())
        
        # Insert into database
        conn.execute(f"""
        INSERT INTO emails ({columns})
        VALUES ({placeholders})
        """, values)
        
        logger.info(f"Stored email {email_data['msg_id']}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing email: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Import emails using IMAP")
    parser.add_argument("--username", required=True, help="Gmail username")
    parser.add_argument("--password", help="App-specific password (or set GOOGLE_APP_PASSWORD env var)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--max", type=int, default=1000, help="Maximum number of emails to import")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of emails per batch")
    parser.add_argument("--db", type=str, help="Database path (default: md:dewey)")
    parser.add_argument("--historical", action="store_true", help="Import all historical emails")
    
    args = parser.parse_args()
    
    try:
        # Get password from args or environment
        password = args.password or os.getenv('GOOGLE_APP_PASSWORD')
        if not password:
            raise ValueError("Password must be provided via --password or GOOGLE_APP_PASSWORD environment variable")
            
        # Connect to database
        db_path = args.db or "md:dewey"
        conn = get_db_connection(db_path)
        logger.info(f"Connected to database at {db_path}")
        
        try:
            # Connect to Gmail
            imap = connect_to_gmail(args.username, password)
            logger.info("Connected to Gmail IMAP")
            
            # Fetch emails
            fetch_emails(
                imap=imap,
                conn=conn,
                days_back=args.days,
                max_emails=args.max,
                batch_size=args.batch_size,
                historical=args.historical
            )
            
        finally:
            conn.close()
            logger.info("Database connection closed")
            
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 