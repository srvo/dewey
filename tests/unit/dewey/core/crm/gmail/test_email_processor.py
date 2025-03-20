import base64
import logging
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from zoneinfo import ZoneInfo

from dewey.core.crm.gmail.email_processor import EmailProcessor

MOUNTAIN_TZ = ZoneInfo("America/Denver")


@pytest.fixture
def email_processor() -> EmailProcessor:
    """Fixture to create an EmailProcessor instance."""
    processor = EmailProcessor()
    processor.logger = MagicMock()  # Mock the logger
    return processor


@pytest.fixture
def mock_email_data() -> Dict[str, Any]:
    """Fixture to provide mock email data."""
    return {
        "id": "12345",
        "threadId": "67890",
        "sizeEstimate": 1024,
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "From", "value": "John Doe <john.doe@example.com>"},
                {"name": "To", "value": "Jane Doe <jane.doe@example.com>"},
                {"name": "Cc", "value": "cc.doe@example.com"},
                {"name": "Bcc", "value": "bcc.doe@example.com"},
                {"name": "Subject", "value": "Test Email"},
                {"name": "Date", "value": "Tue, 1 Jan 2024 00:00:00 MST"},
            ],
            "mimeType": "multipart/alternative",
            "body": {},
            "parts": [
                {
                    "partId": "0",
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(b"This is plain text.").decode(
                            "ASCII"
                        )
                    },
                },
                {
                    "partId": "1",
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.urlsafe_b64encode(
                            b"<html><body>This is HTML.</body></html>"
                        ).decode("ASCII")
                    },
                },
            ],
        },
    }


def test_email_processor_initialization(email_processor: EmailProcessor) -> None:
    """Test that the EmailProcessor is initialized correctly."""
    assert isinstance(email_processor, EmailProcessor)
    assert email_processor.name == "EmailProcessor"
    assert email_processor.config is not None
    assert email_processor.logger is not None


def test_process_email_success(
    email_processor: EmailProcessor, mock_email_data: Dict[str, Any]
) -> None:
    """Test successful email processing."""
    email_info = email_processor.process_email(mock_email_data)

    assert email_info is not None
    assert email_info["gmail_id"] == "12345"
    assert email_info["thread_id"] == "67890"
    assert email_info["subject"] == "Test Email"
    assert len(email_info["from_addresses"]) == 1
    assert email_info["from_addresses"][0]["name"] == "John Doe"
    assert email_info["from_addresses"][0]["email"] == "john.doe@example.com"
    assert len(email_info["to_addresses"]) == 1
    assert email_info["to_addresses"][0]["name"] == "Jane Doe"
    assert email_info["to_addresses"][0]["email"] == "jane.doe@example.com"
    assert len(email_info["cc_addresses"]) == 1
    assert email_info["cc_addresses"][0]["name"] == ""
    assert email_info["cc_addresses"][0]["email"] == "cc.doe@example.com"
    assert len(email_info["bcc_addresses"]) == 1
    assert email_info["bcc_addresses"][0]["name"] == ""
    assert email_info["bcc_addresses"][0]["email"] == "bcc.doe@example.com"
    assert email_info["received_date"] == datetime(
        2024, 1, 1, 7, 0, 0, tzinfo=MOUNTAIN_TZ
    )
    assert email_info["size_estimate"] == 1024
    assert email_info["labels"] == ["INBOX", "UNREAD"]
    assert email_info["body_text"] == "This is plain text."
    assert email_info["body_html"] == "<html><body>This is HTML.</body></html>"


def test_process_email_missing_headers(
    email_processor: EmailProcessor, mock_email_data: Dict[str, Any]
) -> None:
    """Test email processing with missing headers."""
    del mock_email_data["payload"]["headers"]
    email_info = email_processor.process_email(mock_email_data)

    assert email_info is not None
    assert email_info["subject"] == ""
    assert email_info["from_addresses"] == []
    assert email_info["to_addresses"] == []
    assert email_info["cc_addresses"] == []
    assert email_info["bcc_addresses"] == []


def test_process_email_no_parts(
    email_processor: EmailProcessor, mock_email_data: Dict[str, Any]
) -> None:
    """Test email processing with no parts in the payload."""
    mock_email_data["payload"].pop("parts")
    mock_email_data["payload"]["mimeType"] = "text/plain"
    mock_email_data["payload"]["body"] = {
        "data": base64.urlsafe_b64encode(b"This is plain text.").decode("ASCII")
    }
    email_info = email_processor.process_email(mock_email_data)

    assert email_info is not None
    assert email_info["body_text"] == "This is plain text."
    assert email_info["body_html"] == ""


def test_process_email_empty_payload(email_processor: EmailProcessor) -> None:
    """Test email processing with an empty payload."""
    email_data: Dict[str, Any] = {"id": "123"}
    email_info = email_processor.process_email(email_data)

    assert email_info is not None
    assert email_info["subject"] == ""
    assert email_info["from_addresses"] == []
    assert email_info["to_addresses"] == []
    assert email_info["cc_addresses"] == []
    assert email_info["bcc_addresses"] == []
    assert email_info["body_text"] == ""
    assert email_info["body_html"] == ""


def test_process_email_exception(
    email_processor: EmailProcessor, mock_email_data: Dict[str, Any]
) -> None:
    """Test email processing when an exception occurs."""
    # Simulate an exception during header extraction
    mock_email_data["payload"]["headers"] = None  # type: ignore
    email_info = email_processor.process_email(mock_email_data)

    assert email_info is None
    email_processor.logger.error.assert_called_once()


