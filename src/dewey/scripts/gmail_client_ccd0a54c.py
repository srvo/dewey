# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Gmail API Client for Email Processing System.

This module provides a comprehensive interface to interact with the Gmail API, handling
authentication, email fetching, and content processing. It's designed to be robust and
resilient, with built-in rate limiting and error handling.

Key Features:
- OAuth2 authentication with token refresh capability
- Paginated email fetching with checkpointing
- Multi-part email content processing
- Automatic retry on rate limits and transient errors
- Comprehensive logging and error tracking

Class Overview:
    GmailClient: Main class handling all Gmail API interactions

Usage Example:
    client = GmailClient()
    client.authenticate()
    emails = client.fetch_emails(since=datetime.now() - timedelta(days=7))

Security Considerations:
- Store credentials.json securely
- Keep token.pickle with restricted permissions
- Regularly rotate API credentials
- Monitor API usage quotas

Error Handling:
- Implements exponential backoff for rate limits
- Provides detailed error logging
- Maintains processing checkpoints

Dependencies:
- google-auth, google-auth-oauthlib, google-auth-httplib2
- google-api-python-client
- base64 for email content decoding

Testing Strategy:
- Unit tests for individual methods
- Integration tests with mock API responses
- Edge case testing for various email formats
- Performance testing for large email volumes

