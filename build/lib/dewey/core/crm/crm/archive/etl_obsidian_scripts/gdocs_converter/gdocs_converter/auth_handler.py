"""
Handle Google Drive API authentication.
"""
import logging
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class GoogleAuthHandler:
    """Handle Google Drive API authentication."""

    # If modifying scopes, delete the token.json file.
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self, config):
        """Initialize the auth handler with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.token_path = self.config.app_dir / 'token.json'
        self.logger.info("Auth handler initialized", extra={
            "component": "auth",
            "action": "initialize",
            "scopes": self.SCOPES,
            "token_path": str(self.token_path)
        })

    def authenticate(self):
        """Authenticate with Google Drive API."""
        try:
            self.logger.info("Starting authentication process", extra={
                "component": "auth",
                "action": "authenticate",
                "status": "starting"
            })
            
            creds = None
            
            # Check if token.json exists
            if os.path.exists(self.token_path):
                self.logger.info("Loading existing credentials", extra={
                    "component": "auth",
                    "action": "load_token",
                    "token_path": str(self.token_path)
                })
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

            # If credentials are invalid or don't exist, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    self.logger.info("Refreshing expired credentials", extra={
                        "component": "auth",
                        "action": "refresh_token"
                    })
                    creds.refresh(Request())
                else:
                    self.logger.info("Initiating OAuth flow", extra={
                        "component": "auth",
                        "action": "oauth_flow",
                        "credentials_path": str(self.config.credentials_path)
                    })
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config.credentials_path, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save the credentials for future use
                self.logger.info("Saving credentials", extra={
                    "component": "auth",
                    "action": "save_token",
                    "token_path": str(self.token_path)
                })
                os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())

            # Build and return the Drive API service
            self.logger.info("Building Drive API service", extra={
                "component": "auth",
                "action": "build_service",
                "status": "success"
            })
            return build('drive', 'v3', credentials=creds)

        except Exception as e:
            self.logger.error("Authentication failed", extra={
                "component": "auth",
                "action": "authenticate",
                "status": "error",
                "error_type": type(e).__name__,
                "error_details": str(e)
            })
            raise 