"""Initialize the email_processing tests module."""

from __future__ import annotations

import re


def extract_emails(text: str) -> list[str]:
    """Extract all valid email addresses from a given text.

    Args:
    ----
        text: The input string to search for email addresses.

    Returns:
    -------
        A list of strings, where each string is a valid email address found in the text.
        Returns an empty list if no email addresses are found.

    """
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return re.findall(email_pattern, text)


def validate_email(email: str) -> bool:
    """Validate the format of a single email address.

    Args:
    ----
        email: The email address to validate.

    Returns:
    -------
        True if the email address is valid, False otherwise.

    """
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return bool(re.match(email_pattern, email))


def find_email_domain(email: str) -> str | None:
    """Extract the domain from a given email address.

    Args:
    ----
        email: The email address to extract the domain from.

    Returns:
    -------
        The domain part of the email address as a string, or None if the email is invalid.

    """
    if not validate_email(email):
        return None
    return email.split("@")[1]


def parse_email_header(header: str) -> tuple[str | None, str | None]:
    """Parse an email header to extract the sender and subject.

    Args:
    ----
        header: The email header string.

    Returns:
    -------
        A tuple containing the sender and subject. Either value can be None if not found.

    """
    sender_pattern = r"From: (.*?)\n"
    subject_pattern = r"Subject: (.*?)\n"

    sender_match = re.search(sender_pattern, header)
    subject_match = re.search(subject_pattern, header)

    sender = sender_match.group(1).strip() if sender_match else None
    subject = subject_match.group(1).strip() if subject_match else None

    return sender, subject
