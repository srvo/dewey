import datetime
import email
import imaplib
import logging
import os
import re
import sqlite3
import ssl
import time
from email.header import decode_header

import icalendar
from email_validator import EmailNotValidError, validate_email

# Configure logging for debugging and tracking purposes.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Folders to exclude (if any)
EXCLUDE_FOLDERS = ["[Gmail]/Spam", "[Gmail]/Trash"]

# IMAP configuration from environment variables.
IMAP_SERVER = os.getenv("IMAP_SERVER", "your-imap-server.com")
EMAIL_USER = os.getenv("EMAIL_USER", "user@example.com")
# Handle potential quotes in password string
EMAIL_PASS = os.getenv("EMAIL_PASSWORD", "password")
if (EMAIL_PASS.startswith('"') and EMAIL_PASS.endswith('"')) or (
    EMAIL_PASS.startswith("'") and EMAIL_PASS.endswith("'")
):
    EMAIL_PASS = EMAIL_PASS[1:-1]

# Log email configuration (mask the full password)
logging.info(
    f"Email config - Server: {IMAP_SERVER}, User: {EMAIL_USER}, Pass: {EMAIL_PASS[:2]}***{EMAIL_PASS[-2:]} (length: {len(EMAIL_PASS)})",
)

# SQLite database path (ensure your volume is mounted to /data in Docker)
DB_PATH = "/data/emails.db"

# Connection timeout and retry settings
CONNECTION_TIMEOUT = 30  # seconds
MAX_RETRIES = 5
RETRY_DELAY = 60  # seconds


def create_imap_connection():
    """Create and return a new IMAP connection with proper error handling."""
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            logging.info("Establishing IMAP connection to %s", IMAP_SERVER)
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=CONNECTION_TIMEOUT)
            mail.login(EMAIL_USER, EMAIL_PASS)
            logging.info("Successfully connected to IMAP server")
            return mail
        except (OSError, ssl.SSLError, imaplib.IMAP4.error) as e:
            retry_count += 1
            logging.exception(
                "Connection attempt %d failed: %s. Retrying in %d seconds...",
                retry_count,
                str(e),
                RETRY_DELAY,
            )
            time.sleep(RETRY_DELAY)

    logging.critical(
        "Failed to connect to IMAP server after %d attempts. Exiting.",
        MAX_RETRIES,
    )
    msg = f"Could not connect to IMAP server {IMAP_SERVER} after {MAX_RETRIES} attempts"
    raise ConnectionError(msg)


def check_imap_connection(mail):
    """Check if the IMAP connection is still alive and reconnect if necessary."""
    try:
        # Simple NOOP command to check connection
        status, response = mail.noop()
        if status == "OK":
            return mail
    except (OSError, ssl.SSLError, imaplib.IMAP4.error) as e:
        logging.warning("IMAP connection lost: %s. Reconnecting...", str(e))

    # If we got here, connection needs to be re-established
    try:
        mail.logout()
    except:
        pass  # Ignore errors during logout of dead connection

    return create_imap_connection()


def parse_calendar_content(calendar_data):
    """Parse calendar content and return a formatted string."""
    try:
        if isinstance(calendar_data, str):
            calendar_data = calendar_data.encode("utf-8")

        cal = icalendar.Calendar.from_ical(calendar_data)
        event_details = []

        for component in cal.walk():
            if component.name == "VEVENT":
                # Handle date objects vs datetime objects
                start = component.get("dtstart", "No Start Date").dt
                end = component.get("dtend", "No End Date").dt
                if isinstance(start, datetime.date) and not isinstance(
                    start,
                    datetime.datetime,
                ):
                    start = datetime.datetime.combine(start, datetime.time.min)
                if isinstance(end, datetime.date) and not isinstance(
                    end,
                    datetime.datetime,
                ):
                    end = datetime.datetime.combine(end, datetime.time.max)

                event = {
                    "summary": str(component.get("summary", "No Title")),
                    "start": start,
                    "end": end,
                    "location": str(component.get("location", "No Location")),
                    "description": str(component.get("description", "No Description")),
                    "organizer": str(component.get("organizer", "No Organizer")),
                    "status": str(component.get("status", "No Status")),
                    "attendees": [str(a) for a in component.get("attendee", [])],
                }
                event_details.append(
                    f"Event: {event['summary']}\n"
                    f"When: {event['start'].strftime('%Y-%m-%d %H:%M')} - {event['end'].strftime('%Y-%m-%d %H:%M')}\n"
                    f"Where: {event['location']}\n"
                    f"Organizer: {event['organizer']}\n"
                    f"Status: {event['status']}\n"
                    f"Attendees: {', '.join(event['attendees']) if event['attendees'] else 'None'}\n"
                    f"Description: {event['description']}\n",
                )

        return "\n".join(event_details) if event_details else "[Empty Calendar Invite]"
    except Exception as e:
        logging.debug(f"Error parsing calendar content: {e!s}", exc_info=True)
        return "[Calendar Parsing Failed]"


