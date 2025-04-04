"""Test Gmail API access and message retrieval."""

import logging

from .gmail_utils import GmailAPIClient

logger = logging.getLogger(__name__)


def test_gmail_api():
    """Test Gmail API connectivity and message retrieval."""
    gmail_client = GmailAPIClient()

    try:
        service = gmail_client.service
        results = service.users().messages().list(userId="me", maxResults=10).execute()
        messages = results.get("messages", [])

        if not messages:
            logger.info("No messages found.")
            return False

        logger.info(f"Found {len(messages)} messages")

        # Test message retrieval
        msg_id = messages[0]["id"]
        logger.info(f"Fetching content for message {msg_id}")
        full_message = gmail_client.fetch_message(msg_id)

        if full_message:
            headers = {
                header["name"]: header["value"]
                for header in full_message.get("payload", {}).get("headers", [])
            }

            logger.info(f"Subject: {headers.get('Subject', 'No subject')}")
            logger.info(f"From: {headers.get('From', 'Unknown')}")

            plain_text, html = gmail_client.extract_body(full_message)
            if plain_text or html:
                logger.info("Successfully retrieved message content")
                return True

        logger.error("Failed to retrieve message content")
        return False

    except Exception as e:
        logger.error(f"Error testing Gmail API: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = test_gmail_api()
    print("Gmail API test:", "PASSED" if success else "FAILED")
