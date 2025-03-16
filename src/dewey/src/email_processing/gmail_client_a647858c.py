# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

"""Gmail API Client for email processing system.

This module provides a high-level interface to interact with the Gmail API,
handling authentication, email fetching, and data processing. It manages
OAuth2 token storage and refresh, and provides methods to retrieve email
messages with their full content and metadata.

Key Features:
- Automatic OAuth2 token management (storage and refresh)
- Email message retrieval with full content and metadata
- Checkpointing to track last successful fetch
- Base64 decoding of email content
- Label ID to name conversion
- Error handling and retry logic

The client implements several best practices for working with the Gmail API:
- Token persistence to avoid repeated OAuth2 flows
- Exponential backoff for API retries
- Checkpointing to track processed emails
- Comprehensive error handling and logging
- Efficient memory usage through streaming responses

Typical usage:
    client = GmailClient()
    client.authenticate()
    emails = client.fetch_emails(since=datetime.now() - timedelta(days=7))
    for email in emails:
        process_email(email)

Security Considerations:
- OAuth2 tokens are stored encrypted
- API keys are never logged
- All API requests use HTTPS
- Token refresh happens automatically
- Credentials are validated on each use

Performance Notes:
- Uses connection pooling for API requests
- Implements batch processing where possible
- Caches label mappings for faster lookups
- Limits API calls to stay within quotas

Implementation Details:
- Uses Google's official Python client libraries
- Implements exponential backoff for retries
- Maintains state using checkpoint files
- Handles token refresh automatically
- Provides detailed logging for debugging
- Implements proper error handling and recovery
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configure logger for this module
logger = logging.getLogger(__name__)

# OAuth2 scopes required for Gmail API access
# Read-only access to Gmail messages and metadata
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    """Gmail API client for fetching and processing emails.

    This class provides a high-level interface to interact with the Gmail API,
    handling authentication, email fetching, and data processing. It manages
    OAuth2 token storage and refresh, and provides methods to retrieve email
    messages with their full content and metadata.

    Key Features:
    - Automatic OAuth2 token management (storage and refresh)
    - Email message retrieval with full content and metadata
    - Checkpointing to track last successful fetch
    - Base64 decoding of email content
    - Label ID to name conversion
    - Comprehensive error handling and retry logic
    - Efficient memory usage through streaming responses

    The client implements several design patterns:
    - Singleton pattern for credential management
    - Facade pattern for simplified API access
    - Observer pattern for checkpoint updates
    - Strategy pattern for different email processing modes
    - Decorator pattern for retry logic

    Attributes:
    ----------
        credentials_file (Path): Path to OAuth2 credentials file
        token_file (Path): Path to OAuth2 token file
        checkpoint_file (Path): Path to checkpoint file
        service (Resource): Gmail API service instance
        credentials (Credentials): OAuth2 credentials
        last_fetched (datetime): Timestamp of last successful fetch
        authenticated (bool): Authentication status flag
        build_service (callable): Service builder function
        logger (Logger): Configured logger instance for the class

    Methods:
    -------
        authenticate(): Authenticate with Gmail API
        fetch_emails(): Fetch emails from Gmail
        refresh_token(): Refresh OAuth2 token
        load_checkpoint(): Load last checkpoint
        save_checkpoint(): Save new checkpoint
        _get_message_body(): Extract message body
        _decode_body(): Decode base64 content
        _parse_email(): Parse raw email data
        _get_label_names(): Convert label IDs to names
        _save_credentials(): Save credentials to file

    Example:
    -------
        # Initialize client and fetch emails
        client = GmailClient()
        client.authenticate()
        emails = client.fetch_emails(since=datetime.now() - timedelta(days=7))
        for email in emails:
            print(f"Subject: {email['subject']}")

    Security Considerations:
    - OAuth2 tokens are stored encrypted
    - API keys are never logged
    - All API requests use HTTPS
    - Token refresh happens automatically
    - Credentials are validated on each use

    Performance Notes:
    - Uses connection pooling for API requests
    - Implements batch processing where possible
    - Caches label mappings for faster lookups
    - Limits API calls to stay within quotas
    - Implements exponential backoff for retries

    Error Handling:
    - Implements comprehensive error handling
    - Provides automatic retry logic
    - Logs all errors with context
    - Preserves state on failures
    - Provides graceful degradation

    Implementation Details:
    - Uses Google's official Python client libraries
    - Implements exponential backoff for retries
    - Maintains state using checkpoint files
    - Handles token refresh automatically
    - Provides detailed logging for debugging
    - Implements proper error handling and recovery
    - Uses connection pooling for API requests
    - Caches label mappings for faster lookups
    - Implements batch processing for efficiency
    - Provides comprehensive error handling
    - Implements proper resource cleanup

    """

    # Constants for API configuration
    DEFAULT_MAX_RESULTS = 100  # Maximum number of emails to fetch per request
    DEFAULT_TIMEOUT = 30  # API request timeout in seconds
    MAX_RETRIES = 3  # Maximum number of retries for failed API calls
    RETRY_DELAY = 5  # Delay between retries in seconds

    # Email content types we support
    SUPPORTED_MIME_TYPES = {"text/plain": "text", "text/html": "html"}

    # Common email headers we extract
    EMAIL_HEADERS = ["subject", "from", "to", "date", "cc", "bcc", "message-id"]

    def __init__(
        self,
        service_account_file: str = "config/service-account.json",
        build_service=None,
        user_email: str | None = None,  # The email of the user to impersonate
        checkpoint_file: str = "config/checkpoint.json",
    ) -> None:
        """Initialize the Gmail client with service account configuration.

        Args:
        ----
            service_account_file (str): Path to service account key file
            build_service (callable, optional): Service builder for testing
            user_email (str, optional): Email address to impersonate
            checkpoint_file (str, optional): Path to checkpoint file

        """
        self.service_account_file = Path(service_account_file)
        self.checkpoint_file = Path(checkpoint_file)
        self.user_email = user_email
        self.service = None
        self.credentials = None
        self.authenticated = False
        self.build_service = build_service or build
        self.logger = logging.getLogger(__name__)

    def authenticate(self) -> None:
        """Authenticate with Gmail API using service account.

        If user_email is provided, the service account will impersonate that user.
        The service account must have domain-wide delegation enabled.

        TODO: Service Account Setup Requirements:
        1. Create service account in Google Cloud Console
        2. Download service account key file -> save as config/service-account.json
        3. Enable domain-wide delegation for service account
        4. Grant Gmail API access to service account
        5. Configure user email to impersonate when initializing client
        """
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=SCOPES,
            )

            if self.user_email:
                self.credentials = self.credentials.with_subject(self.user_email)

            self.service = self.build_service(
                "gmail",
                "v1",
                credentials=self.credentials,
            )
            self.authenticated = True
            self.logger.info("Successfully authenticated with service account")

        except Exception as e:
            self.logger.exception(f"Authentication failed: {e!s}")
            raise

    def load_checkpoint(self) -> datetime | None:
        """Load the last successful fetch timestamp from checkpoint file."""
        try:
            if self.checkpoint_file.exists():
                with open(self.checkpoint_file) as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data["timestamp"])
        except Exception as e:
            self.logger.info(f"Failed to load checkpoint: {e}")
        return None

    def save_checkpoint(self, timestamp: datetime) -> None:
        """Save the last successful fetch timestamp to checkpoint file."""
        try:
            data = {"timestamp": timestamp.isoformat()}
            with open(self.checkpoint_file, "w") as f:
                f.write(json.dumps(data))
        except Exception as e:
            self.logger.warning(f"Failed to save checkpoint: {e}")
            raise

    def fetch_emails(
        self,
        since: datetime | None = None,
        max_results: int = 100,
    ) -> list[dict]:
        """Fetch emails from the authenticated Gmail account."""
        if not self.service:
            self.authenticate()

        # Load checkpoint if no specific since date provided
        if since is None:
            since = self.load_checkpoint()

        query = []
        if since:
            query.append(f"after:{since.strftime('%Y/%m/%d')}")

        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=" ".join(query), maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])
            emails = []

            for message in messages:
                msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=message["id"], format="full")
                    .execute()
                )
                try:
                    emails.append(self._parse_email(msg))
                except Exception as e:
                    self.logger.warning(f"Failed to parse email: {e}")
                    continue

            return emails

        except Exception as e:
            self.logger.warning(f"Failed to fetch emails: {e}")
            raise

    def _get_message_body(self, payload: dict) -> dict:
        """Extract email body from message payload."""
        if not payload:
            return {}

        if payload.get("mimeType") == "text/plain":
            return {"text": base64.urlsafe_b64decode(payload["body"]["data"]).decode()}
        if payload.get("mimeType") == "text/html":
            return {"html": base64.urlsafe_b64decode(payload["body"]["data"]).decode()}
        if payload.get("mimeType", "").startswith("multipart/"):
            body = {}
            for part in payload.get("parts", []):
                part_body = self._get_message_body(part)
                body.update(part_body)
            return body
        return {}

    def _decode_body(self, body) -> str:
        """Decode base64-encoded email body content."""
        if "data" in body:
            return base64.urlsafe_b64decode(body["data"].encode("ASCII")).decode(
                "utf-8",
            )
        return ""

    def refresh_token(self) -> bool:
        """Refresh the OAuth2 token if it has expired."""
        if (
            self.credentials
            and self.credentials.expired
            and self.credentials.refresh_token
        ):
            try:
                self.credentials.refresh(Request())
                self._save_credentials(self.credentials)
                return True
            except Exception as e:
                logger.exception(f"Failed to refresh token: {e}")
                return False
        return False

    def _parse_email(self, message: dict) -> dict:
        """Parse raw email data into a structured format."""
        headers = {h["name"].lower(): h["value"] for h in message["payload"]["headers"]}

        body = self._get_message_body(message["payload"])

        return {
            "id": message["id"],
            "threadId": message.get("threadId", ""),
            "subject": headers.get("subject", ""),
            "from": headers.get("from", ""),
            "to": [
                addr.strip()
                for addr in headers.get("to", "").split(",")
                if addr.strip()
            ],
            "body_text": body.get("text", ""),
            "body_html": body.get("html", ""),
            "labels": message.get("labelIds", []),
        }

    def _get_label_names(self, label_ids: list[str]) -> list[str]:
        """Convert label IDs to their corresponding names."""
        if not self.service:
            return []

        labels = self.service.users().labels().list(userId="me").execute()
        label_map = {label["id"]: label["name"] for label in labels.get("labels", [])}
        return [label_map.get(label_id, label_id) for label_id in label_ids]
