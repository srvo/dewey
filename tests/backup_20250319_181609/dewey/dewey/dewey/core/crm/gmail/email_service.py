from dewey.core.base_script import BaseScript
import logging
import signal
import time
from datetime import datetime, timedelta
from typing import Optional

# Directly using the root logger is now discouraged.  Use self.logger instead.
# logger = logging.getLogger(__name__)


class EmailService(BaseScript):
    """Manages the email fetching and processing service."""

    def __init__(self, gmail_client, email_processor, fetch_interval: float = 900, check_interval: float = 1.0):
        """
        Initializes the EmailService with dependencies and configuration.

        Args:
            gmail_client: An instance of the GmailClient class.
            email_processor: An instance of the EmailProcessor class.
            fetch_interval: The interval in seconds between email fetches.
            check_interval: The interval in seconds between checks for new emails.
        """
        super().__init__(config_section='crm')
        self.gmail_client = gmail_client
        self.email_processor = email_processor
        self.fetch_interval = float(self.config.get('fetch_interval', fetch_interval))  # Use self.config
        self.check_interval = float(self.config.get('check_interval', check_interval))  # Use self.config
        self.running = False
        self.last_run: Optional[datetime] = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Sets up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signum, frame):
        """Handles shutdown signals gracefully."""
        self.logger.warning(f"Received signal {signum}. Shutting down...")  # Use self.logger
        self.running = False

    def fetch_cycle(self):
        """Executes a single email fetch and process cycle."""
        try:
            self.logger.info("Starting email fetch cycle")  # Use self.logger
            # Fetch emails
            results = self.gmail_client.fetch_emails()
            if results and results['messages']:
                for message in results['messages']:
                    email_data = self.gmail_client.get_message(message['id'])
                    if email_data:
                        processed_email = self.email_processor.process_email(email_data)
                        if processed_email:
                            self.logger.info(f"Successfully processed email {message['id']}")  # Use self.logger
                        else:
                            self.logger.warning(f"Failed to fully process email {message['id']}")  # Use self.logger
                    else:
                        self.logger.warning(f"Could not retrieve email {message['id']}")  # Use self.logger
            else:
                self.logger.info("No emails to fetch")  # Use self.logger
            self.last_run = datetime.now()
            self.logger.info("Email fetch cycle completed")  # Use self.logger
        except Exception as e:
            self.logger.error(f"Error during fetch cycle: {e}", exc_info=True)  # Use self.logger

    def run(self):
        """Runs the email service in a continuous loop."""
        self.running = True
        self.logger.info("Email service started")  # Use self.logger

        try:
            while self.running:
                current_time = datetime.now()
                if self.last_run is None or (current_time - self.last_run) >= timedelta(seconds=self.fetch_interval):
                    self.fetch_cycle()
                time.sleep(self.check_interval)
        except Exception as e:
            self.logger.error(f"Fatal error in email service: {e}", exc_info=True)  # Use self.logger
        finally:
            self.logger.info("Email service shutting down")  # Use self.logger