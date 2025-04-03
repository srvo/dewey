"""Gmail API utilities for the EmailEnrichment class."""

import base64
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache
import logging


# Disable file cache warning
class MemoryCache(Cache):
    _CACHE = {}

    def get(self, url):
        return MemoryCache._CACHE.get(url)

    def set(self, url, content):
        MemoryCache._CACHE[url] = content


class GmailAPIClient:
    """Client for interacting with Gmail API."""

    def __init__(self, config=None):
        """Initialize the Gmail API client.

        Args:
            config: Configuration object or dictionary with Gmail API settings

        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}

        # Use the specified credentials file
        self.credentials_dir = Path("/Users/srvo/dewey/config/credentials")
        self.credentials_path = self.credentials_dir / "credentials.json"
        self.token_path = self.credentials_dir / "gmail_token.json"

        # Set up scopes
        self.scopes = self.config.get(
            "settings.gmail_scopes",
            [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify",
            ],
        )
        self.oauth_token_uri = self.config.get(
            "settings.oauth_token_uri", "https://oauth2.googleapis.com/token"
        )

        # Lazy-loaded service
        self._service = None

    @property
    def service(self):
        """Get the Gmail API service, building it if necessary."""
        if self._service is None:
            self._service = self.build_gmail_service()
        return self._service

    def build_gmail_service(self, user_email: Optional[str] = None):
        """Build the Gmail API service.

        Args:
            user_email: Email address to impersonate (for domain-wide delegation)

        Returns:
            Gmail API service

        """
        try:
            credentials = None

            # Check if we have a token file
            if os.path.exists(self.token_path):
                self.logger.info(f"Using token from {self.token_path}")
                credentials = Credentials.from_authorized_user_file(
                    self.token_path, self.scopes
                )

            # If no valid credentials, and we have a credentials file
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    self.logger.info("Refreshing expired credentials")
                    credentials.refresh(Request())
                elif os.path.exists(self.credentials_path):
                    self.logger.info(f"Using credentials from {self.credentials_path}")

                    # Load the raw JSON to inspect its format
                    try:
                        with open(self.credentials_path, "r") as f:
                            creds_data = json.load(f)

                        # Check if it's a token file (has 'access_token' field)
                        if "access_token" in creds_data:
                            self.logger.info("Using access token from credentials file")

                            # Create credentials from the token
                            credentials = Credentials(
                                token=creds_data.get("access_token"),
                                refresh_token=creds_data.get("refresh_token"),
                                token_uri=self.oauth_token_uri,
                                client_id=creds_data.get("client_id", ""),
                                client_secret=creds_data.get("client_secret", ""),
                            )

                        # Check if it's an API key
                        elif "api_key" in creds_data:
                            self.logger.info("Using API key from credentials file")
                            # Use API key authentication
                            return build(
                                "gmail",
                                "v1",
                                developerKey=creds_data["api_key"],
                                cache=MemoryCache(),
                            )

                        # Check if it's a service account key file
                        elif (
                            "type" in creds_data
                            and creds_data["type"] == "service_account"
                        ):
                            self.logger.info(
                                "Using service account from credentials file"
                            )
                            credentials = (
                                service_account.Credentials.from_service_account_info(
                                    creds_data, scopes=self.scopes
                                )
                            )

                            # If user_email is provided, use domain-wide delegation
                            if user_email and hasattr(credentials, "with_subject"):
                                credentials = credentials.with_subject(user_email)

                        # Check if it's an OAuth client credentials file
                        elif "installed" in creds_data or "web" in creds_data:
                            self.logger.info(
                                "Using OAuth client credentials from credentials file"
                            )

                            # Create a flow from the credentials file
                            flow = InstalledAppFlow.from_client_secrets_file(
                                self.credentials_path, self.scopes
                            )

                            # Run the OAuth flow to get credentials
                            credentials = flow.run_local_server(port=0)

                            # Save the credentials for future use
                            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
                            with open(self.token_path, "w") as token:
                                token.write(credentials.to_json())
                                self.logger.info(f"Saved token to {self.token_path}")

                        else:
                            self.logger.warning(
                                "Unknown credentials format, falling back to application default credentials"
                            )
                            credentials, _ = google.auth.default(
                                scopes=self.scopes
                                + ["https://www.googleapis.com/auth/cloud-platform"]
                            )

                    except Exception as e:
                        self.logger.warning(f"Failed to parse credentials file: {e}")
                        self.logger.info("Using application default credentials")
                        credentials, _ = google.auth.default(
                            scopes=self.scopes
                            + ["https://www.googleapis.com/auth/cloud-platform"]
                        )
                else:
                    self.logger.warning(
                        f"Credentials file not found at {self.credentials_path}"
                    )
                    self.logger.info("Using application default credentials")
                    # Use application default credentials from gcloud CLI
                    credentials, _ = google.auth.default(
                        scopes=self.scopes
                        + ["https://www.googleapis.com/auth/cloud-platform"]
                    )

            # Build the service with memory cache
            return build("gmail", "v1", credentials=credentials, cache=MemoryCache())
        except Exception as e:
            self.logger.error(f"Failed to build Gmail service: {e}")
            raise

    def fetch_message(
        self, msg_id: str, user_id: str = "me"
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single email message from Gmail API.

        Args:
            msg_id: ID of message to fetch
            user_id: User's email address. The special value "me" can be used for the authenticated user.

        Returns:
            A dict containing the email data, or None if the fetch failed

        """
        try:
            # Get the email message
            message = (
                self.service.users()
                .messages()
                .get(userId=user_id, id=msg_id, format="full")
                .execute()
            )
            return message
        except Exception as e:
            self.logger.error(f"Error fetching message {msg_id}: {e}")
            return None

    def extract_body(self, message: Dict[str, Any]) -> Tuple[str, str]:
        """Extract the email body from a Gmail message.

        Args:
            message: Gmail message object

        Returns:
            Tuple of (plain_text, html)

        """
        payload = message.get("payload", {})
        result = {"text": "", "html": ""}

        if not payload:
            return "", ""

        def decode_part(part):
            if "body" in part and "data" in part["body"]:
                try:
                    data = part["body"]["data"]
                    return base64.urlsafe_b64decode(data).decode("utf-8")
                except Exception as e:
                    self.logger.warning(f"Failed to decode email part: {e}")
                    return ""
            return ""

        def process_part(part):
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                if not result["text"]:  # Only set if not already set
                    result["text"] = decode_part(part)
            elif mime_type == "text/html":
                if not result["html"]:  # Only set if not already set
                    result["html"] = decode_part(part)
            elif "parts" in part:
                for subpart in part["parts"]:
                    process_part(subpart)

        # Process the main payload
        process_part(payload)

        return result["text"], result["html"]
