from datetime import datetime

from dateutil.parser import parse as parse_datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from integrations.models import (
    GmailMessage,
    GoogleCalendarEvent,
    GoogleContact,
    GoogleDocument,
)


class Command(BaseCommand):
    help = "Synchronize data with Google services"

    def handle(self, *args, **options) -> None:
        self.stdout.write("Starting Google services sync...")
        self.sync_calendar()
        self.sync_contacts()
        self.sync_drive()
        self.sync_gmail()
        self.stdout.write(self.style.SUCCESS("Sync completed successfully"))

    def sync_calendar(self) -> None:
        service = build("calendar", "v3", credentials=self.get_credentials())
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

    def sync_contacts(self) -> None:
        service = build("people", "v1", credentials=self.get_credentials())
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

    def sync_drive(self) -> None:
        service = build("drive", "v3", credentials=self.get_credentials())
        results = (
            service.files()
            .list(pageSize=100, fields="files(id, name, mimeType)")
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

    def sync_gmail(self) -> None:
        service = build("gmail", "v1", credentials=self.get_credentials())
        results = service.users().messages().list(userId="me", maxResults=100).execute()

        for message in results.get("messages", []):
            msg = (
                service.users().messages().get(userId="me", id=message["id"]).execute()
            )
            GmailMessage.objects.update_or_create(
                google_id=message["id"],
                defaults={
                    "subject": next(
                        (
                            h["value"]
                            for h in msg["payload"]["headers"]
                            if h["name"].lower() == "subject"
                        ),
                        "",
                    ),
                    "sender": next(
                        (
                            h["value"]
                            for h in msg["payload"]["headers"]
                            if h["name"].lower() == "from"
                        ),
                        "",
                    ),
                    "recipient": next(
                        (
                            h["value"]
                            for h in msg["payload"]["headers"]
                            if h["name"].lower() == "to"
                        ),
                        "",
                    ),
                },
            )

    def get_credentials(self):
        # Implement your credentials logic here
        # This should use your OAuth2 setup from settings
        return Credentials.from_authorized_user_info(settings.GOOGLE_OAUTH_CREDENTIALS)
