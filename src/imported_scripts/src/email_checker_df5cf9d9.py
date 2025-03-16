from __future__ import annotations

import os
import pickle
from datetime import datetime
from typing import NamedTuple

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build


class ContactInfo(NamedTuple):
    """Represents contact information."""

    email: str
    first_name: str | None
    last_name: str | None
    last_contact: datetime | None
    uncontacted: bool


def get_gmail_service() -> Resource:
    """Sets up and returns the Gmail API service.

    Authenticates the user and builds the Gmail service object.
    Credentials are automatically refreshed or obtained if needed.

    Returns:
        A Gmail API service object.

    """
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None

    # Load cached credentials if they exist
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
            creds = flow.run_local_server(port=0)

        # Save credentials for future use
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)


def check_email_correspondence(service: Resource, email: str) -> ContactInfo:
    """Checks Gmail for correspondence with the given email address.

    Searches for emails to or from the specified email address and
    returns contact information, including the last contact date if found.

    Args:
        service: The Gmail API service object.
        email: The email address to check.

    Returns:
        A ContactInfo namedtuple containing the email, last contact date,
        and a flag indicating whether the email is uncontacted.

    """
    try:
        # Search for emails to/from this address
        query = f"from:{email} OR to:{email}"
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=1,  # We just need the most recent one
            )
            .execute()
        )

        # If we found any messages
        if "messages" in results:
            # Get the most recent message details
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=results["messages"][0]["id"],
                    format="metadata",
                    metadataHeaders=["From", "Date"],
                )
                .execute()
            )

            # Extract date from headers
            date_str = next(
                header["value"]
                for header in msg["payload"]["headers"]
                if header["name"] == "Date"
            )
            date = datetime.strptime(
                date_str.split(" (")[0],
                "%a, %d %b %Y %H:%M:%S %z",
            )

            return ContactInfo(
                email=email,
                first_name=None,  # We could parse these from the From field if needed
                last_name=None,
                last_contact=date,
                uncontacted=False,
            )

        return ContactInfo(
            email=email,
            first_name=None,
            last_name=None,
            last_contact=None,
            uncontacted=True,
        )

    except Exception:
        return ContactInfo(
            email=email,
            first_name=None,
            last_name=None,
            last_contact=None,
            uncontacted=True,
        )


def parse_email_file(email_file: str) -> list[str]:
    """Extracts email addresses from the input file.

    Reads the file line by line, strips whitespace, and appends
    each line containing an '@' symbol to a list of emails.

    Args:
        email_file: The path to the file containing email addresses.

    Returns:
        A list of email addresses extracted from the file.

    """
    emails: list[str] = []
    with open(email_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if "@" in line:
                emails.append(line)
    return emails


def main() -> None:
    """Main function to process email addresses and check for correspondence.

    Reads email addresses from a file, checks each email against Gmail,
    and prints the results indicating whether correspondence was found.
    """
    # File path
    email_list_file = "/Users/srvo/Data/emails_for_spiderfoot.txt"

    # Get Gmail service
    service = get_gmail_service()

    # Read email addresses
    emails = parse_email_file(email_list_file)

    # Process each email
    results: list[ContactInfo] = []
    for _i, email in enumerate(emails):
        contact_info = check_email_correspondence(service, email)
        results.append(contact_info)

    # Print results
    for info in results:
        if info.uncontacted:
            pass
        else:
            (info.last_contact.strftime("%Y-%m-%d") if info.last_contact else "Unknown")


if __name__ == "__main__":
    main()
