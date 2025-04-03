import argparse
import email
import imaplib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import Message
from typing import Any, Dict, List, Optional, Set

import duckdb
from dotenv import load_dotenv

from dewey.core.base_script import BaseScript

# Load environment variables from .env file
load_dotenv()


class EmailHeaderEncoder(json.JSONEncoder):
    """Custom JSON encoder following project data handling conventions."""

    def default(self, obj):
        """Convert non-serializable objects to strings."""
        try:
            if hasattr(obj, "__str__"):
                return str(obj)
            return repr(obj)
        except Exception:
            return "Non-serializable data"


def safe_json_dumps(data: Any, encoder: json.JSONEncoder | None = None) -> str:
    """JSON dumping with multiple fallback strategies.

    Args:
        data: The data to serialize
        encoder: Optional JSON encoder to use

    Returns:
        JSON string representation of data

    """
    try:
        return json.dumps(data, cls=encoder or EmailHeaderEncoder)
    except TypeError as e:
        try:
            # Try cleaning common non-serializable types
            if isinstance(data, dict):
                cleaned = {k: str(v) for k, v in data.items()}
                return json.dumps(cleaned, cls=encoder or EmailHeaderEncoder)
            else:
                return json.dumps(str(data))
        except Exception as fallback_error:
            return json.dumps(
                {
                    "error": f"JSON serialization failed: {str(e)}",
                    "fallback_error": str(fallback_error),
                }
            )


