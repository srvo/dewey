from __future__ import annotations

import base64
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo

from dewey.core.base_script import BaseScript

logger = logging.getLogger(__name__)
MOUNTAIN_TZ = ZoneInfo("America/Denver")


class EmailProcessor(BaseScript):
    """Processes email messages and extracts relevant information."""

    def __init__(self) -> None:
        """Initializes the EmailProcessor."""
        super().__init__(config_section="crm")

    def process_email(self, email_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Processes a single email message.

        Args:
        ----
            email_data: A dictionary containing the email message data.

        Returns:
        -------
            A dictionary containing the processed email information, or None if an error occurred.

        """
        try:
            # Extract headers
            headers = {
                header["name"].lower(): header["value"]
                for header in email_data["payload"]["headers"]
            }

            # Parse email addresses
            from_addresses = self._parse_email_addresses(headers.get("from", ""))
            to_addresses = self._parse_email_addresses(headers.get("to", ""))
            cc_addresses = self._parse_email_addresses(headers.get("cc", ""))
            bcc_addresses = self._parse_email_addresses(headers.get("bcc", ""))

            # Extract body
            body = self._get_message_body(email_data["payload"])

            # Extract other metadata
            subject = headers.get("subject", "")
            date_str = headers.get("date", "")
            received_date = self._parse_email_date(date_str)
            size_estimate = email_data.get("sizeEstimate", 0)
            labels = email_data.get("labelIds", [])

            # Construct email data dictionary
            email_info = {
                "gmail_id": email_data["id"],
                "thread_id": email_data.get("threadId", ""),
                "subject": subject,
                "from_addresses": from_addresses,
                "to_addresses": to_addresses,
                "cc_addresses": cc_addresses,
                "bcc_addresses": bcc_addresses,
                "received_date": received_date,
                "size_estimate": size_estimate,
                "labels": labels,
                "body_text": body.get("text", ""),
                "body_html": body.get("html", ""),
            }
            return email_info
        except Exception as e:
            self.logger.error(f"Error processing email: {e}")
            return None

    def _parse_email_addresses(self, header_value: str) -> list[dict[str, str]]:
        """
        Parses email addresses from header value into structured format.

        Args:
        ----
            header_value: The header value containing email addresses.

        Returns:
        -------
            A list of dictionaries, where each dictionary contains the name and email address.

        """
        if not header_value:
            return []

        addresses = []
        for addr in header_value.split(","):
            addr = addr.strip()
            if "<" in addr and ">" in addr:
                name = addr.split("<")[0].strip(" \"'")
                email_addr = addr.split("<")[1].split(">")[0].strip()
                addresses.append({"name": name, "email": email_addr})
            else:
                addresses.append({"name": "", "email": addr})
        return addresses

    def _get_message_body(self, payload: dict[str, Any]) -> dict[str, str]:
        """
        Extract and decode message body from Gmail API payload.

        Args:
        ----
            payload: The Gmail API payload.

        Returns:
        -------
            A dictionary containing the plain text and HTML body of the message.

        """
        body = {"text": "", "html": ""}

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    body["text"] = self._decode_body(part["body"])
                elif part["mimeType"] == "text/html":
                    body["html"] = self._decode_body(part["body"])
                elif "parts" in part:
                    nested_body = self._get_message_body(part)
                    if not body["text"]:
                        body["text"] = nested_body["text"]
                    if not body["html"]:
                        body["html"] = nested_body["html"]
        elif payload["mimeType"] == "text/plain":
            body["text"] = self._decode_body(payload["body"])
        elif payload["mimeType"] == "text/html":
            body["html"] = self._decode_body(payload["body"])

        return body

    def _decode_body(self, body: dict[str, Any]) -> str:
        """
        Decode base64-encoded email body content.

        Args:
        ----
            body: The body dictionary.

        Returns:
        -------
            The decoded body content.

        """
        if "data" in body:
            return base64.urlsafe_b64decode(body["data"].encode("ASCII")).decode(
                "utf-8",
            )
        return ""

    def _parse_email_date(self, date_str: str) -> datetime:
        """
        Parse email date strings into timezone-aware datetime objects.

        Args:
        ----
            date_str: The date string from the email header.

        Returns:
        -------
            A timezone-aware datetime object.

        """
        try:
            if date_str:
                return parsedate_to_datetime(date_str)
            return datetime.now(tz=MOUNTAIN_TZ)
        except Exception as e:
            self.logger.error(f"Failed to parse date: {e}")
            return datetime.now(tz=MOUNTAIN_TZ)

    def run(self) -> None:
        """Placeholder for the run method required by BaseScript."""
        self.logger.info("EmailProcessor.run() called, but has no implementation.")
