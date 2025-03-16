# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""SQLAlchemy models for the email processing system.

This module defines all database models using SQLAlchemy's declarative base.
The models are organized into several categories:
- Contact management (Contacts, ContactHistory, ContactEmail, ContactMetadata)
- Email processing (RawEmail, EmailProcessingHistory)
- Event management (Event, EventParticipant, EventNote, EventTranscript)
- Content generation (ContentOpportunity, DiscussionTopic, ActionItem)

Each model includes:
- Standard fields: id, version, timestamps, audit fields
- Relationships to other models
- Indexes for common query patterns
- JSONB fields for flexible data storage

The models are designed to support:
- Versioning and audit trails
- Flexible schema evolution
- Efficient query patterns
- Data validation and constraints
- Relationship management
- Soft delete functionality
- Temporal data tracking
"""

import uuid

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

# Declarative base class for all models
Base = declarative_base()


def generate_uuid() -> uuid.UUID:
    """Generate a UUID for primary keys.

    Returns
    -------
        uuid.UUID: A new UUID4 value

    Notes
    -----
        - Uses UUID v4 for maximum uniqueness
        - Suitable for distributed systems
        - Provides better performance than sequential IDs for large datasets

    """
    return uuid.uuid4()


class Contact(Base):
    """Core contact information model.

    Represents individuals or organizations that interact with the system.
    Tracks email interactions, enrichment status, and relationship metrics.

    Attributes
    ----------
        id (UUID): Primary key using UUID v4
        version (int): Optimistic locking version for concurrency control
        primary_email (str): Main contact email (required, unique)
        name (str): Contact's full name
        domain (str): Email domain for categorization (indexed)
        avg_priority (float): Calculated priority score based on interactions
        email_count (int): Total emails from this contact
        last_priority_change (datetime): When priority last changed
        enrichment_status (str): Current enrichment state (indexed)
        last_enriched (datetime): Last enrichment timestamp
        enrichment_source (str): Source of enrichment data
        confidence_score (float): Data quality confidence (0.0-1.0)
        extra_data (dict): Additional unstructured data in JSONB format
        created_by (str): User/system that created record
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp (auto-set)
        updated_at (datetime): Last update timestamp (auto-updated)
        deleted_at (datetime): Soft delete timestamp
        deleted_by (str): User/system that deleted

    Relationships:
        emails: Associated email addresses (one-to-many)
        metadata_records: Historical metadata (one-to-many)
        organized_events: Events this contact organized (one-to-many)
        participations: Events this contact participated in (many-to-many)

    Indexes:
        - Primary key on id
        - Index on domain for fast domain-based queries
        - Index on enrichment_status for filtering

    Notes
    -----
        - Uses soft delete pattern with deleted_at/deleted_by
        - Supports versioning for optimistic locking
        - Includes audit fields (created_by, updated_by, etc.)
        - JSONB field for flexible additional data storage

    """

    __tablename__ = "contacts"

    # Primary key using UUID v4 for distributed systems
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    # Version for optimistic locking
    version = Column(Integer, nullable=False, default=1)

    # Core contact information
    primary_email = Column(String, nullable=False)  # Required unique email
    name = Column(String)  # Optional full name
    domain = Column(String, index=True)  # Email domain with index

    # Interaction metrics
    avg_priority = Column(Float)  # Calculated priority score
    email_count = Column(Integer, default=0)  # Total email count

    # Priority tracking
    last_priority_change = Column(TIMESTAMP(timezone=True))  # Last priority update

    # Enrichment tracking
    enrichment_status = Column(String, default="pending", index=True)  # Current state
    last_enriched = Column(TIMESTAMP(timezone=True))  # Last enrichment time
    enrichment_source = Column(String)  # Source of enrichment data
    confidence_score = Column(Float, default=0.0)  # Data quality confidence

    # Flexible data storage
    extra_data = Column(JSONB)  # Additional unstructured data

    # Audit fields
    created_by = Column(String, nullable=False)  # Creator identifier
    updated_by = Column(String, nullable=False)  # Last updater identifier

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )  # Auto-set creation time
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )  # Auto-updated on change
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete timestamp
    deleted_by = Column(String)  # Soft delete actor

    # Relationships
    emails = relationship("ContactEmail", back_populates="contact")  # Associated emails
    metadata_records = relationship(
        "ContactMetadata",
        back_populates="contact",
    )  # Historical metadata
    organized_events = relationship(
        "Event",
        back_populates="organizer",
    )  # Organized events
    participations = relationship(
        "EventParticipant",
        back_populates="contact",
    )  # Event participations


class ContactHistory(Base):
    """Audit trail for contact changes.

    Implements full history tracking for Contact model changes using
    a versioned history pattern. Stores both the changed fields and
    their previous/new values.

    Attributes
    ----------
        id (UUID): Primary key
        contact_id (UUID): Reference to Contact
        version (int): Change version number
        changed_fields (dict): List of changed field names
        previous_values (dict): Values before change
        new_values (dict): Values after change
        change_type (str): Type of change (create/update/delete)
        extra_data (dict): Additional context
        created_by (str): User/system making change
        created_at (datetime): Change timestamp

    """

    __tablename__ = "contact_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    version = Column(Integer, nullable=False)
    changed_fields = Column(JSONB, nullable=False)
    previous_values = Column(JSONB, nullable=False)
    new_values = Column(JSONB, nullable=False)
    change_type = Column(String, nullable=False)
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_contact_history_contact_version", "contact_id", "version"),
    )


class ContactEmail(Base):
    """Contact email address model.

    Stores multiple email addresses per contact with verification status.
    Enforces uniqueness across all email addresses in the system.

    Attributes
    ----------
        id (UUID): Primary key
        contact_id (UUID): Reference to Contact
        version (int): Optimistic locking version
        email (str): Email address (unique)
        is_primary (bool): Primary email flag
        source (str): Source of email address
        verified (bool): Verification status
        verification_date (datetime): When verified
        extra_data (dict): Additional email metadata
        created_by (str): User/system that created
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        deleted_at (datetime): Soft delete timestamp
        deleted_by (str): User/system that deleted

    Relationships:
        contact: Parent Contact record

    """

    __tablename__ = "contact_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    email = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    source = Column(String)
    verified = Column(Boolean, default=False)
    verification_date = Column(TIMESTAMP(timezone=True))
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(TIMESTAMP(timezone=True))
    deleted_by = Column(String)

    # Relationships
    contact = relationship("Contact", back_populates="emails")

    __table_args__ = (
        UniqueConstraint("email", name="uq_contact_emails_email"),
        Index("ix_contact_emails_contact", "contact_id"),
    )


class ContactMetadata(Base):
    """Versioned contact metadata model.

    Stores additional contact information with temporal validity.
    Supports multiple versions of metadata with valid_from/valid_to ranges.

    Attributes
    ----------
        id (UUID): Primary key
        contact_id (UUID): Reference to Contact
        version (int): Optimistic locking version
        job_title (str): Contact's job title
        phone (str): Contact phone number
        linkedin (str): LinkedIn profile URL
        relationship_score (float): Relationship strength
        sentiment_score (float): Sentiment analysis
        relationship_type (str): Type of relationship
        is_business (bool): Business contact flag
        confidence (float): Data confidence score
        source (str): Metadata source
        valid_from (datetime): When metadata is valid from
        valid_to (datetime): When metadata is valid to
        extra_data (dict): Additional metadata
        created_by (str): User/system that created
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        deleted_at (datetime): Soft delete timestamp
        deleted_by (str): User/system that deleted

    Relationships:
        contact: Parent Contact record

    """

    __tablename__ = "contact_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    job_title = Column(String)
    phone = Column(String)
    linkedin = Column(String)
    relationship_score = Column(Float)
    sentiment_score = Column(Float)
    relationship_type = Column(String)
    is_business = Column(Boolean)
    confidence = Column(Float)
    source = Column(String)
    valid_from = Column(TIMESTAMP(timezone=True), nullable=False)
    valid_to = Column(TIMESTAMP(timezone=True))
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(TIMESTAMP(timezone=True))
    deleted_by = Column(String)

    # Relationships
    contact = relationship("Contact", back_populates="metadata_records")

    __table_args__ = (
        Index("ix_contact_metadata_validity", "contact_id", "valid_from", "valid_to"),
    )


class EnrichmentTask(Base):
    """Background task management for contact enrichment.

    Tracks enrichment tasks with retry logic and status monitoring.
    Supports multiple entity types and enrichment sources.

    Attributes
    ----------
        id (UUID): Primary key
        entity_type (str): Type of entity being enriched
        entity_id (UUID): Target entity ID
        task_type (str): Enrichment task type
        version (int): Optimistic locking version
        status (str): Current task status
        priority (int): Processing priority
        attempts (int): Number of attempts
        max_attempts (int): Maximum allowed attempts
        last_attempt (datetime): Last attempt timestamp
        next_attempt (datetime): Next attempt timestamp
        result (dict): Task result data
        error_message (str): Last error message
        extra_data (dict): Additional task context
        created_by (str): User/system that created
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        deleted_at (datetime): Soft delete timestamp
        deleted_by (str): User/system that deleted

    """

    __tablename__ = "enrichment_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    task_type = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=0)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    last_attempt = Column(TIMESTAMP(timezone=True))
    next_attempt = Column(TIMESTAMP(timezone=True))
    result = Column(JSONB)
    error_message = Column(String)
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(TIMESTAMP(timezone=True))
    deleted_by = Column(String)

    __table_args__ = (
        Index("ix_enrichment_tasks_entity", "entity_type", "entity_id"),
        Index("ix_enrichment_tasks_status_next", "status", "next_attempt"),
    )


class RawEmail(Base):
    """Raw email storage model.

    Stores complete email data from Gmail API with processing status.
    Tracks email metadata, content, and processing history.

    Attributes
    ----------
        id (UUID): Primary key
        gmail_id (str): Gmail message ID (unique)
        thread_id (str): Gmail thread ID
        version (int): Optimistic locking version
        subject (str): Email subject
        snippet (str): Email snippet
        plain_body (str): Plain text body
        html_body (str): HTML body
        raw_content (str): Complete raw email
        from_name (str): Sender name
        from_email (str): Sender email
        to_addresses (list): Recipient emails
        cc_addresses (list): CC emails
        bcc_addresses (list): BCC emails
        received_date (datetime): When email was received
        labels (list): Gmail labels
        extra_data (dict): Additional email metadata
        importance (int): Calculated importance
        category (str): Email category
        is_draft (bool): Draft flag
        is_sent (bool): Sent flag
        is_read (bool): Read status
        is_starred (bool): Starred status
        is_trashed (bool): Trash status
        status (str): Processing status
        processing_version (int): Processing version
        processed_date (datetime): Last processed timestamp
        error_message (str): Processing error
        size_estimate (int): Email size estimate
        created_by (str): User/system that created
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        deleted_at (datetime): Soft delete timestamp
        deleted_by (str): User/system that deleted

    """

    __tablename__ = "raw_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    gmail_id = Column(String, nullable=False, unique=True)
    thread_id = Column(String, index=True)
    version = Column(Integer, nullable=False, default=1)
    subject = Column(Text)
    snippet = Column(Text)
    plain_body = Column(Text)
    html_body = Column(Text)
    raw_content = Column(Text)
    from_name = Column(String)
    from_email = Column(String, index=True)
    to_addresses = Column(JSONB)
    cc_addresses = Column(JSONB)
    bcc_addresses = Column(JSONB)
    received_date = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    labels = Column(JSONB)
    extra_data = Column(JSONB)
    importance = Column(Integer, nullable=False, default=0)
    category = Column(String, index=True)
    is_draft = Column(Boolean, nullable=False, default=False)
    is_sent = Column(Boolean, nullable=False, default=False)
    is_read = Column(Boolean, nullable=False, default=False)
    is_starred = Column(Boolean, nullable=False, default=False)
    is_trashed = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="new", index=True)
    processing_version = Column(Integer, nullable=False, default=1)
    processed_date = Column(TIMESTAMP(timezone=True))
    error_message = Column(Text)
    size_estimate = Column(Integer)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(TIMESTAMP(timezone=True))
    deleted_by = Column(String)


class EmailProcessingHistory(Base):
    """Email processing audit trail.

    Tracks all state changes and processing attempts for emails.
    Provides complete history of email processing lifecycle.

    Attributes
    ----------
        id (UUID): Primary key
        email_id (UUID): Reference to RawEmail
        version (int): Processing version
        processing_type (str): Type of processing
        status_from (str): Previous status
        status_to (str): New status
        changes (dict): Detailed changes
        extra_data (dict): Additional context
        error_message (str): Processing error
        created_by (str): User/system that processed
        created_at (datetime): Processing timestamp

    """

    __tablename__ = "email_processing_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    email_id = Column(UUID(as_uuid=True), ForeignKey("raw_emails.id"), nullable=False)
    version = Column(Integer, nullable=False)
    processing_type = Column(String, nullable=False)
    status_from = Column(String, nullable=False)
    status_to = Column(String, nullable=False)
    changes = Column(JSONB, nullable=False)
    extra_data = Column(JSONB)
    error_message = Column(Text)
    created_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_email_processing_history_email_version", "email_id", "version"),
    )


class Event(Base):
    """Calendar event model.

    Represents meetings, calls, and other scheduled events.
    Tracks event details, participants, and related content.

    Attributes
    ----------
        id (UUID): Primary key
        type (str): Event type (meeting/call/etc)
        title (str): Event title
        description (str): Event description
        start_time (datetime): Event start
        end_time (datetime): Event end
        timezone (str): Event timezone
        location (str): Event location
        status (str): Event status
        source (str): Event source
        source_id (str): Source system ID
        organizer_id (UUID): Organizer contact
        is_client_meeting (bool): Client meeting flag
        importance (int): Event importance
        extra_data (dict): Additional event data
        created_by (str): User/system that created
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        deleted_at (datetime): Soft delete timestamp
        deleted_by (str): User/system that deleted

    Relationships:
        organizer: Contact who organized event
        participants: Event participants
        notes: Event notes
        transcript: Event transcript
        topics: Discussion topics
        action_items: Action items
        content_opportunities: Content opportunities

    """

    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True), nullable=False)
    timezone = Column(String, nullable=False)
    location = Column(String)
    status = Column(String, nullable=False, default="scheduled")
    source = Column(String, nullable=False)
    source_id = Column(String)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    is_client_meeting = Column(Boolean, nullable=False, default=False)
    importance = Column(Integer, nullable=False, default=0)
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(TIMESTAMP(timezone=True))
    deleted_by = Column(String)

    # Relationships
    organizer = relationship("Contact", back_populates="organized_events")
    participants = relationship("EventParticipant", back_populates="event")
    notes = relationship("EventNote", back_populates="event")
    transcript = relationship("EventTranscript", back_populates="event", uselist=False)
    topics = relationship("DiscussionTopic", back_populates="event")
    action_items = relationship("ActionItem", back_populates="event")
    content_opportunities = relationship("ContentOpportunity", back_populates="event")

    __table_args__ = (
        Index("ix_events_time_range", "start_time", "end_time"),
        Index("ix_events_source", "source", "source_id"),
    )


class EventParticipant(Base):
    """Event participation model.

    Tracks contacts participating in events with their roles and status.

    Attributes
    ----------
        id (UUID): Primary key
        event_id (UUID): Reference to Event
        contact_id (UUID): Reference to Contact
        role (str): Participant role
        response_status (str): RSVP status
        attended (bool): Attendance status
        extra_data (dict): Additional participation data
        created_by (str): User/system that created
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp

    Relationships:
        event: Parent Event record
        contact: Participating Contact

    """

    __tablename__ = "event_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    role = Column(String, nullable=False)
    response_status = Column(String)
    attended = Column(Boolean)
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    event = relationship("Event", back_populates="participants")
    contact = relationship("Contact", back_populates="participations")


class EventNote(Base):
    """Event notes model.

    Stores notes associated with events, supporting private/public visibility.

    Attributes
    ----------
        id (UUID): Primary key
        event_id (UUID): Reference to Event
        type (str): Note type
        content (str): Note content
        is_private (bool): Private note flag
        extra_data (dict): Additional note metadata
        created_by (str): User/system that created
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp

    Relationships:
        event: Parent Event record

    """

    __tablename__ = "event_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_private = Column(Boolean, nullable=False, default=False)
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    event = relationship("Event", back_populates="notes")


class EventRelatedItem(Base):
    """Event relationship model.

    Links events to other entities in the system with typed relationships.

    Attributes
    ----------
        id (UUID): Primary key
        event_id (UUID): Reference to Event
        entity_type (str): Related entity type
        entity_id (UUID): Related entity ID
        relationship_type (str): Relationship type
        extra_data (dict): Additional relationship data
        created_by (str): User/system that created
        created_at (datetime): Creation timestamp

    """

    __tablename__ = "event_related_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    relationship_type = Column(String, nullable=False)
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_event_related_items_entity", "entity_type", "entity_id"),
    )


class EventTranscript(Base):
    """Event transcript model.

    Stores complete transcripts of events with processing status.
    Supports multiple versions and language processing.

    Attributes
    ----------
        id (UUID): Primary key
        event_id (UUID): Reference to Event
        version (int): Transcript version
        status (str): Processing status
        full_text (str): Complete transcript text
        language (str): Transcript language
        confidence_score (float): Transcription confidence
        speaker_count (int): Number of speakers
        duration_seconds (int): Transcript duration
        source (str): Transcription source
        extra_data (dict): Additional transcript data
        created_by (str): User/system that created
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp

    Relationships:
        event: Parent Event record
        segments: Individual transcript segments

    """

    __tablename__ = "event_transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="processing")
    full_text = Column(Text)
    language = Column(String, nullable=False, default="en")
    confidence_score = Column(Float, nullable=False)
    speaker_count = Column(Integer)
    duration_seconds = Column(Integer)
    source = Column(String, nullable=False)
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    event = relationship("Event", back_populates="transcript")
    segments = relationship("TranscriptSegment", back_populates="transcript")


class TranscriptSegment(Base):
    """Transcript segment model.

    Represents individual segments of an event transcript.
    Tracks speaker attribution, timing, and content analysis.

    Attributes
    ----------
        id (UUID): Primary key
        transcript_id (UUID): Reference to EventTranscript
        speaker_id (UUID): Reference to Contact (speaker)
        start_time (int): Segment start time (seconds)
        end_time (int): Segment end time (seconds)
        text (str): Segment text
        confidence_score (float): Transcription confidence
        speaker_confidence (float): Speaker identification confidence
        content_score (float): Content importance score
        is_quotable (bool): Quotable content flag
        key_points (list): Key points in segment
        entities (list): Named entities
        sentiment_score (float): Sentiment analysis
        topics (list): Related topics
        extra_data (dict): Additional segment data
        created_at (datetime): Creation timestamp

    Relationships:
        transcript: Parent EventTranscript record

    """

    __tablename__ = "transcript_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    transcript_id = Column(
        UUID(as_uuid=True),
        ForeignKey("event_transcripts.id"),
        nullable=False,
    )
    speaker_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    speaker_confidence = Column(Float)
    content_score = Column(Float)
    is_quotable = Column(Boolean, default=False)
    key_points = Column(JSONB)
    entities = Column(JSONB)
    sentiment_score = Column(Float)
    topics = Column(JSONB)
    extra_data = Column(JSONB)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    transcript = relationship("EventTranscript", back_populates="segments")

    __table_args__ = (
        Index("ix_transcript_segments_time", "transcript_id", "start_time"),
        Index("ix_transcript_segments_content", "content_score", "is_quotable"),
    )


class ContentOpportunity(Base):
    """Content opportunity model.

    Identifies and tracks potential content pieces derived from events.
    Supports content planning and assignment workflows.

    Attributes
    ----------
        id (UUID): Primary key
        event_id (UUID): Reference to Event
        segment_ids (list): Related transcript segments
        type (str): Opportunity type
        title (str): Content title
        description (str): Content description
        target_audience (list): Target audience
        key_points (list): Key content points
        suggested_quotes (list): Suggested quotes
        content_format (str): Content format
        estimated_length (int): Estimated length
        priority_score (float): Content priority
        status (str): Opportunity status
        assigned_to (UUID): Assigned contact
        due_date (datetime): Content due date
        topics (list): Related topics
        keywords (list): Content keywords
        source_context (dict): Source context
        approval_required (bool): Approval flag
        extra_data (dict): Additional opportunity data
        created_by (str): User/system that created
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        deleted_at (datetime): Soft delete timestamp
        deleted_by (str): User/system that deleted

    Relationships:
        event: Parent Event record

    """

    __tablename__ = "content_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    segment_ids = Column(JSONB, nullable=False)
    type = Column(String, nullable=False)
    title = Column(String)
    description = Column(Text)
    target_audience = Column(JSONB)
    key_points = Column(JSONB)
    suggested_quotes = Column(JSONB)
    content_format = Column(String)
    estimated_length = Column(Integer)
    priority_score = Column(Float, nullable=False, default=0)
    status = Column(String, nullable=False, default="identified")
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    due_date = Column(TIMESTAMP(timezone=True))
    topics = Column(JSONB)
    keywords = Column(JSONB)
    source_context = Column(JSONB)
    approval_required = Column(Boolean, nullable=False, default=False)
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at = Column(TIMESTAMP(timezone=True))
    deleted_by = Column(String)

    # Relationships
    event = relationship("Event", back_populates="content_opportunities")

    __table_args__ = (
        Index("ix_content_opportunities_status", "status", "priority_score"),
    )


class DiscussionTopic(Base):
    """Meeting topic model.

    Tracks individual discussion topics within events.
    Supports topic analysis and action item generation.

    Attributes
    ----------
        id (UUID): Primary key
        event_id (UUID): Reference to Event
        topic (str): Topic name
        category (str): Topic category
        summary (str): Topic summary
        start_time (int): Topic start time (seconds)
        end_time (int): Topic end time (seconds)
        sentiment_score (float): Topic sentiment
        importance_score (float): Topic importance
        extra_data (dict): Additional topic data
        created_by (str): User/system that created
        created_at (datetime): Creation timestamp

    Relationships:
        event: Parent Event record
        action_items: Related action items

    """

    __tablename__ = "discussion_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    topic = Column(String, nullable=False)
    category = Column(String)
    summary = Column(Text)
    start_time = Column(Integer)
    end_time = Column(Integer)
    sentiment_score = Column(Float)
    importance_score = Column(Float)
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    event = relationship("Event", back_populates="topics")
    action_items = relationship("ActionItem", back_populates="topic")


class ActionItem(Base):
    """Action item model.

    Tracks tasks and follow-ups from events and discussions.
    Supports assignment, prioritization, and completion tracking.

    Attributes
    ----------
        id (UUID): Primary key
        event_id (UUID): Reference to Event
        topic_id (UUID): Reference to DiscussionTopic
        type (str): Action item type
        title (str): Action title
        description (str): Action description
        status (str): Completion status
        priority (int): Action priority
        due_date (datetime): Due date
        assigned_to (UUID): Assigned contact
        assigned_by (UUID): Assigning contact
        completion_date (datetime): Completion date
        extra_data (dict): Additional action data
        created_by (str): User/system that created
        updated_by (str): User/system that last updated
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp

    Relationships:
        event: Parent Event record
        topic: Related DiscussionTopic

    """

    __tablename__ = "action_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("discussion_topics.id"))
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=0)
    due_date = Column(TIMESTAMP(timezone=True))
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    completion_date = Column(TIMESTAMP(timezone=True))
    extra_data = Column(JSONB)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    event = relationship("Event", back_populates="action_items")
    topic = relationship("DiscussionTopic", back_populates="action_items")

    __table_args__ = (
        Index("ix_action_items_status", "status", "due_date"),
        Index("ix_action_items_assigned", "assigned_to", "status"),
    )
