"""Script to detect form submissions and client intake patterns in emails.

This module provides functionality to:
- Detect form submissions in emails using deterministic pattern matching
- Track form submissions in a SQLite database
- Manage form data extraction workflows
- Handle both raw and processed email sources

The detection uses regex patterns rather than LLM inference for reliability and speed.
All detected forms are tracked in a database table with their extraction status.
"""

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class FormSubmission:
    """Represents a detected form submission from an email.

    Attributes:
    ----------
        email_id: Unique identifier of the source email
        from_email: Sender's email address
        from_name: Sender's display name
        subject: Email subject line
        date: Date email was received
        form_type: Type of form detected (e.g., CLIENT_INTAKE)
        confidence: Confidence score of detection (0.0-1.0)
        metadata: Additional metadata about the submission
        needs_extraction: Whether form data needs to be extracted
        source_table: Database table where email was found (raw_emails or emails)

    """

    email_id: str
    from_email: str
    from_name: str
    subject: str
    date: datetime
    form_type: str
    confidence: float
    metadata: Dict[str, Any]
    needs_extraction: bool = True
    source_table: str = "unknown"


class FormDetector:
    """Detects and tracks form submissions in email content.

    This class provides methods to:
    - Detect form submissions using regex patterns
    - Track submissions in a database
    - Manage extraction workflows
    - Query pending extractions

    Attributes:
    ----------
        db_path: Path to SQLite database file
        conn: Active database connection

    """

    # Known form patterns with their confidence scores and SQL LIKE patterns
    # Each pattern contains:
    # - pattern: Regex pattern to match in subject
    # - sql_pattern: SQL LIKE pattern for database queries
    # - form_type: Type identifier for the form
    # - confidence: Detection confidence score (0.0-1.0)
    # - has_form_data: Whether form data needs extraction
    FORM_PATTERNS = [
        {
            "pattern": r"Client Intake Questionnaire.*new responses",
            "sql_pattern": "%Client Intake Questionnaire%new responses%",
            "form_type": "CLIENT_INTAKE",
            "confidence": 0.95,
            "has_form_data": True,
        },
        {
            "pattern": r"New submission from Account Opening Information",
            "sql_pattern": "%New submission from Account Opening Information%",
            "form_type": "ACCOUNT_OPENING",
            "confidence": 0.95,
            "has_form_data": True,
        },
        {
            "pattern": r"New Form Entry.*Onboarding Form",
            "sql_pattern": "%New Form Entry%Onboarding Form%",
            "form_type": "ONBOARDING",
            "confidence": 0.90,
            "has_form_data": True,
        },
        {
            "pattern": r"New Form Submission.*ethicic\.com",
            "sql_pattern": "%New Form Submission%ethicic.com%",
            "form_type": "ETHICIC_FORM",
            "confidence": 0.90,
            "has_form_data": True,
        },
    ]

    def __init__(self):
        """Initialize the FormDetector with database connection.

        Creates or connects to SQLite database and ensures the tracking table exists.
        """
        self.db_path = "email_data.db"
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        self._ensure_form_tracking_table(cursor)
        self.conn.commit()
        cursor.close()

    def _ensure_form_tracking_table(self, cursor):
        """Ensure the form tracking table exists with proper schema.

        Drops and recreates the table if it exists to ensure schema consistency.
        Creates necessary indexes for query performance.

        Args:
        ----
            cursor: Database cursor for executing SQL commands

        """
        # Drop existing table to ensure clean schema
        cursor.execute("DROP TABLE IF EXISTS form_data_tracking")

        # Create table with constraints and indexes
        cursor.execute(
            """
            CREATE TABLE form_data_tracking (
                email_id TEXT,
                form_type TEXT NOT NULL,
                source_table TEXT NOT NULL,
                submission_date TIMESTAMP,
                needs_extraction BOOLEAN DEFAULT 1,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                extracted_data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email_id, source_table)
            )
            """
        )

        # Create index for frequently queried field
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_needs_extraction
            ON form_data_tracking(needs_extraction)
            """
        )

    def detect_form_type(self, subject: str) -> Optional[tuple[str, float, bool]]:
        """Detect form type from email subject using regex patterns.

        Args:
        ----
            subject: Email subject line to analyze

        Returns:
        -------
            Tuple containing:
            - form_type: Type identifier string
            - confidence: Detection confidence score (0.0-1.0)
            - has_form_data: Whether form data needs extraction
            Or None if no matching form pattern found

        """
        subject = subject.strip()
        for pattern in self.FORM_PATTERNS:
            if re.search(pattern["pattern"], subject, re.IGNORECASE):
                return (
                    pattern["form_type"],
                    pattern["confidence"],
                    pattern["has_form_data"],
                )
        return None

    def process_emails(self, batch_size: int = 1000) -> List[FormSubmission]:
        """Process unprocessed emails from both raw_emails and emails tables.

        Scans both email tables for new submissions matching form patterns.
        Creates tracking records for detected forms.

        Args:
        ----
            batch_size: Maximum number of emails to process in one batch

        Returns:
        -------
            List of FormSubmission objects representing detected forms

        """
        submissions = []

        with sqlite3.connect("email_data.db") as conn:
            cursor = conn.cursor()
            self._ensure_form_tracking_table(cursor)

            # Process raw_emails table for new submissions
            cursor.execute(
                """
                SELECT r.message_id, r.from_email, r.from_name, r.subject, r.date
                FROM raw_emails r
                LEFT JOIN form_data_tracking t
                ON r.message_id = t.email_id AND t.source_table = 'raw_emails'
                WHERE t.email_id IS NULL
                LIMIT ?
            """,
                (batch_size,),
            )

            # Process each raw email
            for row in cursor.fetchall():
                message_id, from_email, from_name, subject, date = row
                form_type = self.detect_form_type(subject)
                if form_type:
                    form_type_name, confidence, needs_extraction = form_type
                    submission = FormSubmission(
                        email_id=message_id,
                        from_email=from_email,
                        from_name=from_name,
                        subject=subject,
                        date=date,
                        form_type=form_type_name,
                        confidence=confidence,
                        metadata={},
                        needs_extraction=needs_extraction,
                        source_table="raw_emails",
                    )
                    submissions.append(submission)

                    # Insert tracking record using INSERT OR IGNORE to handle duplicates
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO form_data_tracking (
                            email_id, source_table, form_type, submission_date,
                            needs_extraction, status
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            message_id,
                            "raw_emails",
                            form_type_name,
                            date,
                            needs_extraction,
                            "pending",
                        ),
                    )

            # Process emails table for new submissions
            cursor.execute(
                """
                SELECT e.message_id, e.from_email, e.from_name, e.subject, e.date
                FROM emails e
                LEFT JOIN form_data_tracking t
                ON e.message_id = t.email_id AND t.source_table = 'emails'
                WHERE t.email_id IS NULL
                LIMIT ?
            """,
                (batch_size,),
            )

            # Process each processed email
            for row in cursor.fetchall():
                message_id, from_email, from_name, subject, date = row
                form_type = self.detect_form_type(subject)
                if form_type:
                    form_type_name, confidence, needs_extraction = form_type
                    submission = FormSubmission(
                        email_id=message_id,
                        from_email=from_email,
                        from_name=from_name,
                        subject=subject,
                        date=date,
                        form_type=form_type_name,
                        confidence=confidence,
                        metadata={},
                        needs_extraction=needs_extraction,
                        source_table="emails",
                    )
                    submissions.append(submission)

                    # Insert tracking record
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO form_data_tracking (
                            email_id, source_table, form_type, submission_date,
                            needs_extraction, status
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            message_id,
                            "emails",
                            form_type_name,
                            date,
                            needs_extraction,
                            "pending",
                        ),
                    )

            conn.commit()

        print(f"Processed {len(submissions)} new form submissions")
        return submissions

    def get_pending_extractions(self) -> List[FormSubmission]:
        """Get list of form submissions that need data extraction.

        Queries both email tables for submissions marked as needing extraction.

        Returns:
        -------
            List of FormSubmission objects requiring data extraction

        """
        conn = sqlite3.connect("email_data.db")
        cursor = conn.cursor()

        # Ensure tracking table exists
        self._ensure_form_tracking_table(cursor)

        # Query raw_emails for pending extractions
        cursor.execute(
            """
            SELECT r.message_id, r.from_email, r.from_name, r.subject, r.date,
                   t.form_type, t.notes, 'raw_emails' as source
            FROM raw_emails r
            JOIN form_data_tracking t ON r.message_id = t.email_id
            WHERE t.needs_extraction = 1
            AND t.source_table = 'raw_emails'
        """
        )
        raw_pending = cursor.fetchall()

        # Query emails table for pending extractions
        cursor.execute(
            """
            SELECT e.message_id, e.from_email, e.from_name, e.subject, e.date,
                   t.form_type, t.notes, 'emails' as source
            FROM emails e
            JOIN form_data_tracking t ON e.message_id = t.email_id
            WHERE t.needs_extraction = 1
            AND t.source_table = 'emails'
        """
        )
        email_pending = cursor.fetchall()

        # Convert database results to FormSubmission objects
        pending = []
        for result in raw_pending + email_pending:
            submission = FormSubmission(
                email_id=result[0],
                from_email=result[1],
                from_name=result[2],
                subject=result[3],
                date=result[4],
                form_type=result[5],
                confidence=0.9,
                metadata={"notes": result[6]},
                needs_extraction=True,
                source_table=result[7],
            )
            pending.append(submission)

        conn.close()
        return pending

    def __del__(self):
        """Clean up database connection on object destruction.

        Ensures database connection is properly closed when the detector is destroyed.
        """
        if hasattr(self, "conn"):
            self.conn.close()


if __name__ == "__main__":
    """Main execution block for form detection.

    When run directly, this script will:
    1. Initialize form detector
    2. Process new emails for form submissions
    3. Display pending extractions
    """
    detector = FormDetector()
    processed = detector.process_emails()
    print(f"Processed {len(processed)} new form submissions")

    # Get and display pending extractions
    pending = detector.get_pending_extractions()
    if pending:
        print("\nForm submissions needing data extraction:")
        for submission in pending:
            print(f"\n{submission.form_type} submission from {submission.from_email}")
            print(f"Date: {submission.date}")
            print(f"Subject: {submission.subject}")
            print(f"Source: {submission.source_table}")
            if submission.notes:
                print(f"Notes: {submission.notes}")
    else:
        print("\nNo pending form submissions need data extraction")
