from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.utils.dateparse import parse_datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import (
    GmailMessage,
    GoogleCalendarEvent,
    GoogleContact,
    GoogleDocument,
)


def get_credentials():
    """Get valid credentials for Google API access."""
    return Credentials.from_authorized_user_info(settings.GOOGLE_OAUTH_CREDENTIALS)


def get_header(message, header_name):
    """Extract header value from Gmail message."""
    headers = message.get("payload", {}).get("headers", [])
    return next(
        (h["value"] for h in headers if h["name"].lower() == header_name.lower()),
        "",
    )


@shared_task
def sync_google_services() -> None:
    """Synchronize all Google services."""
    sync_calendar()
    sync_contacts()
    sync_drive()
    sync_gmail()


@shared_task
def sync_calendar() -> None:
    """Sync Google Calendar events."""
    service = build("calendar", "v3", credentials=get_credentials())
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=datetime.utcnow().isoformat() + "Z",
            maxResults=100,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    for event in events_result.get("items", []):
        GoogleCalendarEvent.objects.update_or_create(
            google_id=event["id"],
            defaults={
                "summary": event.get("summary", ""),
                "start_time": parse_datetime(
                    event["start"].get("dateTime", event["start"].get("date")),
                ),
                "end_time": parse_datetime(
                    event["end"].get("dateTime", event["end"].get("date")),
                ),
            },
        )


@shared_task
def sync_contacts() -> None:
    """Sync Google Contacts."""
    service = build("people", "v1", credentials=get_credentials())
    results = (
        service.people()
        .connections()
        .list(
            resourceName="people/me",
            pageSize=100,
            personFields="names,emailAddresses,phoneNumbers",
        )
        .execute()
    )

    for person in results.get("connections", []):
        GoogleContact.objects.update_or_create(
            google_id=person["resourceName"],
            defaults={
                "name": person.get("names", [{}])[0].get("displayName", ""),
                "email": person.get("emailAddresses", [{}])[0].get("value", ""),
            },
        )


@shared_task
def sync_drive() -> None:
    """Sync Google Drive documents."""
    service = build("drive", "v3", credentials=get_credentials())
    results = (
        service.files()
        .list(
            pageSize=100,
            fields="files(id, name, mimeType, createdTime, modifiedTime)",
        )
        .execute()
    )

    for file in results.get("files", []):
        GoogleDocument.objects.update_or_create(
            google_id=file["id"],
            defaults={
                "title": file["name"],
                "mime_type": file["mimeType"],
            },
        )


@shared_task
def sync_gmail() -> None:
    """Sync Gmail messages."""
    service = build("gmail", "v1", credentials=get_credentials())
    results = service.users().messages().list(userId="me", maxResults=100).execute()

    for message in results.get("messages", []):
        msg_detail = (
            service.users().messages().get(userId="me", id=message["id"]).execute()
        )

        GmailMessage.objects.update_or_create(
            google_id=message["id"],
            defaults={
                "subject": get_header(msg_detail, "subject"),
                "sender": get_header(msg_detail, "from"),
                "recipient": get_header(msg_detail, "to"),
            },
        )
