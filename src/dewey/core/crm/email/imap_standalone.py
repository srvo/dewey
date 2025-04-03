#!/usr/bin/env python
"""IMAP email synchronization standalone script.
This script connects to a Gmail account using IMAP and downloads emails,
storing email metadata in a simple CSV file instead of a database.
"""

import argparse
import csv
import email
import imaplib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import Message
from typing import Any, Dict, Optional, Set


class EmailHeaderEncoder(json.JSONEncoder):
    """Custom JSON encoder for email headers."""

    def default(self, obj):
        try:
            if hasattr(obj, "__str__"):
                return str(obj)
            return repr(obj)
        except Exception:
            return "Non-serializable data"


def decode_email_header(header: str) -> str:
    """Decode email header properly handling various encodings."""
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
            except:
                decoded_parts.append(part.decode("utf-8", "ignore"))
        else:
            decoded_parts.append(str(part))
    return " ".join(decoded_parts)


def decode_payload(payload: bytes, charset: str | None = None) -> str:
    """Decode email payload bytes to string."""
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


def get_message_structure(msg: Message) -> dict[str, Any]:
    """Extract the structure of an email message for analysis."""
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


def parse_email_message(email_data: bytes) -> dict[str, Any]:
    """Parse email message data into a structured dictionary."""
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
                date_obj = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
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
        "attachments": json.dumps(attachments, cls=EmailHeaderEncoder),
        "raw_analysis": json.dumps(
            {
                "headers": all_headers,
                "structure": get_message_structure(msg),
            },
            cls=EmailHeaderEncoder,
        ),
    }

    return result


def connect_imap(config: dict[str, Any]) -> imaplib.IMAP4_SSL:
    """Connect to IMAP server using configured credentials."""
    try:
        print(f"Connecting to IMAP server {config['host']}:{config['port']}")
        imap = imaplib.IMAP4_SSL(config["host"], config["port"])
        imap.login(config["user"], config["password"])
        imap.select(config["mailbox"])
        return imap
    except Exception as e:
        print(f"IMAP connection failed: {e}")
        raise


def load_existing_ids(csv_file: str) -> set[str]:
    """Load existing message IDs from CSV file."""
    existing_ids = set()
    if os.path.exists(csv_file):
        try:
            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "msg_id" in row:
                        existing_ids.add(row["msg_id"])
            print(f"Found {len(existing_ids)} existing messages in CSV")
        except Exception as e:
            print(f"Error reading existing CSV: {e}")
    return existing_ids


