import logging
import signal
import time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class EmailService:
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
        self.gmail_client = gmail_client
        self.email_processor = email_processor
        self.fetch_interval = fetch_interval
        self.check_interval = check_interval
        self.running = False
        self.last_run: Optional[datetime] = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Sets up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signum, frame):
        """Handles shutdown signals gracefully."""
        logger.warning(f"Received signal {signum}. Shutting down...")
        self.running = False

    def fetch_cycle(self):
        """Executes a single email fetch and process cycle."""
        try:
            logger.info("Starting email fetch cycle")
            # Fetch emails
            results = self.gmail_client.fetch_emails()
            if results and results['messages']:
                for message in results['messages']:
                    email_data = self.gmail_client.get_message(message['id'])
                    if email_data:
                        processed_email = self.email_processor.process_email(email_data)
                        if processed_email:
                            logger.info(f"Successfully processed email {message['id']}")
                        else:
                            logger.warning(f"Failed to fully process email {message['id']}")
                    else:
                        logger.warning(f"Could not retrieve email {message['id']}")
            else:
                logger.info("No emails to fetch")
            self.last_run = datetime.now()
            logger.info("Email fetch cycle completed")
        except Exception as e:
            logger.error(f"Error during fetch cycle: {e}", exc_info=True)

    def run(self):
        """Runs the email service in a continuous loop."""
        self.running = True
        logger.info("Email service started")

        try:
            while self.running:
                current_time = datetime.now()
                if self.last_run is None or (current_time - self.last_run) >= timedelta(seconds=self.fetch_interval):
                    self.fetch_cycle()
                time.sleep(self.check_interval)
        except Exception as e:
            logger.error(f"Fatal error in email service: {e}", exc_info=True)
        finally:
            logger.info("Email service shutting down")
