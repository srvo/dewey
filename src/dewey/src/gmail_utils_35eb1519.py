```python
"""Script to set up and manage Gmail API credentials.

This module handles the authentication flow for Gmail API access, including:
- OAuth2 token generation and management
- Credential file validation
- Token persistence and refresh
- Error handling for credential issues

The module uses Google's OAuth2 flow to authenticate users and store tokens
securely.
"""

import pickle
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import Config  # Import Config directly

# Gmail API scopes - defines the level of access we're requesting
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def load_existing_token(token_path: str) -> Optional[Credentials]:
    """Load credentials from an existing token file.

    Args:
        token_path: Path to the token file.

    Returns:
        Credentials: Loaded credentials object, or None if loading fails.
    """
    try:
        with open(token_path, "rb") as token:
            creds = pickle.load(token)
        return creds
    except Exception as e:
        print(f"Error loading existing token: {e}")
        return None


def save_token(creds: Credentials, token_path: str) -> None:
    """Save credentials to a token file.

    Args:
        creds: Credentials object to save.
        token_path: Path to save the token.
    """
    try:
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)
    except Exception as e:
        print(f"Error saving token: {e}")
        raise


def authenticate(credentials_path: str) -> Credentials:
    """Authenticate and obtain credentials using the OAuth2 flow.

    Args:
        credentials_path: Path to the client secrets file.

    Returns:
        Credentials: Authenticated credentials object.
    """
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    return creds


def setup_credentials() -> Credentials:
    """Set up and manage Gmail API credentials.

    Handles the complete OAuth2 flow including:
    - Checking for existing valid credentials
    - Initiating new authentication if needed
    - Storing credentials securely for future use
    - Handling token refresh and validation

    Returns:
        Credentials: Google API credentials object

    Raises:
        FileNotFoundError: If credentials file is missing
        Exception: For any issues during token loading/storing
    """
    # Initialize credentials as None
    creds: Optional[Credentials] = None

    # Get paths from configuration
    token_path = Config.TOKEN_FILE
    credentials_path = Config.CREDENTIALS_FILE

    # Log paths for debugging
    print(f"Looking for credentials at: {credentials_path}")
    print(f"Token will be saved to: {token_path}")

    # Validate credentials file exists
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Please ensure credentials.json exists at: {credentials_path}"
        )

    # Check for existing token
    if token_path.exists():
        creds = load_existing_token(token_path)
        if creds is None:
            token_path.unlink(missing_ok=True)

    # If no valid credentials, initiate new auth flow
    if not creds or not creds.valid:
        creds = authenticate(credentials_path)

        # Ensure token directory exists
        token_path.parent.mkdir(parents=True, exist_ok=True)

        # Save credentials securely using pickle
        save_token(creds, token_path)

    return creds


if __name__ == "__main__":
    """Main execution block for standalone credential setup."""
    try:
        setup_credentials()
        print("Credentials successfully set up!")
    except Exception as e:
        print(f"Failed to set up credentials: {e}")
        raise
```
