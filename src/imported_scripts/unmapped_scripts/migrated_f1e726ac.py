"""Email processing management commands."""

import re


def extract_email_addresses(text: str) -> list[str]:
    """Extract email addresses from a given text.

    Args:
        text: The input text to search for email addresses.

    Returns:
        A list of email addresses found in the text.

    """
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return re.findall(email_regex, text)


def validate_email_address(email: str) -> bool:
    """Validate a single email address.

    Args:
        email: The email address to validate.

    Returns:
        True if the email address is valid, False otherwise.

    """
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return bool(re.match(email_regex, email))


def extract_and_validate_emails(text: str) -> tuple[list[str], list[str]]:
    """Extract and validate email addresses from a given text.

    Args:
        text: The input text to search for email addresses.

    Returns:
        A tuple containing two lists:
            - A list of valid email addresses.
            - A list of invalid email addresses.

    """
    extracted_emails = extract_email_addresses(text)
    valid_emails = [
        email for email in extracted_emails if validate_email_address(email)
    ]
    invalid_emails = [
        email for email in extracted_emails if not validate_email_address(email)
    ]
    return valid_emails, invalid_emails