def fetch_emails(
    imap: imaplib.IMAP4_SSL,
    csv_file: str,
    days_back: int = 7,
    max_emails: int = 100,
    batch_size: int = 10,
    historical: bool = False,
    start_date: str = None,
    end_date: str = None,
) -> None:
    """Fetch emails from Gmail using IMAP."""
    try:
        # Create CSV file with headers if it doesn't exist
        csv_exists = os.path.exists(csv_file)
        csv_file_dir = os.path.dirname(os.path.abspath(csv_file))
        os.makedirs(csv_file_dir, exist_ok=True)

        # Get existing message IDs from CSV
        existing_ids = load_existing_ids(csv_file)

        # Select the All Mail folder
        imap.select('"[Gmail]/All Mail"')

        # Search for emails based on parameters
        if historical:
            _, message_numbers = imap.search(None, "ALL")
            print(f"Found {len(message_numbers[0].split())} total messages")
        elif start_date and end_date:
            # Format dates as DD-MMM-YYYY for IMAP
            start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%b-%Y")
            end = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%b-%Y")
            search_criteria = f"(SINCE {start} BEFORE {end})"
            print(f"Searching with criteria: {search_criteria}")
            _, message_numbers = imap.search(None, search_criteria)
            print(
                f"Found {len(message_numbers[0].split())} messages between {start} and {end}"
            )
        else:
            date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            _, message_numbers = imap.search(None, f"SINCE {date}")
            print(f"Found {len(message_numbers[0].split())} messages since {date}")

        message_numbers = [int(num) for num in message_numbers[0].split()]

        # Reverse the list to process newest emails first
        message_numbers.reverse()

        total_processed = 0
        batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        print(
            f"Processing {min(len(message_numbers), max_emails)} emails in batches of {batch_size}"
        )

        # Open CSV file for appending
        with open(csv_file, "a", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "msg_id",
                "thread_id",
                "subject",
                "from",
                "to",
                "date",
                "raw_date",
                "message_id",
                "attachments",
                "batch_id",
                "import_timestamp",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header if file is new
            if not csv_exists:
                writer.writeheader()

            # Process in batches
            for i in range(0, min(len(message_numbers), max_emails), batch_size):
                batch = message_numbers[i : i + batch_size]
                print(
                    f"Processing batch {i // batch_size + 1} of {len(batch)} messages"
                )

                for num in batch:
                    try:
                        # First fetch Gmail-specific IDs
                        # print(f"Fetching Gmail IDs for message {num}")
                        _, msg_data = imap.fetch(str(num), "(X-GM-MSGID X-GM-THRID)")

                        if not msg_data or not msg_data[0]:
                            print(f"No Gmail ID data for message {num}")
                            continue

                        # Parse Gmail IDs from response
                        response = (
                            msg_data[0].decode("utf-8")
                            if isinstance(msg_data[0], bytes)
                            else str(msg_data[0])
                        )

                        # Extract Gmail message ID and thread ID using regex
                        msgid_match = re.search(r"X-GM-MSGID\s+(\d+)", response)
                        thrid_match = re.search(r"X-GM-THRID\s+(\d+)", response)

                        if not msgid_match or not thrid_match:
                            print("Failed to extract Gmail IDs from response")
                            continue

                        gmail_msgid = msgid_match.group(1)
                        gmail_thrid = thrid_match.group(1)

                        # Skip if message already exists
                        if gmail_msgid in existing_ids:
                            # print(f"Message {gmail_msgid} already exists, skipping")
                            continue

                        # Now fetch the full message
                        # print(f"Fetching full message {num}")
                        _, msg_data = imap.fetch(str(num), "(RFC822)")
                        if not msg_data or not msg_data[0] or not msg_data[0][1]:
                            print(f"No message data for {num}")
                            continue

                        # Parse email and write to CSV
                        email_data = parse_email_message(msg_data[0][1])
                        email_data["msg_id"] = gmail_msgid
                        email_data["thread_id"] = gmail_thrid
                        email_data["batch_id"] = batch_id
                        email_data["import_timestamp"] = datetime.now().isoformat()

                        # Write to CSV
                        writer.writerow(email_data)

                        total_processed += 1
                        if total_processed % 10 == 0:
                            print(
                                f"Progress: {total_processed}/{min(len(message_numbers), max_emails)} emails processed"
                            )

                    except Exception as e:
                        print(f"Error processing message {num}: {str(e)}")
                        continue

                print(
                    f"Completed batch {i // batch_size + 1}. Total processed: {total_processed}"
                )

                if total_processed >= max_emails:
                    break

                # Small delay between batches to avoid connection issues
                time.sleep(1)

        print(f"Import completed. Total emails processed: {total_processed}")
        print(f"Emails saved to {csv_file}")

    except Exception as e:
        print(f"Error in fetch_emails: {str(e)}")
        raise


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Import emails from Gmail")
    parser.add_argument(
        "--username", help="Gmail username (if not using GMAIL_USERNAME env var)"
    )
    parser.add_argument(
        "--password", help="Gmail password (if not using GMAIL_APP_PASSWORD env var)"
    )
    parser.add_argument(
        "--days_back",
        type=int,
        default=7,
        help="Number of days to look back for emails",
    )
    parser.add_argument(
        "--max_emails",
        type=int,
        default=1000,
        help="Maximum number of emails to import",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=10,
        help="Number of emails to process in each batch",
    )
    parser.add_argument(
        "--historical", action="store_true", help="Import all historical emails"
    )
    parser.add_argument("--start_date", help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", help="End date in YYYY-MM-DD format")
    parser.add_argument(
        "--output", default="data/emails.csv", help="Output CSV file path"
    )

    return parser.parse_args()


def main():
    """Main function."""
    args = parse_args()

    # Get username and password from environment or command line
    username = args.username or os.environ.get("GMAIL_USERNAME")
    password = os.environ.get("GMAIL_APP_PASSWORD") or args.password

    if not username:
        print(
            "Gmail username not provided via GMAIL_USERNAME environment variable or command line argument"
        )
        sys.exit(1)

    if not password:
        print(
            "Gmail password not provided via GMAIL_APP_PASSWORD environment variable or command line argument"
        )
        sys.exit(1)

    imap_config = {
        "host": "imap.gmail.com",
        "port": 993,
        "user": username,
        "password": password,
        "mailbox": '"[Gmail]/All Mail"',
    }

    try:
        with connect_imap(imap_config) as imap:
            fetch_emails(
                imap,
                args.output,
                days_back=args.days_back,
                max_emails=args.max_emails,
                batch_size=args.batch_size,
                historical=args.historical,
                start_date=args.start_date,
                end_date=args.end_date,
            )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
