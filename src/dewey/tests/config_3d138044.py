"""Test configuration module for email sync service testing."""

import os
import tempfile
from pathlib import Path

# Test database paths
TEST_DIR = Path(tempfile.gettempdir()) / "email_sync_tests"
TEST_EMAIL_DB = TEST_DIR / "test_emails.db"
TEST_METADATA_DB = TEST_DIR / "test_metadata.db"

# Test email data
TEST_EMAIL_DATA = {
    "sender": "test@example.com",
    "recipient": "recipient@example.com",
    "cc": "cc@example.com",
    "subject": "Test Subject",
    "body": "Test Body",
    "date": "2023-01-01T12:00:00",
    "folder": "INBOX",
    "uid": "test123",
}

# Test calendar data (iCalendar format)
TEST_CALENDAR_DATA = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example Corp//Example Calendar//EN
METHOD:REQUEST
BEGIN:VEVENT
UID:12345@example.com
DTSTAMP:20230101T120000Z
DTSTART:20230115T140000Z
DTEND:20230115T150000Z
SUMMARY:Test Meeting
LOCATION:Conference Room
DESCRIPTION:This is a test meeting
ORGANIZER;CN=Organizer:mailto:organizer@example.com
ATTENDEE;CN=Attendee 1;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION:mailto:attendee1@example.com
ATTENDEE;CN=Attendee 2;ROLE=OPT-PARTICIPANT;PARTSTAT=ACCEPTED:mailto:attendee2@example.com
END:VEVENT
END:VCALENDAR"""

# Test contact data
TEST_CONTACTS = [
    {"email": "contact1@example.com", "name": "Contact One", "domain": "example.com"},
    {"email": "contact2@example.org", "name": "Contact Two", "domain": "example.org"},
    {"email": "contact3@example.net", "name": "Contact Three", "domain": "example.net"},
]

# API test config
API_TEST_USER = "testuser"
API_TEST_PASSWORD = "testpassword"
API_TEST_SECRET = "testsecret"


def setup_test_environment():
    """Create test directories and set environment variables for testing."""
    # Create test directory if it doesn't exist
    os.makedirs(TEST_DIR, exist_ok=True)

    # Set environment variables for testing
    os.environ["DB_PATH"] = str(TEST_EMAIL_DB)
    os.environ["METADATA_DB_PATH"] = str(TEST_METADATA_DB)
    os.environ["ENABLE_METADATA"] = "true"
    os.environ["EXTRACT_CONTACTS"] = "true"
    os.environ["EXTRACT_CALENDAR_EVENTS"] = "true"
    os.environ["JWT_SECRET"] = API_TEST_SECRET
    os.environ["API_USER"] = API_TEST_USER
    os.environ["API_PASSWORD"] = API_TEST_PASSWORD

    return TEST_DIR


def cleanup_test_environment() -> None:
    """Clean up test databases."""
    if TEST_EMAIL_DB.exists():
        TEST_EMAIL_DB.unlink()

    if TEST_METADATA_DB.exists():
        TEST_METADATA_DB.unlink()