def create_database() -> None:
    """Create the emails table in the database if it doesn't already exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY,
            uid TEXT UNIQUE,
            sender TEXT,
            recipient TEXT,
            cc TEXT,
            subject TEXT,
            body TEXT,
            raw_body TEXT,
            folder TEXT,
            labels TEXT,
            annotations TEXT,
            date TEXT
        )
    """,
    )
    conn.commit()
    conn.close()
    logging.info("Database is initialized.")


def validate_email_address(email_str):
    """Validates and normalizes an email address, returns empty string if invalid."""
    if not email_str:
        return ""
    try:
        valid = validate_email(email_str, check_deliverability=False)
        return valid.normalized
    except EmailNotValidError:
        logging.debug(f"Invalid email address: {email_str}")
        return email_str  # Return original string instead of empty to preserve data


def parse_email(raw_email):
    """Parse the raw email content and extract all email data."""
    try:
        import mailparser

        parsed_mail = mailparser.parse_from_bytes(raw_email)

        # Extract and clean basic fields
        subject = (parsed_mail.subject or "").strip()
        sender = parsed_mail.from_[0][1] if parsed_mail.from_ else ""
        recipient = parsed_mail.to[0][1] if parsed_mail.to else ""
        cc_list = [cc[1] for cc in (parsed_mail.cc or [])]
        cc = "; ".join(cc_list)
        date = parsed_mail.date.isoformat() if parsed_mail.date else ""

        # Store raw message body
        raw_body = raw_email.decode("utf-8", errors="replace")

        # Handle different content types
        body = ""
        if parsed_mail.text_plain:
            body = parsed_mail.text_plain[0]
        elif parsed_mail.text_html:
            body = parsed_mail.text_html[0]
        elif getattr(parsed_mail, "calendar", None):
            # Try to find calendar content in attachments
            for attachment in parsed_mail.attachments:
                if attachment.get("content_type", "").startswith("text/calendar"):
                    calendar_data = attachment.get("payload", "")
                    body = parse_calendar_content(calendar_data)
                    break
            if not body:  # If no calendar attachment found
                body = "[Calendar Invite - No Details Available]"

            logging.info("Calendar content found and marked")
        else:
            body = parsed_mail.body or ""

    except Exception as e:
        logging.exception(
            "Error parsing email with mailparser: %s. Falling back to standard parsing.",
            str(e),
        )
        return parse_email_fallback(raw_email)

    # Validate and clean email addresses
    sender = validate_email_address(sender)
    recipient = validate_email_address(recipient)
    cc = "; ".join([validate_email_address(cc_addr) for cc_addr in cc_list if cc_addr])

    return subject, sender, recipient, cc, body, raw_body, date


def parse_email_fallback(raw_email):
    """Fallback parsing using Python's standard library."""
    try:
        msg = email.message_from_bytes(raw_email)
        subject = msg.get("subject", "")
        parts = decode_header(subject)
        decoded_subject = "".join(
            [
                (
                    part.decode(encoding if encoding else "utf-8")
                    if isinstance(part, bytes)
                    else part
                )
                for part, encoding in parts
            ],
        )
        sender = msg.get("from", "")
        recipient = msg.get("to", "")
        cc = msg.get("cc", "")
        date = msg.get("date", "")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and "attachment" not in str(
                    part.get("Content-Disposition", ""),
                ):
                    try:
                        body = part.get_payload(decode=True).decode(
                            "utf-8",
                            errors="replace",
                        )
                        break
                    except Exception as e:
                        logging.exception("Error decoding email part: %s", str(e))
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            except Exception as e:
                logging.exception("Error decoding email: %s", str(e))
        return decoded_subject, sender, recipient, cc, body, "", date
    except Exception as e:
        logging.exception("Fallback email parsing failed: %s", str(e))
        return "", "", "", "", "", "", ""


