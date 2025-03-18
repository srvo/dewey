"""Tests for the email processor module."""

import base64
from datetime import datetime
import pytest
from dewey.core.crm.gmail.email_processor import EmailProcessor

def test_process_email(sample_email_data):
    """Test processing a complete email message."""
    processor = EmailProcessor()
    result = processor.process_email(sample_email_data)
    
    assert result is not None
    assert result['gmail_id'] == 'msg123'
    assert result['thread_id'] == 'thread123'
    assert result['subject'] == 'Test Email'
    assert len(result['from_addresses']) == 1
    assert result['from_addresses'][0]['name'] == 'John Doe'
    assert result['from_addresses'][0]['email'] == 'john@example.com'
    assert len(result['to_addresses']) == 1
    assert result['to_addresses'][0]['name'] == 'Jane Smith'
    assert result['to_addresses'][0]['email'] == 'jane@example.com'

def test_parse_email_addresses():
    """Test parsing various email address formats."""
    processor = EmailProcessor()
    
    # Test cases
    test_cases = [
        (
            'John Doe <john@example.com>',
            [{'name': 'John Doe', 'email': 'john@example.com'}]
        ),
        (
            'john@example.com',
            [{'name': '', 'email': 'john@example.com'}]
        ),
        (
            'John Doe <john@example.com>, Jane Smith <jane@example.com>',
            [
                {'name': 'John Doe', 'email': 'john@example.com'},
                {'name': 'Jane Smith', 'email': 'jane@example.com'}
            ]
        ),
        (
            '',
            []
        )
    ]
    
    for input_str, expected in test_cases:
        result = processor._parse_email_addresses(input_str)
        assert result == expected

def test_get_message_body():
    """Test extracting message body from different payload structures."""
    processor = EmailProcessor()
    
    # Test plain text
    plain_payload = {
        'mimeType': 'text/plain',
        'body': {'data': base64.urlsafe_b64encode(b'Plain text').decode()}
    }
    result = processor._get_message_body(plain_payload)
    assert result['text'] == 'Plain text'
    assert result['html'] == ''
    
    # Test HTML
    html_payload = {
        'mimeType': 'text/html',
        'body': {'data': base64.urlsafe_b64encode(b'<p>HTML</p>').decode()}
    }
    result = processor._get_message_body(html_payload)
    assert result['text'] == ''
    assert result['html'] == '<p>HTML</p>'
    
    # Test multipart
    multipart_payload = {
        'mimeType': 'multipart/alternative',
        'parts': [
            {
                'mimeType': 'text/plain',
                'body': {'data': base64.urlsafe_b64encode(b'Plain text').decode()}
            },
            {
                'mimeType': 'text/html',
                'body': {'data': base64.urlsafe_b64encode(b'<p>HTML</p>').decode()}
            }
        ]
    }
    result = processor._get_message_body(multipart_payload)
    assert result['text'] == 'Plain text'
    assert result['html'] == '<p>HTML</p>'

def test_decode_body():
    """Test decoding base64-encoded body content."""
    processor = EmailProcessor()
    
    # Test valid base64
    encoded_text = base64.urlsafe_b64encode(b'Test message').decode()
    body = {'data': encoded_text}
    result = processor._decode_body(body)
    assert result == 'Test message'
    
    # Test empty body
    result = processor._decode_body({})
    assert result == ''

def test_parse_email_date():
    """Test parsing email date strings."""
    processor = EmailProcessor()
    
    # Test valid date string
    date_str = 'Mon, 15 Mar 2024 10:00:00 -0700'
    result = processor._parse_email_date(date_str)
    assert isinstance(result, datetime)
    assert result.year == 2024
    assert result.month == 3
    assert result.day == 15
    
    # Test empty date string
    result = processor._parse_email_date('')
    assert isinstance(result, datetime)
    
    # Test invalid date string
    result = processor._parse_email_date('invalid date')
    assert isinstance(result, datetime)

def test_process_email_error_handling():
    """Test error handling in process_email."""
    processor = EmailProcessor()
    
    # Test with None input
    result = processor.process_email(None)
    assert result is None
    
    # Test with invalid data structure
    result = processor.process_email({})
    assert result is None
    
    # Test with missing payload
    result = processor.process_email({'id': 'test'})
    assert result is None 