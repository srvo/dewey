from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from email_processing.imap_sync import IMAPSync
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize emails from IMAP server while maintaining immutable records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder", default="INBOX", help="IMAP folder to sync (default: INBOX)"
        )
        parser.add_argument("--username", help="IMAP username (if not in settings)")
        parser.add_argument("--password", help="IMAP password (if not in settings)")

    def handle(self, *args, **options):
        start_time = timezone.now()
        logger.info("Starting email sync at %s", start_time)

        try:
            # Get credentials from settings or command line
            username = options["username"] or settings.IMAP_USERNAME
            password = options["password"] or settings.IMAP_PASSWORD
            folder = options["folder"]

            # Initialize and run sync
            sync = IMAPSync()
            sync.initialize(username, password)

            try:
                sync.sync_folder(folder)
                logger.info("Successfully synced folder %s", folder)
            finally:
                sync.close()

            end_time = timezone.now()
            duration = end_time - start_time
            logger.info("Completed email sync in %s seconds", duration.total_seconds())

        except Exception as e:
            logger.error("Email sync failed: %s", str(e))
            raise
