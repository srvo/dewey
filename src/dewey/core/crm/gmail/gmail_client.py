import base64
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dewey.core.base_script import BaseScript


class GmailClient(BaseScript):
    """Handles Gmail API authentication and interactions."""

    def __init__(
        self,
        service_account_file: str,
        user_email: str | None = None,
        scopes: list[str] | None = None,
    ) -> None:
        """
        Initializes the Gmail client with service account credentials.

        Args:
        ----
            service_account_file: Path to the service account JSON file.
            user_email: Optional user email to impersonate (for domain-wide delegation).
            scopes: List of API scopes to request.

        """
        super().__init__(config_section="crm")
        self.service_account_file = service_account_file
        self.user_email = user_email
        self.scopes = scopes or self.get_config_value(
            "gmail_scopes", ["https://www.googleapis.com/auth/gmail.readonly"],
        )
        self.creds = None
        self.service = None

    def authenticate(self) -> Any | None:
        """
        Authenticates with Gmail API using a service account.

        Returns
        -------
            The Gmail service object if authentication is successful, otherwise None.

        """
        try:
            creds = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.scopes,
            )
            if self.user_email:
                creds = creds.with_subject(self.user_email)

            self.service = build("gmail", "v1", credentials=creds)
            self.logger.info(
                "Successfully authenticated with Gmail API using service account",
            )
            return self.service
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return None

    def fetch_emails(
        self, query: str = None, max_results: int = 100, page_token: str = None,
    ) -> dict[str, Any] | None:
        """
        Fetches emails from Gmail based on the provided query.

        Args:
        ----
            query: Gmail search query (e.g., "from:user@example.com").
            max_results: Maximum number of emails to return per page.
            page_token: Token for retrieving the next page of results.

        Returns:
        -------
            A dictionary containing the list of emails and the next page token, or None if an error occurred.

        """
        try:
            results = (
                self.service.users()
                .messages()
                .list(
                    userId="me", q=query, maxResults=max_results, pageToken=page_token,
                )
                .execute()
            )
            return results
        except HttpError as error:
            self.logger.error(f"An error occurred: {error}")
            return None

    def get_message(self, msg_id: str, format: str = "full") -> dict[str, Any] | None:
        """
        Retrieves a specific email message by ID.

        Args:
        ----
            msg_id: The ID of the email message to retrieve.
            format: The format of the message to retrieve (e.g., 'full', 'metadata', 'raw').

        Returns:
        -------
            A dictionary containing the email message, or None if an error occurred.

        """
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format=format)
                .execute()
            )
            return message
        except HttpError as error:
            self.logger.error(f"An error occurred: {error}")
            return None

    def decode_message_body(self, message: dict[str, Any]) -> str:
        """
        Decodes the message body from base64.

        Args:
        ----
            message: The email message dictionary.

        Returns:
        -------
            The decoded message body as a string.

        """
        try:
            if "data" in message:
                return base64.urlsafe_b64decode(message["data"].encode("ASCII")).decode(
                    "utf-8",
                )
            return ""
        except Exception as e:
            self.logger.error(f"Error decoding message body: {e}")
            return ""

    def execute(self) -> None:
        """Main execution method for GmailClient."""
        self.logger.info("GmailClient execute method called.")
        # Add your main logic here, e.g., fetching and processing emails.
        # Example:
        # emails = self.fetch_emails(query="from:example@example.com", max_results=10)
        # if emails:
        #     for email in emails['messages']:
        #         message = self.get_message(email['id'])
        #         if message:
        #             body = self.decode_message_body(message['payload'])
        #             self.logger.info(f"Email body: {body[:100]}...")  # Print first 100 chars
        # else:
        #     self.logger.info("No emails found.")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()
