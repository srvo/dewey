"""
Feedback Models

Classes for feedback management in the TUI.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FeedbackItem:
    """A class representing a feedback item from a contact."""

    uid: str
    sender: str
    subject: str
    content: str
    date: datetime
    starred: bool = False
    is_client: bool = False
    annotation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def contact_email(self) -> str:
        """Get the contact email (alias for sender)."""
        return self.sender

    @property
    def contact_name(self) -> str:
        """Extract a name from the sender's email address."""
        if "@" in self.sender:
            return self.sender.split("@")[0].replace(".", " ").title()
        return self.sender.title()

    @property
    def timestamp(self) -> datetime:
        """Alias for date to maintain compatibility."""
        return self.date

    @property
    def feedback_id(self) -> str:
        """Alias for uid to maintain compatibility."""
        return self.uid

    @property
    def needs_follow_up(self) -> bool:
        """Alias for starred to maintain compatibility."""
        return self.starred

    @property
    def done(self) -> bool:
        """Whether the feedback item is done (always False for now)."""
        return False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackItem":
        """Create a FeedbackItem from a dictionary."""
        # Convert old format to new format if needed
        if "feedback_id" in data and "uid" not in data:
            data["uid"] = data.pop("feedback_id")
        if "contact_email" in data and "sender" not in data:
            data["sender"] = data.pop("contact_email")
        if "timestamp" in data and "date" not in data:
            data["date"] = data.pop("timestamp")
        if "needs_follow_up" in data and "starred" not in data:
            data["starred"] = data.pop("needs_follow_up")

        # Handle string dates
        if "date" in data and isinstance(data["date"], str):
            try:
                data["date"] = datetime.fromisoformat(data["date"])
            except ValueError:
                data["date"] = datetime.now()

        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert FeedbackItem to a dictionary."""
        return {
            "uid": self.uid,
            "sender": self.sender,
            "subject": self.subject,
            "content": self.content,
            "date": self.date.isoformat()
            if isinstance(self.date, datetime)
            else self.date,
            "starred": self.starred,
            "is_client": self.is_client,
            "annotation": self.annotation,
            "metadata": self.metadata,
        }


class SenderProfile:
    """A class representing a unique sender with their history."""

    def __init__(
        self,
        email: str,
        name: str = "",
        message_count: int = 0,
        last_contact: datetime | None = None,
        first_contact: datetime | None = None,
        pattern: str = "",
        annotation: str = "",
        is_client: bool = False,
    ):
        """Initialize a SenderProfile."""
        self.email = email
        self.name = name or email.split("@")[0]
        self.message_count = message_count
        self.last_contact = last_contact
        self.first_contact = first_contact
        self.pattern = pattern
        self.annotation = annotation
        self.recent_emails: list[dict[str, Any]] = []
        self.needs_follow_up = False
        self.tags: list[str] = []
        self.domain = email.split("@")[-1] if "@" in email else ""
        self.is_client = is_client

    def add_email(self, email_data: dict[str, Any]) -> None:
        """Add an email message to this sender's history."""
        # Add to recent emails list, keeping newest at the beginning
        self.recent_emails.append(email_data)
        self.recent_emails.sort(
            key=lambda x: x.get("timestamp", datetime.now()), reverse=True,
        )

        # Keep only the 10 most recent emails
        if len(self.recent_emails) > 10:
            self.recent_emails = self.recent_emails[:10]

        # Update message count
        self.message_count = len(self.recent_emails)

        # Update last contact time
        timestamp = email_data.get("timestamp")
        if timestamp:
            if not self.last_contact or timestamp > self.last_contact:
                self.last_contact = timestamp

            if not self.first_contact or timestamp < self.first_contact:
                self.first_contact = timestamp

        # Check if this message needs follow-up
        if email_data.get("needs_follow_up", False):
            self.needs_follow_up = True

        # Extract tags from email (example logic)
        subject = email_data.get("subject", "").lower()
        if "urgent" in subject:
            self.add_tag("urgent")
        if "question" in subject:
            self.add_tag("question")
        if "bug" in subject:
            self.add_tag("bug")
        if "feature" in subject:
            self.add_tag("feature request")

    def add_tag(self, tag: str) -> None:
        """Add a tag to this sender if it doesn't already exist."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this sender if it exists."""
        if tag in self.tags:
            self.tags.remove(tag)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SenderProfile":
        """
        Create a SenderProfile from a dictionary.

        Args:
        ----
            data: Dictionary containing sender data

        Returns:
        -------
            A SenderProfile instance

        """
        last_contact = None
        if "last_contact" in data:
            if isinstance(data["last_contact"], str):
                try:
                    last_contact = datetime.fromisoformat(data["last_contact"])
                except ValueError:
                    last_contact = datetime.now()
            elif isinstance(data["last_contact"], datetime):
                last_contact = data["last_contact"]

        first_contact = None
        if "first_contact" in data:
            if isinstance(data["first_contact"], str):
                try:
                    first_contact = datetime.fromisoformat(data["first_contact"])
                except ValueError:
                    first_contact = None
            elif isinstance(data["first_contact"], datetime):
                first_contact = data["first_contact"]

        return cls(
            email=data.get("email", "unknown@example.com"),
            name=data.get("name", "Unknown Sender"),
            message_count=data.get("message_count", 0),
            last_contact=last_contact,
            domain=data.get("domain"),
            first_contact=first_contact,
            tags=data.get("tags", []),
            needs_follow_up=data.get("needs_follow_up", False),
            annotation=data.get("annotation", ""),
            pattern=data.get("pattern", ""),
            is_client=data.get("is_client", False),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the sender profile to a dictionary.

        Returns
        -------
            Dictionary representation of the sender profile

        """
        return {
            "email": self.email,
            "name": self.name,
            "message_count": self.message_count,
            "last_contact": self.last_contact.isoformat()
            if self.last_contact
            else None,
            "first_contact": self.first_contact.isoformat()
            if self.first_contact
            else None,
            "domain": self.domain,
            "tags": self.tags,
            "needs_follow_up": self.needs_follow_up,
            "annotation": self.annotation,
            "pattern": self.pattern,
            "is_client": self.is_client,
        }