@pytest.mark.parametrize(
    "header_value, expected_addresses",
    [
        (
            "John Doe <john.doe@example.com>, Jane Doe <jane.doe@example.com>",
            [
                {"name": "John Doe", "email": "john.doe@example.com"},
                {"name": "Jane Doe", "email": "jane.doe@example.com"},
            ],
        ),
        ("john.doe@example.com", [{"name": "", "email": "john.doe@example.com"}]),
        ("", []),
        ("  ", []),
        (
            "John Doe <john.doe@example.com>",
            [{"name": "John Doe", "email": "john.doe@example.com"}],
        ),
        (
            "  John Doe  <  john.doe@example.com  >  ",
            [{"name": "John Doe", "email": "john.doe@example.com"}],
        ),
        ("  John Doe  ", [{"name": "", "email": "John Doe"}]),
    ],
)
def test_parse_email_addresses(
    email_processor: EmailProcessor,
    header_value: str,
    expected_addresses: List[Dict[str, str]],
) -> None:
    """Test parsing of email addresses from header values."""
    addresses = email_processor._parse_email_addresses(header_value)
    assert addresses == expected_addresses


def test_get_message_body_text_html(
    email_processor: EmailProcessor, mock_email_data: Dict[str, Any]
) -> None:
    """Test extracting message body with both text and HTML parts."""
    body = email_processor._get_message_body(mock_email_data["payload"])
    assert body["text"] == "This is plain text."
    assert body["html"] == "<html><body>This is HTML.</body></html>"


def test_get_message_body_nested_parts(
    email_processor: EmailProcessor, mock_email_data: Dict[str, Any]
) -> None:
    """Test extracting message body with nested parts."""
    nested_payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(b"Nested plain text.").decode(
                        "ASCII"
                    )
                },
            },
            {
                "mimeType": "text/html",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        b"<html><body>Nested HTML.</body></html>"
                    ).decode("ASCII")
                },
            },
        ],
    }
    mock_email_data["payload"]["parts"] = [nested_payload]
    body = email_processor._get_message_body(mock_email_data["payload"])
    assert body["text"] == "Nested plain text."
    assert body["html"] == "<html><body>Nested HTML.</body></html>"


def test_get_message_body_only_text(email_processor: EmailProcessor) -> None:
    """Test extracting message body with only a text part."""
    payload: Dict[str, Any] = {
        "mimeType": "text/plain",
        "body": {"data": base64.urlsafe_b64encode(b"Only plain text.").decode("ASCII")},
    }
    body = email_processor._get_message_body(payload)
    assert body["text"] == "Only plain text."
    assert body["html"] == ""


def test_get_message_body_only_html(email_processor: EmailProcessor) -> None:
    """Test extracting message body with only an HTML part."""
    payload: Dict[str, Any] = {
        "mimeType": "text/html",
        "body": {
            "data": base64.urlsafe_b64encode(
                b"<html><body>Only HTML.</body></html>"
            ).decode("ASCII")
        },
    }
    body = email_processor._get_message_body(payload)
    assert body["text"] == ""
    assert body["html"] == "<html><body>Only HTML.</body></html>"


def test_get_message_body_empty(email_processor: EmailProcessor) -> None:
    """Test extracting message body when the payload is empty."""
    payload: Dict[str, Any] = {}
    body = email_processor._get_message_body(payload)
    assert body["text"] == ""
    assert body["html"] == ""


def test_decode_body(email_processor: EmailProcessor) -> None:
    """Test decoding a base64-encoded body."""
    body = {"data": base64.urlsafe_b64encode(b"Decoded text.").decode("ASCII")}
    decoded_text = email_processor._decode_body(body)
    assert decoded_text == "Decoded text."


def test_decode_body_empty(email_processor: EmailProcessor) -> None:
    """Test decoding an empty body."""
    body: Dict[str, Any] = {}
    decoded_text = email_processor._decode_body(body)
    assert decoded_text == ""


def test_parse_email_date(email_processor: EmailProcessor) -> None:
    """Test parsing a valid email date."""
    date_str = "Tue, 1 Jan 2024 00:00:00 MST"
    parsed_date = email_processor._parse_email_date(date_str)
    assert parsed_date == datetime(2024, 1, 1, 7, 0, 0, tzinfo=MOUNTAIN_TZ)


def test_parse_email_date_empty(email_processor: EmailProcessor) -> None:
    """Test parsing an empty email date."""
    date_str = ""
    parsed_date = email_processor._parse_email_date(date_str)
    assert isinstance(parsed_date, datetime)
    assert parsed_date.tzinfo == MOUNTAIN_TZ


def test_parse_email_date_invalid(email_processor: EmailProcessor) -> None:
    """Test parsing an invalid email date."""
    date_str = "Invalid Date"
    parsed_date = email_processor._parse_email_date(date_str)
    assert isinstance(parsed_date, datetime)
    assert parsed_date.tzinfo == MOUNTAIN_TZ
    email_processor.logger.error.assert_called_once()


def test_run_method(email_processor: EmailProcessor) -> None:
    """Test the run method (which should do nothing)."""
    email_processor.run()
    email_processor.logger.info.assert_called_with(
        "EmailProcessor.run() called, but has no implementation."
    )