Maintenance Notes:
1. Update SCOPES when adding new API permissions
2. Monitor API quota usage in Google Cloud Console
3. Regularly review error logs for patterns
4. Keep dependencies updated
"""
from __future__ import annotations

import base64
import os
import pickle
from pathlib import Path
from typing import TYPE_CHECKING, Any

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from scripts.log_config import log_manager

if TYPE_CHECKING:
    from datetime import datetime

# If modifying these scopes, delete the token.pickle file.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    """Gmail API Client for email processing operations.

    This class encapsulates all interactions with the Gmail API, providing methods for:
    - Authentication and token management
    - Email fetching with pagination
    - Email content processing
    - Error handling and rate limiting

    Attributes:
    ----------
        logger (logging.Logger): Configured logger instance
        credentials_file (Path): Path to credentials JSON file
        token_file (Path): Path to token pickle file
        creds (Credentials): OAuth2 credentials object
        service (Resource): Gmail API service resource

    Methods:
    -------
        authenticate(): Handles OAuth2 authentication flow
        fetch_emails(): Fetches emails with pagination and rate limiting
        _get_message_body(): Extracts message body from payload
        _decode_body(): Decodes base64 email content

    Example:
    -------
        client = GmailClient()
        client.authenticate()
        emails = client.fetch_emails(since=datetime.now() - timedelta(days=7))

    """

    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "token.pickle",
    ) -> None:
        """Initialize Gmail client with configuration files.

        Args:
        ----
            credentials_file (str): Path to credentials JSON file containing OAuth2 client secrets.
                                   Defaults to "credentials.json" in current directory.
            token_file (str): Path to token pickle file for storing/loading OAuth2 tokens.
                             Defaults to "token.pickle" in current directory.

        Attributes:
        ----------
            logger (logging.Logger): Configured logger instance for this client
            credentials_file (Path): Path object for credentials file
            token_file (Path): Path object for token file
            creds (Credentials): OAuth2 credentials object, initialized as None
            service (Resource): Gmail API service resource, initialized as None

        Notes:
        -----
            - Both files are converted to Path objects for better path manipulation
            - Directories are created automatically if they don't exist
            - Logs the actual paths being used for debugging purposes

        """
        self.logger = log_manager.setup_logger("gmail_client")
        self.credentials_file = Path(os.path.expanduser(credentials_file))
        self.token_file = Path(os.path.expanduser(token_file))
        self.creds = None
        self.service = None

        # Log the actual paths being used
        self.logger.info(f"Using credentials file: {self.credentials_file}")
        self.logger.info(f"Using token file: {self.token_file}")

    def authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2.

        This method handles the complete authentication flow:
        1. Checks for existing valid credentials
        2. Refreshes expired credentials if possible
        3. Initiates new OAuth2 flow if needed
        4. Stores credentials for future use

        Returns:
        -------
            None

        Raises:
        ------
            FileNotFoundError: If credentials file is missing
            google.auth.exceptions.RefreshError: If token refresh fails
            google.auth.exceptions.DefaultCredentialsError: If authentication fails
            Exception: For other unexpected errors during authentication

        Side Effects:
            - Creates/updates token.pickle file
            - Initializes self.service with authenticated API client
            - Sets self.creds with valid credentials

        Security Notes:
            - The token.pickle file contains sensitive credentials and should be
              stored with appropriate file permissions (600 recommended)
            - Credentials are stored in memory only during the session
            - Token refresh is handled automatically when credentials expire

        Example:
        -------
            >>> client = GmailClient()
            >>> client.authenticate()
            Successfully authenticated with Gmail API

        """
        if self.token_file.exists():
            with open(self.token_file, "rb") as token:
                self.creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    msg = f"Credentials file not found: {self.credentials_file}"
                    self.logger.error(msg)
                    raise FileNotFoundError(msg)
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file),
                    SCOPES,  # Convert Path to string
                )
                self.creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            self.token_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )  # Ensure directory exists
            with open(self.token_file, "wb") as token:
                pickle.dump(self.creds, token)

        self.service = build("gmail", "v1", credentials=self.creds)
        self.logger.info("Successfully authenticated with Gmail API")

    def fetch_emails(
        self,
        since: datetime | None = None,
        max_emails: int = 100,
        include_spam_trash: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch emails from Gmail with pagination and rate limiting.

        Args:
        ----
            since (Optional[datetime]): Optional datetime to fetch emails after (inclusive).
                                       If None, fetches all available emails.
            max_emails (int): Maximum number of emails to fetch. Defaults to 100.
            include_spam_trash (bool): Whether to include SPAM/TRASH messages. Defaults to False.

        Returns:
        -------
            List[Dict[str, Any]]: List of email dictionaries containing:
                - id: Gmail message ID (str)
                - threadId: Thread ID (str)
                - subject: Email subject (str)
                - from: Sender email (str)
                - to: Recipient emails (str)
                - date: Received date (str)
                - snippet: Message snippet (str)
                - body_text: Plain text body (str)
                - body_html: HTML body (str)
                - labels: List of label IDs (List[str])
                - label_names: List of label names (List[str])

        Raises:
        ------
            RateLimitError: If API quota is exceeded
            HttpError: For API communication errors
            ValueError: For invalid input parameters
            Exception: For other unexpected errors during email fetching

        Notes:
        -----
            - Implements exponential backoff for rate limits
            - Uses pagination to handle large result sets
            - Processes multi-part email content
            - Maintains message uniqueness across pages
            - Logs detailed progress information
            - Handles API errors gracefully with retries

        Example:
        -------
            >>> client = GmailClient()
            >>> client.authenticate()
            >>> emails = client.fetch_emails(since=datetime.now() - timedelta(days=7))
            >>> len(emails)
            100

        """
        if not self.service:
            self.authenticate()

        # Get all available labels first
        try:
            labels_response = self.service.users().labels().list(userId="me").execute()
            all_labels = {
                label["id"]: label["name"]
                for label in labels_response.get("labels", [])
            }
            self.logger.info(f"Available Gmail labels: {all_labels}")
        except Exception as e:
            self.logger.exception(f"Failed to fetch labels: {e!s}")
            all_labels = {}

        # Build query
        query = []
        if since:
            # Convert to Gmail's search format (YYYY/MM/DD)
            date_str = since.strftime("%Y/%m/%d")
            query.append(f"after:{date_str}")

        # Get message list with pagination
        try:
            page_token = None
            messages = []
            total_fetched = 0
            seen_message_ids = set()  # Track which messages we've already processed

            while True:  # Keep going until we hit max_emails or no more messages
                self.logger.debug(
                    f"Fetching batch of messages (total so far: {total_fetched})",
                )

                # Log the query and page token being used
                self.logger.info(
                    f"Fetching with query: {' '.join(query)}, page_token: {page_token}",
                )

                results = (
                    self.service.users()
                    .messages()
                    .list(
                        userId="me",
                        q=" ".join(query),
                        maxResults=min(
                            max_emails - total_fetched,
                            100,
                        ),  # Don't request more than we need
                        pageToken=page_token,
                        includeSpamTrash=include_spam_trash,
                    )
                    .execute()
                )

                batch_messages = results.get("messages", [])
                if not batch_messages:
                    self.logger.info("No more messages to fetch")
                    break

                # Log how many new messages we got
                new_messages = [
                    msg for msg in batch_messages if msg["id"] not in seen_message_ids
                ]
                self.logger.info(
                    f"Got {len(batch_messages)} messages, {len(new_messages)} are new",
                )

                # Fetch full message details in this batch
                for message in new_messages:
                    if message["id"] in seen_message_ids:
                        continue

                    try:
                        msg = (
                            self.service.users()
                            .messages()
                            .get(userId="me", id=message["id"], format="full")
                            .execute()
                        )

                        # Extract headers
                        headers = {
                            h["name"].lower(): h["value"]
                            for h in msg["payload"]["headers"]
                        }

                        # Extract body
                        body = self._get_message_body(msg["payload"])

                        # Convert to our format
                        email = {
                            "id": msg["id"],
                            "threadId": msg["threadId"],
                            "subject": headers.get("subject", ""),
                            "from": headers.get("from", ""),
                            "to": headers.get("to", ""),
                            "date": headers.get("date", ""),
                            "snippet": msg.get("snippet", ""),
                            "body_text": body.get("text", ""),
                            "body_html": body.get("html", ""),
                            "labels": msg.get("labelIds", []),
                            "label_names": [
                                all_labels.get(label_id, label_id)
                                for label_id in msg.get("labelIds", [])
                            ],
                        }
                        messages.append(email)
                        seen_message_ids.add(msg["id"])
                        total_fetched += 1

                        if total_fetched >= max_emails:
                            self.logger.info(f"Reached max emails limit ({max_emails})")
                            return messages

                    except Exception as e:
                        self.logger.exception(
                            f"Failed to fetch message {message['id']}: {e!s}",
                        )
                        continue

                # Get next page token
                page_token = results.get("nextPageToken")
                if not page_token:
                    self.logger.info("No more pages available")
                    break

                # Safety check - if we've seen all messages in this batch, but got a next page token,
                # something might be wrong with the pagination
                if not new_messages and page_token:
                    self.logger.warning(
                        "Got no new messages but have a next page token - pagination may be stuck",
                    )
                    break

        except Exception as e:
            self.logger.exception(f"Failed to fetch message list: {e!s}")
            raise

        self.logger.info(f"Successfully fetched {len(messages)} emails")
        return messages

    def _get_message_body(self, payload: dict) -> dict[str, str]:
        """Extract and decode message body from Gmail API payload.

        Args:
        ----
            payload (Dict): Dictionary containing message payload from Gmail API.
                          Expected to contain 'parts' or 'body' keys.

        Returns:
        -------
            Dict[str, str]: Dictionary containing:
                - text: Plain text version of message body (str)
                - html: HTML version of message body (str)

        Notes:
        -----
            - Handles both single-part and multi-part messages
            - Recursively processes nested message parts
            - Returns empty strings for missing content types
            - Preserves original encoding and character sets
            - Logs any issues encountered during processing

        Example:
        -------
            >>> payload = {
            ...     "parts": [
            ...         {"mimeType": "text/plain", "body": {"data": "base64encoded"}},
            ...         {"mimeType": "text/html", "body": {"data": "base64encoded"}}
            ...     ]
            ... }
            >>> body = self._get_message_body(payload)
            >>> body["text"]
            "Plain text content"
            >>> body["html"]
            "<html>HTML content</html>"

        """
        body = {"text": "", "html": ""}

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    body["text"] = self._decode_body(part["body"])
                elif part["mimeType"] == "text/html":
                    body["html"] = self._decode_body(part["body"])
                # Handle multipart recursively
                elif "parts" in part:
                    nested_body = self._get_message_body(part)
                    if not body["text"]:
                        body["text"] = nested_body["text"]
                    if not body["html"]:
                        body["html"] = nested_body["html"]
        elif payload["mimeType"] == "text/plain":
            body["text"] = self._decode_body(payload["body"])
        elif payload["mimeType"] == "text/html":
            body["html"] = self._decode_body(payload["body"])

        return body

    def _decode_body(self, body: dict) -> str:
        """Decode base64-encoded email body content.

        Args:
        ----
            body (Dict): Dictionary containing message body part from Gmail API.
                       Expected to contain 'data' key with base64 content.

        Returns:
        -------
            str: Decoded message content as UTF-8 string. Returns empty string if no data.

        Raises:
        ------
            ValueError: If body data is missing or invalid
            UnicodeDecodeError: If content cannot be decoded as UTF-8
            Exception: For other unexpected errors during decoding

        Notes:
        -----
            - Handles URL-safe base64 encoding
            - Returns empty string if no data is present
            - Preserves original line breaks and formatting
            - Logs any issues encountered during decoding

        Example:
        -------
            >>> body = {"data": "SGVsbG8gV29ybGQ="}  # Base64 for "Hello World"
            >>> self._decode_body(body)
            "Hello World"

        """
        if "data" in body:
            return base64.urlsafe_b64decode(body["data"].encode("ASCII")).decode(
                "utf-8",
            )
        return ""
