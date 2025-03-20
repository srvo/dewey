import logging
import signal
import time
from datetime import datetime, timedelta
from typing import Optional

from dewey.core.base_script import BaseScript


class EmailService(BaseScript):
    """Manages the email fetching and processing service.

    Inherits from BaseScript for standardized configuration, logging,
    and lifecycle management.
    """

    def __init__(self, gmail_client, email_processor, config_section: str = 'crm'):
        """Initializes the EmailService with dependencies and configuration.

        Args:
            gmail_client: An instance of the GmailClient class.
            email_processor: An instance of the EmailProcessor class.
            config_section: The configuration section to use for this service.
        """
        super().__init__(config_section=config_section)
        self.gmail_client = gmail_client
        self.email_processor = email_processor
        self.fetch_interval: float = float(self.get_config_value('fetch_interval', 900))
        self.check_interval: float = float(self.get_config_value('check_interval', 1.0))
        self.running: bool = False
        self.last_run: Optional[datetime] = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Sets up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signum: int, frame) -> None:
        """Handles shutdown signals gracefully.

        Args:
            signum: The signal number.
            frame: The frame object.
        """
        self.logger.warning(f"Received signal {signum}. Shutting down...")
        self.running = False

    def fetch_cycle(self) -> None:
        """Executes a single email fetch and process cycle."""
        try:
            self.logger.info("Starting email fetch cycle")
            # Fetch emails
            results = self.gmail_client.fetch_emails()
            if results and results['messages']:
                for message in results['messages']:
                    email_data = self.gmail_client.get_message(message['id'])
                    if email_data:
                        processed_email = self.email_processor.process_email(email_data)
                        if processed_email:
                            self.logger.info(f"Successfully processed email {message['id']}")
                        else:
                            self.logger.warning(f"Failed to fully process email {message['id']}")
                    else:
                        self.logger.warning(f"Could not retrieve email {message['id']}")
            else:
                self.logger.info("No emails to fetch")
            self.last_run = datetime.now()
            self.logger.info("Email fetch cycle completed")
        except Exception as e:
            self.logger.error(f"Error during fetch cycle: {e}", exc_info=True)

    def run(self) -> None:
        """Runs the email service in a continuous loop."""
        self.running = True
        self.logger.info("Email service started")

        try:
            while self.running:
                current_time = datetime.now()
                if self.last_run is None or (current_time - self.last_run) >= timedelta(seconds=self.fetch_interval):
                    self.fetch_cycle()
                time.sleep(self.check_interval)
        except Exception as e:
            self.logger.error(f"Fatal error in email service: {e}", exc_info=True)
        finally:
            self.logger.info("Email service shutting down")
