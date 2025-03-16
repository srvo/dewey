```python
import base64
import json
import logging
import os
import pickle
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource

# Define custom exception for rate limiting
class RateLimitError(Exception):
    """Custom exception for Gmail API rate limits."""
    pass


class GmailClient:
    """
    A comprehensive Gmail API client for interacting with Gmail.

    This class provides methods for authentication, fetching emails,
    and processing email content. It handles OAuth2 authentication,
    rate limiting, pagination, and email body decoding.

    Attributes:
        logger (logging.Logger): Configured logger instance for this client.
        credentials_file (Path): Path object for credentials file.
        token_file (Path): Path object for token file.
        creds (Credentials): OAuth2 credentials object, initialized as None.
        service (Resource): Gmail API service resource, initialized as None.
    """

    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']  # Read-only access

    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "token.pickle",
    ) -> None:
        """
        Initialize Gmail client with configuration files.

        Args:
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
        self.logger = logging.getLogger(__name__)
        self.credentials_file = Path(credentials_file).resolve()
        self.token_file = Path(token_file).resolve()
        self.creds: Optional[Credentials] = None
        self.service: Optional[Resource] = None

        self.logger.info(f"Using credentials file: {self.credentials_file}")
        self.logger.info(f"Using token file: {self.token_file}")

        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

    def authenticate(self) -> None:
        """
        Authenticate with Gmail API using OAuth2.

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
        try:
            if self.token_file.exists():
                with open(self.token_file, "rb") as token:
                    self.creds = pickle.load(token)
        except FileNotFoundError:
            self.logger.warning(f"Token file not found: {self.token_file}. Starting new authentication flow.")
            self.creds = None
        except Exception as e:
            self.logger.error(f"Error loading token file: {e}")
            self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    self.logger.info("Credentials refreshed successfully.")
                except Exception as e:
                    self.logger.error(f"Failed to refresh credentials: {e}")
                    # If refresh fails, start a new flow
                    self.creds = None
            if not self.creds:
                from google_auth_oauthlib.flow import InstalledAppFlow
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                    self.logger.info("New credentials obtained.")
                except FileNotFoundError:
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                except Exception as e:
                    self.logger.error(f"Authentication failed: {e}")
                    raise

            # Save the credentials for the next run
            try:
                with open(self.token_file, "wb") as token:
                    pickle.dump(self.creds, token)
                self.logger.info(f"Credentials saved to {self.token_file}")
            except Exception as e:
                self.logger.error(f"Failed to save credentials: {e}")

        try:
            self.service = build("gmail", "v1", credentials=self.creds)
            self.logger.info("Successfully authenticated with Gmail API")
        except Exception as e:
            self.logger.error(f"Failed to build Gmail service: {e}")
            raise

    def fetch_emails(
        self,
        since: Optional[datetime] = None,
        max_emails: int = 100,
        include_spam_trash: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from Gmail with pagination and rate limiting.

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
            raise Exception("Gmail service not initialized.  Call authenticate() first.")

        if max_emails <= 0:
            raise ValueError("max_emails must be a positive integer.")

        query = []
        if since:
            query.append(f"after:{since.strftime('%Y/%m/%d')}")

        if not include_spam_trash:
            query.append("-in:spam -in:trash")

        all_emails: List[Dict[str, Any]] = []
        seen_message_ids: set[str] = set()
        next_page_token: Optional[str] = None
        total_fetched = 0
        max_results = min(max_emails, 500)  # Gmail API max is 500

        while total_fetched < max_emails:
            try:
                self.logger.info(f"Fetching emails, page {len(all_emails) // max_results + 1}...")
                params: Dict[str, Any] = {
                    "userId": "me",
                    "maxResults": max_results,
                    "q": " ".join(query),
                    "includeSpamTrash": include_spam_trash,
                }
                if next_page_token:
                    params["pageToken"] = next_page_token

                results = (
                    self.service.users()
                    .messages()
                    .list(**params)
                    .execute()
                )

                messages = results.get("messages", [])
                next_page_token = results.get("nextPageToken")

                if not messages:
                    self.logger.info("No more emails found.")
                    break

                batch_message = []
                for message in messages:
                    if message["id"] not in seen_message_ids:
                        batch_message.append(message["id"])
                        seen_message_ids.add(message["id"])

                if not batch_message:
                    self.logger.info("No new emails found on this page.")
                    if not next_page_token:
                        break
                    else:
                        continue

                batch_size = 100  # Gmail API batch limit
                for i in range(0, len(batch_message), batch_size):
                    batch_ids = batch_message[i:i + batch_size]
                    try:
                        batch_response = (
                            self.service.users()
                            .messages()
                            .batchGet(userId="me", ids=batch_ids)
                            .execute()
                        )

                        for message_response in batch_response.get("messages", []):
                            if message_response:
                                try:
                                    email_data = self._parse_email(message_response)
                                    all_emails.append(email_data)
                                    total_fetched += 1
                                    self.logger.debug(f"Fetched email: {email_data['id']}")
                                    if total_fetched >= max_emails:
                                        break
                                except Exception as e:
                                    self.logger.exception(f"Failed to parse email: {e}")
                            else:
                                self.logger.warning(f"Message not found in batch response.")

                    except HttpError as e:
                        if e.resp.status == 429:  # Too Many Requests (Rate Limit)
                            self.logger.warning("Rate limit exceeded. Retrying...")
                            # Implement exponential backoff
                            retry_delay = 2
                            for attempt in range(3):  # Retry up to 3 times
                                try:
                                    import time
                                    time.sleep(retry_delay)
                                    batch_response = (
                                        self.service.users()
                                        .messages()
                                        .batchGet(userId="me", ids=batch_ids)
                                        .execute()
                                    )
                                    for message_response in batch_response.get("messages", []):
                                        if message_response:
                                            try:
                                                email_data = self._parse_email(message_response)
                                                all_emails.append(email_data)
                                                total_fetched += 1
                                                self.logger.debug(f"Fetched email: {email_data['id']}")
                                                if total_fetched >= max_emails:
                                                    break
                                            except Exception as e:
                                                self.logger.exception(f"Failed to parse email: {e}")
                                        else:
                                            self.logger.warning(f"Message not found in batch response.")
                                    break  # Successfully retried
                                except HttpError as retry_e:
                                    if retry_e.resp.status == 429:
                                        self.logger.warning(f"Rate limit exceeded on retry {attempt + 1}.  Waiting...")
                                        retry_delay *= 2  # Exponential backoff
                                    else:
                                        self.logger.error(f"Error during retry: {retry_e}")
                                        raise  # Re-raise other errors
                            else:
                                raise RateLimitError("Rate limit exceeded after multiple retries.")
                        else:
                            self.logger.error(f"HTTP error during batch get: {e}")
                            raise  # Re-raise other HTTP errors

                    if total_fetched >= max_emails:
                        break

                if not next_page_token:
                    self.logger.info("No more pages.")
                    break

            except HttpError as e:
                if e.resp.status == 429:  # Rate Limit
                    self.logger.warning("Rate limit exceeded.  Waiting...")
                    # Implement exponential backoff
                    retry_delay = 2
                    for attempt in range(3):  # Retry up to 3 times
                        try:
                            import time
                            time.sleep(retry_delay)
                            results = (
                                self.service.users()
                                .messages()
                                .list(**params)
                                .execute()
                            )
                            messages = results.get("messages", [])
                            next_page_token = results.get("nextPageToken")
                            if not messages:
                                self.logger.info("No more emails found.")
                                break
                            batch_message = []
                            for message in messages:
                                if message["id"] not in seen_message_ids:
                                    batch_message.append(message["id"])
                                    seen_message_ids.add(message["id"])
                            if not batch_message:
                                self.logger.info("No new emails found on this page.")
                                if not next_page_token:
                                    break
                                else:
                                    continue
                            batch_size = 100  # Gmail API batch limit
                            for i in range(0, len(batch_message), batch_size):
                                batch_ids = batch_message[i:i + batch_size]
                                try:
                                    batch_response = (
                                        self.service.users()
                                        .messages()
                                        .batchGet(userId="me", ids=batch_ids)
                                        .execute()
                                    )
                                    for message_response in batch_response.get("messages", []):
                                        if message_response:
                                            try:
                                                email_data = self._parse_email(message_response)
                                                all_emails.append(email_data)
                                                total_fetched += 1
                                                self.logger.debug(f"Fetched email: {email_data['id']}")
                                                if total_fetched >= max_emails:
                                                    break
                                            except Exception as e:
                                                self.logger.exception(f"Failed to parse email: {e}")
                                        else:
                                            self.logger.warning(f"Message not found in batch response.")
                                except HttpError as e:
                                    if e.resp.status == 429:
                                        self.logger.warning(f"Rate limit exceeded on retry {attempt + 1}.  Waiting...")
                                        retry_delay *= 2  # Exponential backoff
                                    else:
                                        self.logger.error(f"Error during retry: {e}")
                                        raise  # Re-raise other errors
                                    break
                                if total_fetched >= max_emails:
                                    break
                            if not next_page_token:
                                self.logger.info("No more pages.")
                                break
                            break  # Successfully retried
                        except HttpError as retry_e:
                            if retry_e.resp.status == 429:
                                self.logger.warning(f"Rate limit exceeded on retry {attempt + 1}.  Waiting...")
                                retry_delay *= 2  # Exponential backoff
                            else:
                                self.logger.error(f"Error during retry: {retry_e}")
                                raise  # Re-raise other errors
                    else:
                        raise RateLimitError("Rate limit exceeded after multiple retries.")
                else:
                    self.logger.error(f"HTTP error during list: {e}")
                    raise  # Re-raise other HTTP errors
            except Exception as e:
                self.logger.exception(f"An unexpected error occurred: {e}")
                raise

        self.logger.info(f"Fetched a total of {len(all_emails)} emails.")
        return all_emails

    def _get_message_body(self, payload: Dict) -> Dict[str, str]:
        """
        Extract and decode message body from Gmail API payload.

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
        text_body = ""
        html_body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    text_body = self._decode_body(part.get("body", {}))
                elif part["mimeType"] == "text/html":
                    html_body = self._decode_body(part.get("body", {}))
                elif "parts" in part:
                    # Recursive call for nested parts (e.g., multipart/alternative)
                    nested_body = self._get_message_body(part)
                    text_body = text_body or nested_body.get("text", "")
                    html_body = html_body or nested_body.get("html", "")
        elif "body" in payload:
            if payload.get("mimeType") == "text/plain":
                text_body = self._decode_body(payload.get("body", {}))
            elif payload.get("mimeType") == "text/html":
                html_body = self._decode_body(payload.get("body", {}))
            else:
                self.logger.debug(f"Unhandled mimeType: {payload.get('mimeType')}")

        return {"text": text_body, "html": html_body}

    def _decode_body(self, body: Dict) -> str:
        """
        Decode base64-encoded email body content.

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
        try:
            data = body.get("data")
            if not data:
                return ""
            decoded_bytes = base64.urlsafe_b64decode(data.encode("ASCII"))
            return decoded_bytes.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as e:
            self.logger.error(f"Error decoding email body: {e}")
            return ""
        except Exception as e:
            self.logger.exception(f"Unexpected error during decoding: {e}")
            return ""

    def _parse_email(self, message: Dict) -> Dict[str, Any]:
        """
        Parse raw email data into a structured format.

        Args:
            message (Dict): The raw message data from the Gmail API.

        Returns:
            Dict[str, Any]: A dictionary containing the parsed email data.
        """
        headers = message["payload"]["headers"]
        headers_dict = {h["name"].lower(): h["value"] for h in headers}

        email_data: Dict[str, Any] = {
            "id": message["id"],
            "threadId": message["threadId"],
            "subject": headers_dict.get("subject", ""),
            "from": headers_dict.get("from", ""),
            "to": headers_dict.get("to", ""),
            "date": headers_dict.get("date", ""),
            "snippet": message.get("snippet", ""),
            "body_text": "",
            "body_html": "",
            "labels": message.get("labelIds", []),
            "label_names": [],
        }

        body = self._get_message_body(message["payload"])
        email_data["body_text"] = body.get("text", "")
        email_data["body_html"] = body.get("html", "")
        email_data["label_names"] = self._get_label_names(email_data["labels"])

        return email_data

    def _get_label_names(self, label_ids: List[str]) -> List[str]:
        """
        Convert label IDs to their corresponding names.

        Args:
            label_ids (List[str]): A list of label IDs.

        Returns:
            List[str]: A list of label names.
        """
        label_names = []
        try:
            labels_response = (
                self.service.users().labels().list(userId="me").execute()
            )
            label_map = {label["id"]: label["name"] for label in labels_response.get("labels", [])}
            for label_id in label_ids:
                label_name = label_map.get(label_id)
                if label_name:
                    label_names.append(label_name)
        except Exception as e:
            self.logger.error(f"Failed to retrieve label names: {e}")
        return label_names

    def refresh_token(self) -> None:
        """
        Refresh the OAuth2 token if it has expired.
        """
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                self.logger.info("Token refreshed successfully.")
            except Exception as e:
                self.logger.exception(f"Failed to refresh token: {e}")
                self.creds.expired = False  # Prevent infinite loop if refresh fails
        else:
            self.logger.debug("Token is not expired or refresh token is not available.")

    def __init__(
        self,
        service_account_file: str,
        build_service: Optional[Callable] = None,
        user_email: Optional[str] = None,
        checkpoint_file: str = "checkpoint.json",
    ) -> None:
        """
        Initialize the Gmail client with service account configuration.

        Args:
        ----
            service_account_file (str): Path to service account key file
            build_service (callable, optional): Service builder for testing
            user_email (str, optional): Email address to impersonate
            checkpoint_file (str, optional): Path to checkpoint file
        """
        self.logger = logging.getLogger(__name__)
        self.service_account_file = service_account_file
        self.user_email = user_email
        self.checkpoint_file = checkpoint_file
        self.service: Optional[Resource] = None
        self.credential: Optional[Credentials] = None
        self.authenticate()

    def authenticate(self) -> None:
        """
        Authenticate with Gmail API using service account.

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
            from google.oauth2 import service_account
            self.credential = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.SCOPES
            )
            if self.user_email:
                self.credential = self.credential.with_subject(self.user_email)
            self.service = build("gmail", "v1", credentials=self.credential)
            self.logger.info("Successfully authenticated with Gmail API using service account.")
        except Exception as e:
            self.logger.exception(f"Authentication failed: {e}")
            raise

    def load_checkpoint(self) -> Optional[datetime]:
        """
        Load the last successful fetch timestamp from checkpoint file.
        """
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, "r") as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data["timestamp"])
            else:
                self.logger.info(f"Checkpoint file not found: {self.checkpoint_file}")
                return None
        except Exception as e:
            self.logger.exception(f"Failed to load checkpoint: {e}")
            return None

    def save_checkpoint(self, timestamp: datetime) -> None:
        """
        Save the last successful fetch timestamp to checkpoint file.
        """
        try:
            data = {"timestamp": timestamp.isoformat()}
            with open(self.checkpoint_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            self.logger.warning(f"Failed to save checkpoint: {e}")

    def fetch_emails(
        self,
        since: Optional[datetime] = None,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from the authenticated Gmail account.
        """
        if not self.service:
            self.authenticate()

        all_emails: List[Dict[str, Any]] = []
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

            for message in messages:
                try:
                    message_data = self._parse_email(message)
                    all_emails.append(message_data)
                except Exception as e:
                    self.logger.warning(f"Failed to parse message: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to fetch emails: {e}")
            raise

        return all_emails

    def _get_message_body(self, payload: Dict) -> Dict[str, str]:
        """
        Extract email body from message payload.
        """
        text_body = ""
        html_body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    text_body = self._decode_body(part)
                elif part.get("mimeType") == "text/html":
                    html_body = self._decode_body(part)
                elif "parts" in part:
                    nested_body = self._get_message_body(part)
                    text_body = text_body or nested_body.get("text", "")
                    html_body = html_body or nested_body.get("html", "")
        elif "body" in payload:
            if payload.get("mimeType") == "text/plain":
                text_body = self._decode_body(payload)
            elif payload.get("mimeType") == "text/html":
                html_body = self._decode_body(payload)

        return {"text": text_body, "html": html_body}

    def _decode_body(self, body: Dict) -> str:
        """
        Decode base64-encoded email body content.
        """
        try:
            if "data" in body:
                return base64.urlsafe_b64decode(body["data"].encode("ASCII")).decode()
            else:
                return ""
        except Exception as e:
            self.logger.exception(f"Error decoding body: {e}")
            return ""

    def _parse_email(self, message: Dict) -> Dict[str, Any]:
        """
        Parse raw email data into a structured format.
        """
        headers = message["payload"]["headers"]
        headers_dict = {h["name"].lower(): h["value"] for h in headers}

        email_data: Dict[str, Any] = {
            "id": message["id"],
            "threadId": message["threadId"],
            "subject": headers_dict.get("subject", ""),
            "from": headers_dict.get("from", ""),
            "to": headers_dict.get("to", ""),
            "date": headers_dict.get("date", ""),
            "body_text": "",
            "body_html": "",
        }

        body = self._get_message_body(message["payload"])
        email_data["body_text"] = body.get("text", "")
        email_data["body_html"] = body.get("html", "")

        return email_data
```
