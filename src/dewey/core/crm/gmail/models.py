from typing import List, Optional, Dict
from datetime import datetime

class RawEmail:
    """Represents a raw email message."""
    def __init__(
        self,
        gmail_id: str,
        thread_id: str,
        subject: str,
        snippet: str,
        plain_body: str,
        html_body: str,
        from_name: str,
        from_email: str,
        to_addresses: List[str],
        cc_addresses: List[str],
        bcc_addresses: List[str],
        received_date: datetime,
        labels: List[str],
        size_estimate: int,
        ):
        self.gmail_id = gmail_id
        self.thread_id = thread_id
        self.subject = subject
        self.snippet = snippet
        self.plain_body = plain_body
        self.html_body = html_body
        self.from_name = from_name
        self.from_email = from_email
        self.to_addresses = to_addresses
        self.cc_addresses = cc_addresses
        self.bcc_addresses = bcc_addresses
        self.received_date = received_date
        self.labels = labels
        self.size_estimate = size_estimate
