import argparse
import base64
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add the project root to Python path
repo_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(repo_root))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("gmail_sync")

# Load environment variables
load_dotenv()


class OAuthGmailClient:
    """Gmail client that uses OAuth authentication."""

    def __init__(self, credentials_file, token_file=None, scopes=None):
        self.credentials_file = credentials_file
        self.token_file = token_file or os.path.join(
            os.path.dirname(credentials_file), "gmail_token.json",
        )
        self.scopes = scopes or [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
        ]
        self.service = None
        self.logger = logging.getLogger("gmail_client")

    def authenticate(self):
        """Authenticates with Gmail API using OAuth."""
        creds = None

        if os.path.exists(self.token_file):
            try:
                with open(self.token_file) as token:
                    creds_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(
                        creds_data, self.scopes,
                    )
                self.logger.info("Loaded credentials from token file")
            except Exception as e:
                self.logger.warning(f"Error loading token file: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info("Refreshed expired credentials")
                except Exception as e:
                    self.logger.warning(f"Failed to refresh credentials: {e}")
                    creds = None

            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes,
                    )
                    creds = flow.run_local_server(port=0)
                    self.logger.info("Created new credentials via OAuth flow")

                    os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
                    with open(self.token_file, "w") as token:
                        token.write(creds.to_json())
                    self.logger.info(f"Saved new token to {self.token_file}")
                except Exception as e:
                    self.logger.error(f"OAuth flow failed: {e}")
                    return None

        try:
            self.service = build("gmail", "v1", credentials=creds)
            self.logger.info("Successfully authenticated with Gmail API via OAuth")
            return self.service
        except Exception as e:
            self.logger.error(f"Service build failed: {e}")
            return None

    def fetch_emails(self, query=None, max_results=1000, page_token=None):
        """Fetches emails from Gmail based on the provided query."""
        try:
            results = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=max_results,
                    pageToken=page_token,
                    includeSpamTrash=False,
                )
                .execute()
            )
            return results
        except HttpError as error:
            if error.resp.status == 404:
                self.logger.warning("History ID expired, triggering full sync")
                return None
            self.logger.error(f"An error occurred: {error}")
            return None

    def get_message(self, msg_id, format="full"):
        """Retrieves a specific email message by ID."""
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format=format)
                .execute()
            )
            return message
        except HttpError as error:
            if error.resp.status == 404:
                # Don't log as error, this is expected sometimes
                self.logger.debug(f"Message {msg_id} not found (404)")
                return None
            self.logger.error(f"Error fetching message {msg_id}: {error}")
            return None

    def decode_message_body(self, message):
        """Decodes the message body from base64."""
        try:
            if "data" in message:
                return base64.urlsafe_b64decode(message["data"].encode("ASCII")).decode(
                    "utf-8",
                )
            return ""
        except Exception as e:
            self.logger.error(f"Error decoding message body: {e}")
            return ""

    def get_history(self, start_history_id):
        """Implement history.list API for incremental sync"""
        try:
            return (
                self.service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=start_history_id,
                    historyTypes=[
                        "messageAdded",
                        "messageDeleted",
                        "labelAdded",
                        "labelRemoved",
                    ],
                    maxResults=500,
                )
                .execute()
            )
        except HttpError as error:
            if error.resp.status == 404:
                self.logger.warning("History ID expired or invalid")
                return None
            self.logger.error(f"History API error: {error}")
            return None


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Sync emails from Gmail to database.")
    parser.add_argument(
        "--initial",
        action="store_true",
        help="Perform initial sync instead of incremental",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10000,
        help="Maximum number of emails to sync",
    )
    parser.add_argument(
        "--query", type=str, help='Gmail search query (e.g., "from:user@example.com")',
    )
    parser.add_argument(
        "--credentials",
        type=str,
        default="/Users/srvo/dewey/config/credentials/credentials.json",
        help="Path to Gmail API credentials file",
    )
    parser.add_argument("--token", type=str, help="Path to OAuth token file (optional)")
    parser.add_argument(
        "--db-path",
        type=str,
        default="md:dewey",
        help="Database path (default: md:dewey for MotherDuck, or a file path for local)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
