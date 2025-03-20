"""Tests for Gmail models."""

from datetime import datetime
import pytest
from dewey.core.crm.gmail.models import RawEmail

def test_raw_email_creation():
    """Test creating a RawEmail instance."""
    now = datetime.now()
    email = RawEmail(
        gmail_id="msg123",
        thread_id="thread123",
        subject="Test Subject",
        snippet="Test snippet",
        plain_body="Test body",
        html_body="<p>Test body</p>",
        from_name="John Doe",
        from_email="john@example.com",
        to_addresses=["jane@example.com"],
        cc_addresses=["cc@example.com"],
        bcc_addresses=["bcc@example.com"],
        received_date=now,
        labels=["INBOX", "UNREAD"],
        size_estimate=1024
    )
    
    assert email.gmail_id == "msg123"
    assert email.thread_id == "thread123"
    assert email.subject == "Test Subject"
    assert email.snippet == "Test snippet"
    assert email.plain_body == "Test body"
    assert email.html_body == "<p>Test body</p>"
    assert email.from_name == "John Doe"
    assert email.from_email == "john@example.com"
    assert email.to_addresses == ["jane@example.com"]
    assert email.cc_addresses == ["cc@example.com"]
    assert email.bcc_addresses == ["bcc@example.com"]
    assert email.received_date == now
    assert email.labels == ["INBOX", "UNREAD"]
    assert email.size_estimate == 1024

def test_raw_email_empty_lists():
    """Test RawEmail with empty address lists."""
    now = datetime.now()
    email = RawEmail(
        gmail_id="msg123",
        thread_id="thread123",
        subject="Test Subject",
        snippet="Test snippet",
        plain_body="Test body",
        html_body="<p>Test body</p>",
        from_name="John Doe",
        from_email="john@example.com",
        to_addresses=[],
        cc_addresses=[],
        bcc_addresses=[],
        received_date=now,
        labels=[],
        size_estimate=1024
    )
    
    assert email.to_addresses == []
    assert email.cc_addresses == []
    assert email.bcc_addresses == []
    assert email.labels == [] 