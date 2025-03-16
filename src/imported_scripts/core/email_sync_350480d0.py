import email
import logging
from email.utils import parsedate_to_datetime

from django.utils import timezone
from imapclient import IMAPClient

from .models import Email, RawEmail

logger = logging.getLogger(__name__)


class IMAPSync:
    """Handles email synchronization using IMAP protocol."""

    def __init__(self, host="imap.gmail.com", port=993) -> None:
        self.host = host
        self.port = port
        self.client = None

    def initialize(self, username, password):
        """Initialize IMAP connection with credentials."""
        try:
            self.client = IMAPClient(self.host, port=self.port, use_uid=True)
            self.client.login(username, password)
            return self
        except Exception as e:
            logger.exception("IMAP connection failed: %s", str(e))
            raise

    def sync_folder(self, folder="INBOX") -> None:
        """Sync emails from a specific IMAP folder."""
        try:
            self.client.select_folder(folder)
            messages = self.client.search(["ALL"])

            for msg_id in messages:
                try:
                    # Fetch message data
                    msg_data = self.client.fetch(
                        [msg_id],
                        ["RFC822", "FLAGS", "INTERNALDATE"],
                    )
                    if not msg_data:
                        continue

                    raw_email = msg_data[msg_id][b"RFC822"]
                    flags = msg_data[msg_id][b"FLAGS"]
                    msg_data[msg_id][b"INTERNALDATE"]

                    # Parse email
                    email_message = email.message_from_bytes(raw_email)

                    # Get or create Email record
                    try:
                        email_obj = Email.objects.get(
                            message_id=email_message["Message-ID"],
                        )
                        logger.info(
                            "Updating existing email: %s",
                            email_message["Message-ID"],
                        )
                    except Email.DoesNotExist:
                        logger.info(
                            "Creating new email: %s",
                            email_message["Message-ID"],
                        )
                        email_obj = Email(message_id=email_message["Message-ID"])

                    # Update email fields
                    email_obj.subject = email_message["Subject"] or ""
                    email_obj.from_email = email.utils.parseaddr(email_message["From"])[
                        1
                    ]
                    email_obj.from_name = email.utils.parseaddr(email_message["From"])[
                        0
                    ]
                    email_obj.to_emails = [
                        addr[1]
                        for addr in email.utils.getaddresses(
                            email_message.get_all("To", []),
                        )
                    ]
                    received_at = parsedate_to_datetime(email_message["Date"])
                    if received_at.tzinfo is None:
                        received_at = timezone.make_aware(received_at)
                    email_obj.received_at = received_at
                    email_obj.is_read = b"\\Seen" in flags
                    email_obj.last_sync_at = timezone.now()

                    # Get email body
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                email_obj.body_text = part.get_payload(
                                    decode=True,
                                ).decode()
                            elif part.get_content_type() == "text/html":
                                email_obj.body_html = part.get_payload(
                                    decode=True,
                                ).decode()
                    else:
                        email_obj.body_text = email_message.get_payload(
                            decode=True,
                        ).decode()

                    email_obj.save()

                    # Store raw email
                    RawEmail.objects.update_or_create(
                        email=email_obj,
                        defaults={"raw_data": raw_email},
                    )

                except Exception as e:
                    logger.exception("Failed to process email %s: %s", msg_id, str(e))
                    continue

        except Exception as e:
            logger.exception("Failed to sync folder %s: %s", folder, str(e))
            raise
        finally:
            self.client.unselect_folder()

    def close(self) -> None:
        """Close IMAP connection."""
        if self.client:
            self.client.logout()