class UnifiedIMAPImporter(BaseScript):
    """Unified IMAP importer supporting both database and MotherDuck."""

    SQL_RESERVED = {
        "from",
        "where",
        "select",
        "insert",
        "update",
        "delete",
        "order",
        "group",
        "having",
        "limit",
    }

    def __init__(self) -> None:
        """Initialize the IMAP email importer."""
        super().__init__(
            name="IMAPEmailImporter",
            description="Import emails from IMAP to database or MotherDuck",
            config_section="imap_import",
            requires_db=True,
            enable_llm=False,
        )
        self.motherduck_mode = False
        self._init_schema_and_indexes()

    def _init_schema_and_indexes(self) -> None:
        """Combine schema definitions from both sources."""
        self.email_schema = """
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

        # Create index statements - broken into multiple lines for readability
        idx_thread_id = (
            "CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id)"
        )
        idx_from_addr = (
            "CREATE INDEX IF NOT EXISTS idx_emails_from_address ON emails(from_address)"
        )
        idx_internal_date = (
            "CREATE INDEX IF NOT EXISTS idx_emails_internal_date "
            "ON emails(internal_date)"
        )
        idx_status = "CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status)"
        idx_batch_id = (
            "CREATE INDEX IF NOT EXISTS idx_emails_batch_id ON emails(batch_id)"
        )
        idx_import_ts = (
            "CREATE INDEX IF NOT EXISTS idx_emails_import_timestamp "
            "ON emails(import_timestamp)"
        )

        self.email_indexes = [
            idx_thread_id,
            idx_from_addr,
            idx_internal_date,
            idx_status,
            idx_batch_id,
            idx_import_ts,
        ]

    def setup_argparse(self) -> argparse.ArgumentParser:
        """Set up command line arguments."""
        parser = super().setup_argparse()
        parser.add_argument(
            "--motherduck", action="store_true", help="Use MotherDuck database"
        )
        parser.add_argument(
            "--username",
            default="sloane@ethicic.com",
            help="Gmail username (default: sloane@ethicic.com)",
        )
        parser.add_argument(
            "--password",
            help="App password (uses GMAIL_APP_PASSWORD from .env by default)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Days back to search for emails",
        )
        parser.add_argument(
            "--max",
            type=int,
            default=1000,
            help="Maximum emails to import",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Batch size for processing",
        )
        parser.add_argument(
            "--historical",
            action="store_true",
            help="Import all historical emails",
        )
        parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
        parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
        parser.add_argument(
            "--workers",
            type=int,
            default=4,
            help="Number of worker threads for parallel processing",
        )
        return parser

    def init_database(self) -> None:
        """Initialize database connection and schema."""
        if self.motherduck_mode:
            self._init_motherduck()
        else:
            # Initialize database connection using the base_script method
            self._initialize_db_connection()
            # Create the emails table
            self.db_conn.execute(self.email_schema)
            # Create indexes
            for index_sql in self.email_indexes:
                self.db_conn.execute(index_sql)
            self.logger.info(
                "Initialized SQLite database with email schema and indexes"
            )

    def _init_motherduck(self) -> None:
        """Initialize MotherDuck database connection."""
        motherduck_token = os.environ.get("MOTHERDUCK_TOKEN")
        if not motherduck_token:
            raise ValueError("MOTHERDUCK_TOKEN environment variable required")

        conn_string = f"md:dewey?motherduck_token={motherduck_token}"
        self.db_conn = duckdb.connect(conn_string)
        self.db_conn.execute(self.email_schema)
        for index_sql in self.email_indexes:
            self.db_conn.execute(index_sql)
        self.logger.info("Initialized MotherDuck database connection")

    def connect_to_gmail(self, username: str, password: str) -> imaplib.IMAP4_SSL:
        """Connect to Gmail using IMAP.

        Args:
            username: Gmail username
            password: App-specific password

        Returns:
            IMAP connection

        """
        config = {
            "host": "imap.gmail.com",
            "port": 993,
            "user": username,
            "password": password,
            "mailbox": '"[Gmail]/All Mail"',
        }
        return self._connect_imap(config)

    def _connect_imap(self, config: dict) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server using configured credentials.

        Args:
            config: Dictionary with connection parameters

        Returns:
            IMAP connection object

        """
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                self.logger.info(
                    "Connecting to IMAP server %s:%s (attempt %d/%d)",
                    config["host"],
                    config["port"],
                    attempt + 1,
                    max_retries,
                )
                # Set socket timeout to prevent hanging
                socket_timeout = 60  # 60 seconds timeout
                imap = imaplib.IMAP4_SSL(
                    config["host"], config["port"], timeout=socket_timeout
                )
                imap.login(config["user"], config["password"])
                self.logger.info(
                    "Successfully logged in as %s",
                    config["user"],
                )

                # Set a shorter timeout for operations
                imap.socket().settimeout(socket_timeout)

                # Select the mailbox
                imap.select(config["mailbox"])
                self.logger.info("Selected mailbox: %s", config["mailbox"])

                return imap
            except (
                imaplib.IMAP4.abort,
                ConnectionResetError,
                TimeoutError,
                OSError,
            ) as e:
                self.logger.error(
                    "IMAP connection failed on attempt %d: %s", attempt + 1, e
                )
                if attempt < max_retries - 1:
                    self.logger.info("Retrying in %d seconds...", retry_delay)
                    time.sleep(retry_delay)
                else:
                    self.logger.error("Max retries reached, giving up.")
                    raise
            except Exception as e:
                self.logger.error("Unexpected IMAP error: %s", e)
                raise

    def _decode_email_header(self, header: str) -> str:
        """Decode email header properly handling various encodings.

        Args:
            header: Raw email header

        Returns:
            Decoded header string

        """
        if not header:
            return ""

        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    if encoding:
                        decoded_parts.append(part.decode(encoding))
                    else:
                        decoded_parts.append(part.decode())
                except Exception:  # Replacing bare except with Exception
                    decoded_parts.append(part.decode("utf-8", "ignore"))
            else:
                decoded_parts.append(str(part))
        return " ".join(decoded_parts)

    def _decode_payload(self, payload: bytes, charset: str | None = None) -> str:
        """Decode email payload bytes to string.

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

    def _get_message_structure(self, msg: Message) -> dict[str, Any]:
        """Extract the structure of an email message for analysis.

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
                    "size": (len(part.as_bytes()) if hasattr(part, "as_bytes") else 0),
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
                "size": (len(msg.as_bytes()) if hasattr(msg, "as_bytes") else 0),
            }

    def _parse_email_message(self, email_data: bytes) -> dict[str, Any]:
        """Parse email message data into a structured dictionary.

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
                    timestamp = email.utils.mktime_tz(date_tuple)
                    date_obj = datetime.fromtimestamp(timestamp)
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
                        attachments.append(
                            {
                                "filename": filename,
                                "content_type": content_type,
                                "size": len(payload) if payload else 0,
                            }
                        )
                    continue

                # Try to get the payload
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset()
                    payload_str = self._decode_payload(payload, charset)

                    if content_type == "text/plain":
                        body_text += payload_str
                    elif content_type == "text/html":
                        body_html += payload_str
        else:
            # Not multipart - get the payload directly
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset()
                payload_str = self._decode_payload(payload, charset)
                content_type = msg.get_content_type()

                if content_type == "text/plain":
                    body_text = payload_str
                elif content_type == "text/html":
                    body_html = payload_str

        # Get all headers for raw analysis
        all_headers = {}
        for key in msg.keys():
            all_headers[key] = msg[key]

        # Define from_name with a helper function to improve readability
        def extract_name(addr):
            return addr.split("<")[0].strip() if "<" in addr else ""

        # Process list of addresses with a helper function
        def extract_addresses(header_value):
            if not header_value:
                return []
            return [addr.strip() for addr in header_value.split(",") if addr.strip()]

        # Prepare metadata (store to_addresses, cc_addresses, bcc_addresses here)
        metadata = {
            "from_name": extract_name(from_addr),
            "to_addresses": extract_addresses(to_addr),
            "cc_addresses": extract_addresses(msg["Cc"]),
            "bcc_addresses": extract_addresses(msg["Bcc"]),
            "received_date": date_obj.isoformat() if date_obj else None,
            "body_text": body_text,
            "body_html": body_html,
            "message_id": message_id,
        }

        # Calculate internal_date as Unix timestamp if available
        internal_date = int(date_obj.timestamp() * 1000) if date_obj else None

        # Store message parts as JSON for compatibility
        message_parts = {"text": body_text, "html": body_html}

        # Return structured email data matching MotherDuck schema
        return {
            "msg_id": message_id,  # Will be replaced with Gmail ID
            "thread_id": None,  # Will be replaced with Gmail thread ID
            "subject": subject,
            "from_address": from_addr,
            "analysis_date": datetime.now().isoformat(),
            "raw_analysis": safe_json_dumps(
                {
                    "headers": all_headers,
                    "structure": self._get_message_structure(msg),
                }
            ),
            "metadata": safe_json_dumps(metadata),
            "snippet": body_text[:500] if body_text else "",
            "internal_date": internal_date,
            "size_estimate": len(email_data),
            "message_parts": safe_json_dumps(message_parts),
            "attachments": safe_json_dumps(attachments),
            "status": "new",
        }

    def _fetch_emails(
        self,
        imap: imaplib.IMAP4_SSL,
        days_back: int = 7,
        max_emails: int = 100,
        batch_size: int = 10,
        historical: bool = False,
        start_date: str | None = None,
        end_date: str | None = None,
        num_workers: int = 4,  # Number of worker threads
    ) -> None:
        """Fetch emails from Gmail using IMAP with parallel processing.

        Args:
            imap: IMAP connection
            days_back: Number of days back to fetch
            max_emails: Maximum number of emails to fetch
            batch_size: Number of emails to process in each batch
            historical: Whether to fetch all emails or just recent ones
            start_date: Optional start date in format YYYY-MM-DD
            end_date: Optional end date in format YYYY-MM-DD
            num_workers: Number of worker threads for parallel processing

        """
        try:
            # Get existing message IDs from database
            existing_ids = self._get_existing_ids()

            # Search for emails based on parameters
            if historical:
                _, message_numbers = imap.search(None, "ALL")
                num_msgs = len(message_numbers[0].split())
                self.logger.debug("Found %d total messages", num_msgs)
            elif start_date and end_date:
                # Format dates as DD-MMM-YYYY for IMAP
                start_fmt = datetime.strptime(start_date, "%Y-%m-%d").strftime(
                    "%d-%b-%Y"
                )

                end_fmt = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%b-%Y")

                search_criteria = f"(SINCE {start_fmt} BEFORE {end_fmt})"
                self.logger.info(
                    "Searching with criteria: %s",
                    search_criteria,
                )

                _, message_numbers = imap.search(None, search_criteria)
                num_msgs = len(message_numbers[0].split())

                self.logger.debug(
                    "Found %d messages between %s and %s",
                    num_msgs,
                    start_fmt,
                    end_fmt,
                )
            else:
                date_fmt = (datetime.now() - timedelta(days=days_back)).strftime(
                    "%d-%b-%Y"
                )

                _, message_numbers = imap.search(None, f"SINCE {date_fmt}")
                num_msgs = len(message_numbers[0].split())

                self.logger.debug(
                    "Found %d messages since %s",
                    num_msgs,
                    date_fmt,
                )

            message_numbers = [int(num) for num in message_numbers[0].split()]

            # Reverse the list to process newest emails first
            message_numbers.reverse()

            total_processed = 0
            batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            processed_count = min(len(message_numbers), max_emails)
            self.logger.info(
                "Processing %d emails in batches of %d with %d worker threads",
                processed_count,
                batch_size,
                num_workers,
            )

            # Process in batches using multiple threads
            max_to_process = min(len(message_numbers), max_emails)

            # Create multiple IMAP connections for the worker threads
            imap_connections = self._create_imap_connections(num_workers)

            for i in range(0, max_to_process, batch_size):
                batch = message_numbers[i : i + batch_size]
                batch_num = i // batch_size + 1

                self.logger.debug(
                    "Processing batch %d of %d messages",
                    batch_num,
                    len(batch),
                )

                try:
                    # Process each batch with parallel workers
                    with ThreadPoolExecutor(max_workers=num_workers) as executor:
                        # Create tasks for each message in the batch
                        futures = []
                        for idx, msg_num in enumerate(batch):
                            # Distribute connections among workers
                            conn_idx = idx % len(imap_connections)
                            conn = imap_connections[conn_idx]

                            futures.append(
                                executor.submit(
                                    self._process_single_email,
                                    conn,
                                    msg_num,
                                    existing_ids,
                                    batch_id,
                                )
                            )

                        # Process results as they complete
                        for future in as_completed(futures):
                            try:
                                result = future.result()
                                if result:
                                    total_processed += 1
                                    if total_processed % 10 == 0:
                                        self.logger.info(
                                            "Progress: %d/%d emails processed",
                                            total_processed,
                                            max_to_process,
                                        )
                            except Exception as e:
                                self.logger.error("Worker thread error: %s", str(e))

                    self.logger.info(
                        "Completed batch %d. Total processed: %d",
                        batch_num,
                        total_processed,
                    )

                except Exception as e:
                    self.logger.error("Batch processing error: %s", str(e))

                if total_processed >= max_emails:
                    break

                # Small delay between batches
                time.sleep(1)

            # Close the extra IMAP connections
            for conn in imap_connections:
                try:
                    conn.close()
                    conn.logout()
                except Exception:
                    pass

            self.logger.info(
                "Import completed. Total emails processed: %d",
                total_processed,
            )

        except Exception as e:
            self.logger.error("Error in fetch_emails: %s", str(e))
            raise

    def _create_imap_connections(self, num_connections: int) -> list[imaplib.IMAP4_SSL]:
        """Create multiple IMAP connections for parallel processing.

        Args:
            num_connections: Number of connections to create

        Returns:
            List of IMAP connections

        """
        connections = []
        config = self._get_imap_config()

        for i in range(num_connections):
            try:
                self.logger.debug(f"Creating IMAP connection {i + 1}/{num_connections}")
                conn = self._connect_imap(config)
                connections.append(conn)
            except Exception as e:
                self.logger.error(f"Failed to create IMAP connection {i + 1}: {e}")

        if not connections:
            raise ValueError("Failed to create any IMAP connections")

        return connections

    def _get_imap_config(self) -> dict:
        """Get IMAP configuration from environment variables or args."""
        username = self.args.username
        password = self.args.password or os.getenv("GMAIL_APP_PASSWORD")

        if not password:
            raise ValueError(
                "Gmail password required in GMAIL_APP_PASSWORD "
                "environment variable or --password"
            )

        return {
            "host": "imap.gmail.com",
            "port": 993,
            "user": username,
            "password": password,
            "mailbox": '"[Gmail]/All Mail"',
        }

    def _process_single_email(
        self,
        imap: imaplib.IMAP4_SSL,
        msg_num: int,
        existing_ids: set[str],
        batch_id: str,
    ) -> bool:
        """Process a single email message in a worker thread.

        Args:
            imap: IMAP connection to use
            msg_num: Message number to process
            existing_ids: Set of existing message IDs
            batch_id: Current batch ID

        Returns:
            True if email was processed successfully

        """
        try:
            # First fetch Gmail-specific IDs
            self.logger.debug(
                "Fetching Gmail IDs for message %d",
                msg_num,
            )
            _, msg_data = imap.fetch(str(msg_num), "(X-GM-MSGID X-GM-THRID)")

            if not msg_data or not msg_data[0]:
                self.logger.error(
                    "No Gmail ID data for message %d",
                    msg_num,
                )
                return False

            # Parse Gmail IDs from response
            response = (
                msg_data[0].decode("utf-8")
                if isinstance(msg_data[0], bytes)
                else str(msg_data[0])
            )

            # Extract Gmail IDs using regex
            msgid_match = re.search(
                r"X-GM-MSGID\s+(\d+)",
                response,
            )
            thrid_match = re.search(
                r"X-GM-THRID\s+(\d+)",
                response,
            )

            if not msgid_match or not thrid_match:
                self.logger.error(
                    "Failed to extract Gmail IDs: %s",
                    response,
                )
                return False

            gmail_msgid = msgid_match.group(1)
            gmail_thrid = thrid_match.group(1)

            # Skip if message already exists
            if gmail_msgid in existing_ids:
                self.logger.debug(
                    "Message %s already exists, skipping",
                    gmail_msgid,
                )
                return False

            # Now fetch the full message
            self.logger.debug(
                "Fetching full message %d",
                msg_num,
            )
            _, msg_data = imap.fetch(str(msg_num), "(RFC822)")

            if not msg_data or not msg_data[0]:
                self.logger.error(
                    "No message data for %d",
                    msg_num,
                )
                return False

            # Extract and store message data
            raw_data = msg_data[0][1]
            email_data = self._parse_email_message(raw_data)
            email_data["msg_id"] = gmail_msgid
            email_data["thread_id"] = gmail_thrid

            return self._store_email(email_data, batch_id)

        except Exception as e:
            self.logger.error(
                "Error processing message %d: %s",
                msg_num,
                str(e),
            )
            return False

    def _store_email(self, email_data: dict[str, Any], batch_id: str) -> bool:
        """Store email in the database.

        Args:
            email_data: Parsed email data
            batch_id: Batch identifier

        Returns:
            True if successful

        """
        try:
            # Add batch ID to email data
            email_data["batch_id"] = batch_id

            # SQL reserved keywords that need escaping
            escaped_columns = []
            escaped_values = []

            # Prepare columns with proper escaping
            for col, val in email_data.items():
                if col.lower() in self.SQL_RESERVED:
                    escaped_columns.append(f'"{col}"')
                else:
                    escaped_columns.append(col)
                escaped_values.append(val)

            columns = ", ".join(escaped_columns)
            placeholders = ", ".join(["?" for _ in email_data])

            # Insert into database
            query = f"""
                INSERT INTO emails ({columns})
                VALUES ({placeholders})
            """
            self.db_conn.execute(query, escaped_values)

            self.logger.debug("Stored email %s", email_data["msg_id"])
            return True

        except Exception as e:
            self.logger.error("Error storing email: %s", e)
            return False

    def _get_existing_ids(self) -> set[str]:
        """Get existing message IDs from database.

        Returns:
            Set of existing message IDs

        """
        existing_ids = set()
        try:
            query = "SELECT msg_id FROM emails"
            result = self.db_conn.execute(query).fetchall()
            existing_ids = {str(row[0]) for row in result}
            self.logger.info(
                "Found %d existing messages in database",
                len(existing_ids),
            )
        except Exception as e:
            self.logger.error("Error getting existing message IDs: %s", e)
        return existing_ids

    def execute(self) -> None:
        """Main execution method."""
        try:
            args = self.parse_args()
            self.args = args  # Store args for use in other methods
            self.motherduck_mode = args.motherduck
            self.init_database()

            # Configure number of workers based on args
            num_workers = args.workers

            imap_config = self._get_imap_config()

            with self._connect_imap(imap_config) as imap:
                self._fetch_emails(
                    imap,
                    days_back=args.days,
                    max_emails=args.max,
                    batch_size=args.batch_size,
                    historical=args.historical,
                    start_date=args.start_date,
                    end_date=args.end_date,
                    num_workers=num_workers,
                )

            self.logger.info("IMAP sync completed successfully")

        except Exception as e:
            self.logger.error("IMAP sync failed: %s", str(e))
            raise