def get_gmail_labels(mail, email_id):
    """Fetch Gmail labels for a specific email."""
    try:
        # Fetch Gmail-specific labels using X-GM-LABELS
        status, label_data = mail.fetch(email_id, "(X-GM-LABELS)")
        if status == "OK":
            # Parse the label string and clean it
            label_str = label_data[0].decode("utf-8")
            # Extract labels from response like "(...labels...)"
            labels = re.findall(r"\((.*?)\)", label_str)
            if labels:
                return labels[0]
        return ""
    except Exception as e:
        logging.exception(f"Error fetching labels: {e!s}")
        return ""


def main() -> None:
    """Main function to run the email sync process."""
    try:
        # Initialize database
        create_database()
        logging.info("SQLite database initialized successfully")

        # Connect to IMAP server using the new connection function
        mail = create_imap_connection()

        while True:
            try:
                # Check and refresh the connection if needed before each major operation
                mail = check_imap_connection(mail)

                # List all folders
                status, folders = mail.list()

                for folder_info in folders:
                    folder_name = folder_info.decode().split('"/"')[-1].strip('" ')
                    if folder_name in EXCLUDE_FOLDERS:
                        continue

                    logging.info(f"Processing folder: {folder_name}")

                    # Check connection before each folder selection
                    mail = check_imap_connection(mail)
                    mail.select(f'"{folder_name}"')

                    # Search for all emails in the folder
                    mail = check_imap_connection(mail)
                    status, messages = mail.search(None, "ALL")

                    for email_id in messages[0].split():
                        try:
                            # Check if email already exists in database
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute(
                                "SELECT uid FROM emails WHERE uid = ?",
                                (email_id.decode(),),
                            )
                            if cursor.fetchone() is not None:
                                continue

                            # Check connection before fetching email
                            mail = check_imap_connection(mail)

                            # Fetch email content
                            status, msg_data = mail.fetch(email_id, "(RFC822)")
                            email_body = msg_data[0][1]

                            # Parse email
                            subject, sender, recipient, cc, body, raw_body, date = (
                                parse_email(email_body)
                            )

                            # Get Gmail labels
                            mail = check_imap_connection(mail)
                            labels = get_gmail_labels(mail, email_id)

                            # Store in SQLite
                            cursor.execute(
                                """
                                INSERT INTO emails (uid, sender, recipient, cc, subject, body, raw_body, folder, labels, date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    email_id.decode(),
                                    sender,
                                    recipient,
                                    cc,
                                    subject,
                                    body,
                                    raw_body,
                                    folder_name,
                                    labels,
                                    date,
                                ),
                            )
                            conn.commit()
                            logging.info(f"Stored email {email_id.decode()} in SQLite")

                        except (OSError, ssl.SSLError, imaplib.IMAP4.error) as e:
                            logging.exception(
                                f"IMAP error processing email {email_id}: {e!s}",
                            )
                            # Reconnect and skip this email
                            mail = create_imap_connection()
                            continue
                        except Exception as e:
                            logging.exception(
                                f"Error processing email {email_id}: {e!s}",
                            )
                            continue
                        finally:
                            if "conn" in locals():
                                conn.close()

                # Sleep before next sync
                logging.info(
                    "Completed sync cycle. Sleeping for 5 minutes before next sync.",
                )
                time.sleep(300)  # 5 minutes

            except (OSError, ssl.SSLError, imaplib.IMAP4.error) as e:
                logging.exception(f"IMAP connection error in sync loop: {e!s}")
                # Don't try to reconnect here - let the next loop iteration handle it
                time.sleep(60)  # Wait a minute before retrying
            except Exception as e:
                logging.exception(f"Error in sync loop: {e!s}")
                time.sleep(60)  # Wait a minute before retrying

    except Exception as e:
        logging.exception(f"Fatal error: {e!s}")
        raise


if __name__ == "__main__":
    main()
