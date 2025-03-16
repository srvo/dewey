#!/usr/bin/env python3

import contextlib
import datetime
import logging
import os
import pickle

import pytz
from dateutil import parser
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from jinja2 import Environment, FileSystemLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.pickle"
NOTES_DIR = os.path.expanduser("~/configs/docs/current/notes")


def get_credentials():
    """Get valid user credentials from storage or user authentication."""
    creds = None

    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                msg = (
                    f"Missing {CREDENTIALS_FILE}. Please download it from Google Cloud Console "
                    "and save it in the current directory."
                )
                raise FileNotFoundError(
                    msg,
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return creds


def is_all_day_event(event):
    """Check if an event is an all-day event."""
    start = event["start"].get("date")
    return bool(start)


def clean_html(text):
    """Clean HTML from text and format links."""
    if not text:
        return ""

    # Replace <br/> and <br> with newlines
    text = text.replace("<br/>", "\n").replace("<br>", "\n")

    # Replace <p> and </p> with newlines
    text = text.replace("<p>", "").replace("</p>", "\n")

    # Extract links in markdown format: [text](url)
    while '<a href="' in text:
        start = text.find('<a href="')
        href_start = start + 9
        href_end = text.find('"', href_start)
        link_end = text.find("</a>", href_end)
        if -1 in [start, href_end, link_end]:
            break
        url = text[href_start:href_end]
        link_text = text[text.find(">", href_end) + 1 : link_end]
        text = text[:start] + f"[{link_text}]({url})" + text[link_end + 4 :]

    # Remove multiple newlines
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def clean_text(text):
    """Clean and format text content."""
    if not text:
        return ""

    # Lines to remove
    remove_patterns = [
        "Event Name:",
        "Powered by",
        "Need to make changes to this event?",
        "Cancel:",
        "Reschedule:",
    ]

    # Clean the text
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Skip lines with remove patterns
        if any(pattern in line for pattern in remove_patterns):
            continue

        lines.append(line)

    return "\n".join(lines)


def clean_location(text):
    """Clean and format location text."""
    if not text:
        return ""

    # If it's a URL, return just the URL
    if text.startswith(("http://", "https://")):
        return text.split()[0]  # Take just the URL part

    # If it contains "Join the meeting", extract just the URL and phone
    if "Join the meeting" in text:
        parts = text.split()
        url = next((p for p in parts if p.startswith("http")), "")
        phone = next((p for p in parts if p.replace("-", "").isdigit()), "")
        if phone:
            return f"{url}\nDial-in: {phone}"
        return url

    return text


def normalize_summary(summary):
    """Normalize event summary for better duplicate detection."""
    # Convert to lowercase for comparison
    summary = summary.lower()

    # Remove common suffixes after " - "
    summary = summary.split(" - ")[0]

    # Remove common words that don't change the event meaning
    remove_words = ["joins the call", "w/", "with"]
    for word in remove_words:
        summary = summary.replace(word, "")

    return summary.strip()


def get_calendar_events(service, date):
    """Get calendar events for a specific date."""
    # Convert to datetime objects for the full day
    start_time = datetime.datetime.combine(date, datetime.time.min)
    end_time = datetime.datetime.combine(date, datetime.time.max)

    # Get timezone from system
    timezone = pytz.timezone("America/New_York")
    start_time = timezone.localize(start_time)
    end_time = timezone.localize(end_time)

    # Convert to RFC3339 format
    start_time_str = start_time.isoformat()
    end_time_str = end_time.isoformat()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_time_str,
            timeMax=end_time_str,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])

    # Track seen event summaries to avoid duplicates
    seen_events = {}  # normalized_summary -> event
    formatted_events = []

    for event in events:
        # Skip all-day events and events with "Home" in the title
        if is_all_day_event(event) or event.get("summary", "").strip() == "Home":
            continue

        summary = event.get("summary", "No Title").strip()
        normalized_summary = normalize_summary(summary)

        # If we've seen this normalized summary before, skip this event
        if normalized_summary in seen_events:
            # If this event is longer, use this one instead
            prev_event = seen_events[normalized_summary]
            prev_duration = (
                parser.parse(prev_event["end"]["dateTime"])
                - parser.parse(prev_event["start"]["dateTime"])
            ).total_seconds()
            curr_duration = (
                parser.parse(event["end"]["dateTime"])
                - parser.parse(event["start"]["dateTime"])
            ).total_seconds()
            if curr_duration <= prev_duration:
                continue

        seen_events[normalized_summary] = event

        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))

        # Parse the times
        start_dt = parser.parse(start)
        end_dt = parser.parse(end)

        # Clean up description and location
        description = clean_html(event.get("description", ""))
        description = clean_text(description)
        location = clean_location(clean_html(event.get("location", "")))

        formatted_events.append(
            {
                "summary": summary,
                "start_time": start_dt.strftime("%I:%M %p").lstrip("0"),
                "end_time": end_dt.strftime("%I:%M %p").lstrip("0"),
                "description": description,
                "location": location,
                "is_all_day": is_all_day_event(event),
            },
        )

    return formatted_events


def generate_note(date, events):
    """Generate a note file for a specific date."""
    # Create template environment
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("daily_note.md.j2")

    # Format dates for the note
    date_str = date.strftime("%Y%m%d")
    date_str_long = date.strftime("%B %d, %Y")

    # Render the template
    content = template.render(
        date_str=date_str,
        date_str_long=date_str_long,
        events=events,
    )

    # Ensure the notes directory exists
    os.makedirs(NOTES_DIR, exist_ok=True)

    # Write the note file
    note_path = os.path.join(NOTES_DIR, f"{date_str} notes.md")
    with open(note_path, "w") as f:
        f.write(content)

    return note_path


def generate_note_for_date(date=None):
    """Generate a note for a specific date or today."""
    try:
        if date is None:
            date = datetime.date.today()

        # Get Google Calendar credentials
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)

        # Get calendar events
        events = get_calendar_events(service, date)

        # Generate the note file
        note_path = generate_note(date, events)
        logging.info(f"Generated daily note: {note_path}")

        return note_path

    except Exception as e:
        logging.exception(f"Error generating note: {e!s}")
        raise


def main() -> None:
    """Main function to generate daily notes."""
    with contextlib.suppress(Exception):
        generate_note_for_date()


if __name__ == "__main__":
    main()
