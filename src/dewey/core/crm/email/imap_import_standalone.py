#!/usr/bin/env python3
"""
Standalone IMAP Email Import Script
==================================

This script imports emails using IMAP, with no dependencies on the dewey package structure.
It is more reliable for bulk imports than the Gmail API.
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
from email.message import Message

# Custom JSON encoder to handle non-serializable types like email Header objects
class EmailHeaderEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            # Check if the object has a __str__ method
            if hasattr(obj, '__str__'):
                return str(obj)
            # If we still can't serialize it, fallback to its representation
            return repr(obj)
        except Exception:
            # Last resort
            return "Non-serializable data"

# Configure logging
log_dir = Path("logs")
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

# Email table schema
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
    """Connect to DuckDB/MotherDuck database"""
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

def decode_payload(payload: bytes, charset: Optional[str] = None) -> str:
    """
    Decode email payload bytes to string.
    
    Args:
        payload: The binary payload data
        charset: Character set to use for decoding
        
    Returns:
        Decoded string
    """
    if not payload:
        return ""
    
    if not charset:
        charset = "utf-8"  # Default to UTF-8
    
    try:
        return payload.decode(charset)
    except (UnicodeDecodeError, LookupError):
        # If the specified charset fails, try some fallbacks
        try:
            return payload.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            try:
                return payload.decode("latin1", errors="replace")
            except UnicodeDecodeError:
                return payload.decode("ascii", errors="replace")

def get_message_structure(msg: Message) -> Dict[str, Any]:
    """
    Extract the structure of an email message for analysis.
    
    Args:
        msg: The email message object
        
    Returns:
        Dictionary with message structure information
    """
    if msg.is_multipart():
        parts = []
        for i, part in enumerate(msg.get_payload()):
            part_info = {
                "part_index": i,
                "content_type": part.get_content_type(),
                "charset": part.get_content_charset(),
                "content_disposition": part.get("Content-Disposition", ""),
                "filename": part.get_filename(),
                "size": len(part.as_bytes()) if hasattr(part, "as_bytes") else 0,
            }
            
            if part.is_multipart():
                part_info["subparts"] = get_message_structure(part)
            
            parts.append(part_info)
        
        return {"multipart": True, "parts": parts}
    else:
        return {
            "multipart": False,
            "content_type": msg.get_content_type(),
            "charset": msg.get_content_charset(),
            "content_disposition": msg.get("Content-Disposition", ""),
            "filename": msg.get_filename(),
            "size": len(msg.as_bytes()) if hasattr(msg, "as_bytes") else 0,
        }

def parse_email_message(email_data: bytes) -> Dict[str, Any]:
    """
    Parse email message data into a structured dictionary.
    
    Args:
        email_data: Raw email data
        
    Returns:
        Dictionary containing parsed email data
    """
    # Parse the email message
    msg = email.message_from_bytes(email_data)
    
    # Get basic headers
    subject = decode_email_header(msg["Subject"])
    from_addr = decode_email_header(msg["From"])
    to_addr = decode_email_header(msg["To"])
    date_str = msg["Date"]
    
    # Try to parse the date
    date_obj = None
    if date_str:
        try:
            date_tuple = email.utils.parsedate_tz(date_str)
            if date_tuple:
                date_obj = datetime.datetime.fromtimestamp(
                    email.utils.mktime_tz(date_tuple)
                )
        except Exception:
            pass
    
    # Get message ID
    message_id = msg["Message-ID"]
    
    # Extract email body (both text and HTML)
    body_text = ""
    body_html = ""
    attachments = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            # Skip any multipart/* parts
            if content_type.startswith("multipart"):
                continue
            
            # Handle attachments
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    # Get attachment data
                    payload = part.get_payload(decode=True)
                    attachments.append({
                        "filename": filename,
                        "content_type": content_type,
                        "size": len(payload) if payload else 0,
                    })
                continue
            
            # Try to get the payload
            payload = part.get_payload(decode=True)
            if payload:
                payload_str = decode_payload(payload, part.get_content_charset())
                
                if content_type == "text/plain":
                    body_text += payload_str
                elif content_type == "text/html":
                    body_html += payload_str
    else:
        # Not multipart - get the payload directly
        payload = msg.get_payload(decode=True)
        if payload:
            payload_str = decode_payload(payload, msg.get_content_charset())
            content_type = msg.get_content_type()
            
            if content_type == "text/plain":
                body_text = payload_str
            elif content_type == "text/html":
                body_html = payload_str
    
    # Get all headers for raw analysis
    all_headers = {}
    for key in msg.keys():
        all_headers[key] = msg[key]
    
    # Return structured email data
    result = {
        "subject": subject,
        "from": from_addr,
        "to": to_addr,
        "date": date_obj.isoformat() if date_obj else None,
        "raw_date": date_str,
        "message_id": message_id,
        "body_text": body_text,
        "body_html": body_html,
        "attachments": attachments,
        'raw_analysis': json.dumps({
            "headers": all_headers,
            "structure": get_message_structure(msg),
        }, cls=EmailHeaderEncoder),  # Use the custom encoder for non-serializable objects
    }
    
    return result

def fetch_emails(imap: imaplib.IMAP4_SSL, conn: duckdb.DuckDBPyConnection,
                days_back: int = 7, max_emails: int = 100, batch_size: int = 10,
                historical: bool = False, start_date: str = None, end_date: str = None) -> None:
    """Fetch emails from Gmail using IMAP.
    
    Args:
        imap: IMAP connection
        conn: Database connection
        days_back: Number of days back to fetch
        max_emails: Maximum number of emails to fetch
        batch_size: Number of emails to process in each batch
        historical: Whether to fetch all emails or just recent ones
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
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
        
        # Search for emails based on parameters
        if historical:
            _, message_numbers = imap.search(None, 'ALL')
            logger.debug(f"Found {len(message_numbers[0].split())} total messages")
        elif start_date and end_date:
            # Format dates as DD-MMM-YYYY for IMAP
            start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%b-%Y")
            end = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%b-%Y")
            search_criteria = f'(SINCE {start} BEFORE {end})'
            logger.info(f"Searching with criteria: {search_criteria}")
            _, message_numbers = imap.search(None, search_criteria)
            logger.debug(f"Found {len(message_numbers[0].split())} messages between {start} and {end}")
        else:
            date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            _, message_numbers = imap.search(None, f'SINCE {date}')
            logger.debug(f"Found {len(message_numbers[0].split())} messages since {date}")
        
        message_numbers = [int(num) for num in message_numbers[0].split()]
        total_processed = 0
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        logger.info(f"Processing {min(len(message_numbers), max_emails)} emails in batches of {batch_size}")
        
        # Process in batches
        for i in range(0, min(len(message_numbers), max_emails), batch_size):
            batch = message_numbers[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1} of {len(batch)} messages")
            
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
                        if total_processed % 10 == 0:
                            logger.info(f"Progress: {total_processed}/{min(len(message_numbers), max_emails)} emails processed")
                        
                except Exception as e:
                    logger.error(f"Error processing message {num}: {str(e)}", exc_info=True)
                    continue
            
            logger.info(f"Completed batch {i//batch_size + 1}. Total processed: {total_processed}")
            
            if total_processed >= max_emails:
                break
                
            # Small delay between batches
            time.sleep(1)
            
        logger.info(f"Import completed. Total emails processed: {total_processed}")
            
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
        
        logger.debug(f"Stored email {email_data['msg_id']}")
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
    parser.add_argument("--start-date", type=str, help="Start date for import (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date for import (YYYY-MM-DD)")
    
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
                historical=args.historical,
                start_date=args.start_date,
                end_date=args.end_date
            )
            
        finally:
            conn.close()
            logger.info("Database connection closed")
            
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 