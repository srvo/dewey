"""Management commands for email processing."""

import re


def extract_emails_from_text(text: str) -> list[str]:
    """Extracts email addresses from a given text.

    Args:
        text: The input text to search for email addresses.

    Returns:
        A list of email addresses found in the text.

    """
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return re.findall(email_regex, text)


def validate_email_format(email: str) -> bool:
    """Validates the format of a single email address.

    Args:
        email: The email address to validate.

    Returns:
        True if the email format is valid, False otherwise.

    """
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return bool(re.match(email_regex, email))


def extract_emails_with_validation(text: str) -> list[str]:
    """Extracts and validates email addresses from a given text.

    Args:
        text: The input text to search for email addresses.

    Returns:
        A list of valid email addresses found in the text.

    """
    emails = extract_emails_from_text(text)
    return [email for email in emails if validate_email_format(email)]


def extract_name_and_email(text: str) -> list[tuple[str, str]]:
    """Extracts name and email pairs from a string.

    Assumes the format "Name <email>".

    Args:
        text: The input string.

    Returns:
        A list of tuples, where each tuple contains a name and an email address.
        Returns an empty list if no matches are found.

    """
    name_email_regex = r"([^<]+) <([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>"
    return re.findall(name_email_regex, text)
