"""Gmail OAuth2 authentication utilities."""

import os
import json
import warnings
import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Suppress the file_cache warning
warnings.filterwarnings(
    "ignore", message="file_cache is only supported with oauth2client<4.0.0"
)

logger = structlog.get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://mail.google.com/",  # Required for IMAP access
]


def get_gmail_service():
    """Get an authorized Gmail service instance."""
    credentials = get_gmail_credentials()
    return build("gmail", "v1", credentials=credentials)


def get_gmail_credentials():
    """Get Gmail OAuth2 credentials."""
    logger.info("getting_gmail_credentials")
    creds = None

    # Try to load existing token
    if os.path.exists("token.json"):
        logger.info("loading_existing_token")
        try:
            with open("token.json", "r") as token:
                token_data = json.load(token)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            logger.error("failed_to_load_token", error=str(e))

    # Check if credentials are valid
    if creds and creds.valid:
        logger.info(
            "credentials_valid",
            expired=creds.expired,
            needs_refresh=creds.refresh_token is not None,
        )
    else:
        logger.info("credentials_invalid_or_missing")

    # Refresh if expired but refresh token exists
    if creds and creds.expired and creds.refresh_token:
        logger.info("refreshing_credentials")
        try:
            creds.refresh(Request())
            save_credentials(creds)
        except Exception as e:
            logger.error("failed_to_refresh_token", error=str(e))
            creds = None

    # If no valid credentials available, get new ones
    if not creds or not creds.valid:
        logger.info("starting_oauth_flow", scopes=SCOPES)
        if not os.path.exists("credentials.json"):
            raise FileNotFoundError("credentials.json not found")

        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)

        # Save credentials for future use
        logger.info("saving_new_credentials")
        save_credentials(creds)

    return creds


def save_credentials(creds):
    """Save credentials to token file."""
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    with open("token.json", "w") as token:
        json.dump(token_data, token)


def get_mailbox(email="sloane@ethicic.com"):
    """Get an authenticated MailBox instance for Gmail."""
    creds = get_gmail_credentials()
    logger.info("creating_mailbox", email=email)

    # Create mailbox with OAuth2
    mailbox = MailBox("imap.gmail.com")
    mailbox.xoauth2(
        email,
        creds.token,
        initial_folder="[Gmail]/All Mail",  # Start in All Mail folder
    )

    return mailbox


def get_imap_auth_string(credentials, email="sloane@ethicic.com"):
    """Get the IMAP OAuth2 authentication string."""
    logger.info("creating_imap_auth_string", email=email)
    auth_string = f"user={email}\1auth=Bearer {credentials.token}\1\1"
    logger.debug("auth_string_created", length=len(auth_string))
    return auth_string
