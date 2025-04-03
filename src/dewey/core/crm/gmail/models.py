from typing import Any

from dewey.core.base_script import BaseScript


class GmailModel(BaseScript):
    """A model for interacting with Gmail within Dewey.

    This class inherits from BaseScript and provides a standardized
    structure for Gmail-related scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the GmailModel.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        super().__init__(*args, **kwargs)
        self.name = "GmailModel"
        self.description = "A base model for Gmail interactions."

    def run(self) -> None:
        """Executes the primary logic of the Gmail model."""
        self.logger.info("Starting Gmail model run...")

        # Example of accessing configuration
        api_key = self.get_config_value("gmail_api_key", default="default_key")
        self.logger.debug(f"Gmail API Key: {api_key}")

        # Add your Gmail interaction logic here
        self.logger.info("Gmail model run completed.")

    def some_method(self, arg1: str, arg2: int) -> str:
        """An example method.

        Args:
            arg1: A string argument.
            arg2: An integer argument.

        Returns:
            A string result.

        """
        self.logger.info(f"Executing some_method with arg1={arg1}, arg2={arg2}")
        return f"Result: {arg1} - {arg2}"

    def execute(self) -> None:
        """Initializes and interacts with the Gmail API."""
        self.logger.info("Executing Gmail model...")

        try:
            # Attempt to initialize Gmail service
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials

            # Load credentials from config
            client_id = self.get_config_value("gmail_credentials.client_id")
            client_secret = self.get_config_value("gmail_credentials.client_secret")
            token = self.get_config_value("gmail_credentials.token")
            refresh_token = self.get_config_value("gmail_credentials.refresh_token")

            if not all([client_id, client_secret, token, refresh_token]):
                raise ValueError("Missing Gmail credentials in config.")

            creds = Credentials(
                token=token,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_uri="https://oauth2.googleapis.com/token",
            )

            service = build("gmail", "v1", credentials=creds)

            # Call the Gmail API
            results = (
                service.users()
                .labels()
                .list(userId="me")
                .execute()
            )
            labels = results.get("labels", [])

            if not labels:
                self.logger.info("No labels found.")
                return

            self.logger.info("Labels:")
            for label in labels:
                self.logger.info(f"- {label['name']}")

            self.logger.info("Gmail model execution completed successfully.")

        except Exception as e:
            self.logger.error(f"Error executing Gmail model: {e}", exc_info=True)
            raise
