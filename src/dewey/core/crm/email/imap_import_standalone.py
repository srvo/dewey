from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
import argparse
import email
import imaplib
import json
import time
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import Message
from typing import Any, Dict, List, Optional

class IMAPSync(BaseScript):
    """IMAP email synchronization script with database integration."""
    
    def __init__(self) -> None:
        super().__init__(
            name="imap_sync",
            description="Synchronizes emails from IMAP server to database",
            config_section="imap",
            requires_db=True,
            enable_llm=False
        )

    # Email table schema matching project conventions
    EMAIL_SCHEMA = '''
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
    '''

    # Indexes matching project performance requirements
    EMAIL_INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id)",
        "CREATE INDEX IF NOT EXISTS idx_emails_from_address ON emails(from_address)",
        "CREATE INDEX IF NOT EXISTS idx_emails_internal_date ON emails(internal_date)",
        "CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status)",
        "CREATE INDEX IF NOT EXISTS idx_emails_batch_id ON emails(batch_id)",
        "CREATE INDEX IF NOT EXISTS idx_emails_import_timestamp ON emails(import_timestamp)"
    ]

    class EmailHeaderEncoder(json.JSONEncoder):
        """Custom JSON encoder following project data handling conventions"""
        def default(self, obj):
            try:
                if hasattr(obj, '__str__'):
                    return str(obj)
                return repr(obj)
            except Exception:
                return "Non-serializable data"

    def _init_database(self) -> None:
        """Initialize database schema using BaseScript's connection"""
        try:
            self.logger.info("Initializing email database schema")
            
            # Create table
            self.db_conn.execute(self.EMAIL_SCHEMA)
            
            # Create indexes
            for index_sql in self.EMAIL_INDEXES:
                self.db_conn.execute(index_sql)
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    def _connect_imap(self, config: dict) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server using configured credentials"""
        try:
            self.logger.info(f"Connecting to IMAP server {config['host']}:{config['port']}")
            imap = imaplib.IMAP4_SSL(config["host"], config["port"])
            imap.login(config["user"], config["password"])
            imap.select(config["mailbox"])
            return imap
        except Exception as e:
            self.logger.error(f"IMAP connection failed: {e}")
            raise

    def _decode_email_header(self, header: str) -> str:
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

    def _decode_payload(self, payload: bytes, charset: Optional[str] = None) -> str:
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

    def _get_message_structure(self, msg: Message) -> Dict[str, Any]:
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
                    part_info["subparts"] = self._get_message_structure(part)
                
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

    def _parse_email_message(self, email_data: bytes) -> Dict[str, Any]:
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
        subject = self._decode_email_header(msg["Subject"])
        from_addr = self._decode_email_header(msg["From"])
        to_addr = self._decode_email_header(msg["To"])
        date_str = msg["Date"]
        
        # Try to parse the date
        date_obj = None
        if date_str:
            try:
                date_tuple = email.utils.parsedate_tz(date_str)
                if date_tuple:
                    date_obj = datetime.fromtimestamp(
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
                    payload_str = self._decode_payload(payload, part.get_content_charset())
                    
                    if content_type == "text/plain":
                        body_text += payload_str
                    elif content_type == "text/html":
                        body_html += payload_str
        else:
            # Not multipart - get the payload directly
            payload = msg.get_payload(decode=True)
            if payload:
                payload_str = self._decode_payload(payload, msg.get_content_charset())
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
                "structure": self._get_message_structure(msg),
            }, cls=self.EmailHeaderEncoder),  # Use the custom encoder for non-serializable objects
        }
        
        return result

    def _fetch_emails(self, imap: imaplib.IMAP4_SSL, days_back: int = 7, max_emails: int = 100, 
                     batch_size: int = 10, historical: bool = False, 
                     start_date: str = None, end_date: str = None) -> None:
        """Fetch emails from Gmail using IMAP.
        
        Args:
            imap: IMAP connection
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
                result = self.db_conn.execute("SELECT msg_id FROM emails").fetchall()
                existing_ids = {str(row[0]) for row in result}
                self.logger.info(f"Found {len(existing_ids)} existing messages in database")
            except Exception as e:
                self.logger.error(f"Error getting existing message IDs: {e}")
            
            # Select the All Mail folder
            imap.select('"[Gmail]/All Mail"')
            
            # Search for emails based on parameters
            if historical:
                _, message_numbers = imap.search(None, 'ALL')
                self.logger.debug(f"Found {len(message_numbers[0].split())} total messages")
            elif start_date and end_date:
                # Format dates as DD-MMM-YYYY for IMAP
                start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%b-%Y")
                end = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%b-%Y")
                search_criteria = f'(SINCE {start} BEFORE {end})'
                self.logger.info(f"Searching with criteria: {search_criteria}")
                _, message_numbers = imap.search(None, search_criteria)
                self.logger.debug(f"Found {len(message_numbers[0].split())} messages between {start} and {end}")
            else:
                date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
                _, message_numbers = imap.search(None, f'SINCE {date}')
                self.logger.debug(f"Found {len(message_numbers[0].split())} messages since {date}")
            
            message_numbers = [int(num) for num in message_numbers[0].split()]
            total_processed = 0
            batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            self.logger.info(f"Processing {min(len(message_numbers), max_emails)} emails in batches of {batch_size}")
            
            # Process in batches
            for i in range(0, min(len(message_numbers), max_emails), batch_size):
                batch = message_numbers[i:i + batch_size]
                self.logger.debug(f"Processing batch {i//batch_size + 1} of {len(batch)} messages")
                
                for num in batch:
                    try:
                        # First fetch Gmail-specific IDs
                        self.logger.debug(f"Fetching Gmail IDs for message {num}")
                        _, msg_data = imap.fetch(str(num), "(X-GM-MSGID X-GM-THRID)")
                        self.logger.debug(f"Raw Gmail ID response: {msg_data}")
                        
                        if not msg_data or not msg_data[0]:
                            self.logger.error(f"No Gmail ID data for message {num}")
                            continue
                            
                        # Parse Gmail IDs from response
                        response = msg_data[0].decode('utf-8') if isinstance(msg_data[0], bytes) else str(msg_data[0])
                        self.logger.debug(f"Decoded Gmail ID response: {response}")
                        
                        # Extract Gmail message ID and thread ID using regex
                        import re
                        msgid_match = re.search(r'X-GM-MSGID\s+(\d+)', response)
                        thrid_match = re.search(r'X-GM-THRID\s+(\d+)', response)
                        
                        if not msgid_match or not thrid_match:
                            self.logger.error(f"Failed to extract Gmail IDs from response: {response}")
                            continue
                            
                        gmail_msgid = msgid_match.group(1)
                        gmail_thrid = thrid_match.group(1)
                        self.logger.debug(f"Extracted Gmail IDs - Message: {gmail_msgid}, Thread: {gmail_thrid}")
                        
                        # Skip if message already exists in database
                        if gmail_msgid in existing_ids:
                            self.logger.debug(f"Message {gmail_msgid} already exists in database, skipping")
                            continue
                        
                        # Now fetch the full message
                        self.logger.debug(f"Fetching full message {num}")
                        _, msg_data = imap.fetch(str(num), "(RFC822)")
                        if not msg_data or not msg_data[0] or not msg_data[0][1]:
                            self.logger.error(f"No message data for {num}")
                            continue
                            
                        email_data = self._parse_email_message(msg_data[0][1])
                        email_data['msg_id'] = gmail_msgid
                        email_data['thread_id'] = gmail_thrid
                        
                        if self._store_email(email_data, batch_id):
                            total_processed += 1
                            if total_processed % 10 == 0:
                                self.logger.info(f"Progress: {total_processed}/{min(len(message_numbers), max_emails)} emails processed")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing message {num}: {str(e)}", exc_info=True)
                        continue
                
                self.logger.info(f"Completed batch {i//batch_size + 1}. Total processed: {total_processed}")
                
                if total_processed >= max_emails:
                    break
                    
                # Small delay between batches
                time.sleep(1)
                
            self.logger.info(f"Import completed. Total emails processed: {total_processed}")
                
        except Exception as e:
            self.logger.error(f"Error in fetch_emails: {str(e)}", exc_info=True)
            raise

    def _store_email(self, email_data: Dict[str, Any], batch_id: str) -> bool:
        """Store email in the database.
        
        Args:
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
            self.db_conn.execute(f"""
            INSERT INTO emails ({columns})
            VALUES ({placeholders})
            """, values)
            
            self.logger.debug(f"Stored email {email_data['msg_id']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing email: {e}")
            return False

    def run(self) -> None:
        """Main execution method following BaseScript pattern"""
        try:
            args = self.parse_args()
            self._init_database()
            
            imap_config = {
                "host": self.get_config_value("host", "imap.gmail.com"),
                "port": self.get_config_value("port", 993),
                "user": args.username,
                "password": args.password or self.get_config_value("password"),
                "mailbox": self.get_config_value("mailbox", "INBOX")
            }

            with self._connect_imap(imap_config) as imap:
                self._fetch_and_process_emails(imap, args)
                
            self.logger.info("IMAP sync completed successfully")

        except Exception as e:
            self.logger.error(f"IMAP sync failed: {str(e)}", exc_info=True)
            raise

    def _fetch_and_process_emails(self, imap: imaplib.IMAP4_SSL, args: argparse.Namespace) -> None:
        """Orchestrate email fetching and processing"""
        try:
            self.logger.info(f"Starting email sync with params: {vars(args)}")
            message_ids = self._search_emails(imap, args)
            emails = self._fetch_email_batches(imap, message_ids, args.batch_size)
            self._store_emails(emails)
            
        except imaplib.IMAP4.error as e:
            self.logger.error(f"IMAP protocol error: {e}")
            raise
        finally:
            imap.close()
            imap.logout()

if __name__ == "__main__":
    IMAPSync().execute()
