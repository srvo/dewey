from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class FormSubmission:
    """Represents a detected form submission from an email.

    Attributes
    ----------
        email_id: Unique identifier of the source email.
        from_email: Sender's email address.
        from_name: Sender's display name.
        subject: Email subject line.
        date: Date email was received.
        form_type: Type of form detected (e.g., CLIENT_INTAKE).
        confidence: Confidence score of detection (0.0-1.0).
        metadata: Additional metadata about the submission.
        needs_extraction: Whether form data needs to be extracted.
        source_table: Database table where email was found (raw_emails or emails).

    """

    email_id: str
    from_email: str
    from_name: str
    subject: str
    date: datetime
    form_type: str
    confidence: float
    metadata: dict[str, Any]
    needs_extraction: bool = True
    source_table: str = "unknown"


class FormDetector:
    """Detects and tracks form submissions in email content.

    This class provides methods to:
    - Detect form submissions using regex patterns.
    - Track submissions in a database.
    - Manage extraction workflows.
    - Query pending extractions.

    Attributes
    ----------
        db_path: Path to SQLite database file.
        conn: Active database connection.

    """

    FORM_PATTERNS: list[dict[str, Any]] = [
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

    def __init__(self) -> None:
        """Initialize the FormDetector with database connection.

        Creates or connects to SQLite database and ensures the tracking table exists.
        """
        self.db_path: str = "email_data.db"
        self.conn: sqlite3.Connection = sqlite3.connect(self.db_path)
        self._setup_database()

    def _setup_database(self) -> None:
        """Sets up the database by ensuring the form tracking table exists."""
        with self.conn:
            cursor = self.conn.cursor()
            self._ensure_form_tracking_table(cursor)

    def _ensure_form_tracking_table(self, cursor: sqlite3.Cursor) -> None:
        """Ensure the form tracking table exists with proper schema.

        Drops and recreates the table if it exists to ensure schema consistency.
        Creates necessary indexes for query performance.

        Args:
        ----
            cursor: Database cursor for executing SQL commands.

        """
        cursor.execute("DROP TABLE IF EXISTS form_data_tracking")
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
            """,
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_needs_extraction
            ON form_data_tracking(needs_extraction)
            """,
        )

    def detect_form_type(self, subject: str) -> tuple[str, float, bool] | None:
        """Detect form type from email subject using regex patterns.

        Args:
        ----
            subject: Email subject line to analyze.

        Returns:
        -------
            Tuple containing:
            - form_type: Type identifier string.
            - confidence: Detection confidence score (0.0-1.0).
            - has_form_data: Whether form data needs extraction.
            Or None if no matching form pattern found.

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

    def _process_email_table(
        self,
        cursor: sqlite3.Cursor,
        table_name: str,
        batch_size: int,
    ) -> list[FormSubmission]:
        """Processes emails from a given table and detects form submissions.

        Args:
        ----
            cursor: Database cursor for executing SQL commands.
            table_name: Name of the email table to process (raw_emails or emails).
            batch_size: Maximum number of emails to process in one batch.

        Returns:
        -------
            List of FormSubmission objects representing detected forms.

        """
        submissions: list[FormSubmission] = []

        cursor.execute(
            f"""
            SELECT e.message_id, e.from_email, e.from_name, e.subject, e.date
            FROM {table_name} e
            LEFT JOIN form_data_tracking t
            ON e.message_id = t.email_id AND t.source_table = ?
            WHERE t.email_id IS NULL
            LIMIT ?
            """,
            (table_name, batch_size),
        )

        for row in cursor.fetchall():
            message_id, from_email, from_name, subject, date = row
            form_data = self.detect_form_type(subject)
            if form_data:
                form_type_name, confidence, needs_extraction = form_data
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
                    source_table=table_name,
                )
                submissions.append(submission)
                self._insert_tracking_record(cursor, submission)

        return submissions

    def _insert_tracking_record(
        self,
        cursor: sqlite3.Cursor,
        submission: FormSubmission,
    ) -> None:
        """Inserts a tracking record into the form_data_tracking table.

        Args:
        ----
            cursor: Database cursor for executing SQL commands.
            submission: FormSubmission object representing the detected form.

        """
        cursor.execute(
            """
            INSERT OR IGNORE INTO form_data_tracking (
                email_id, source_table, form_type, submission_date,
                needs_extraction, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                submission.email_id,
                submission.source_table,
                submission.form_type,
                submission.date,
                submission.needs_extraction,
                "pending",
            ),
        )

    def process_emails(self, batch_size: int = 1000) -> list[FormSubmission]:
        """Process unprocessed emails from both raw_emails and emails tables.

        Scans both email tables for new submissions matching form patterns.
        Creates tracking records for detected forms.

        Args:
        ----
            batch_size: Maximum number of emails to process in one batch.

        Returns:
        -------
            List of FormSubmission objects representing detected forms.

        """
        submissions: list[FormSubmission] = []

        with sqlite3.connect("email_data.db") as conn:
            cursor = conn.cursor()
            self._ensure_form_tracking_table(cursor)

            raw_email_submissions = self._process_email_table(
                cursor,
                "raw_emails",
                batch_size,
            )
            email_submissions = self._process_email_table(cursor, "emails", batch_size)

            submissions.extend(raw_email_submissions)
            submissions.extend(email_submissions)

            conn.commit()

        return submissions

    def get_pending_extractions(self) -> list[FormSubmission]:
        """Get list of form submissions that need data extraction.

        Queries both email tables for submissions marked as needing extraction.

        Returns
        -------
            List of FormSubmission objects requiring data extraction.

        """
        conn = sqlite3.connect("email_data.db")
        cursor = conn.cursor()

        self._ensure_form_tracking_table(cursor)

        pending_raw = self._query_pending_extractions(cursor, "raw_emails")
        pending_emails = self._query_pending_extractions(cursor, "emails")

        pending: list[FormSubmission] = pending_raw + pending_emails

        conn.close()
        return pending

    def _query_pending_extractions(
        self,
        cursor: sqlite3.Cursor,
        source_table: str,
    ) -> list[FormSubmission]:
        """Queries the database for pending extractions from a specific source table.

        Args:
        ----
            cursor: Database cursor for executing SQL commands.
            source_table: The table to query (e.g., 'raw_emails' or 'emails').

        Returns:
        -------
            A list of FormSubmission objects representing pending extractions.

        """
        cursor.execute(
            f"""
            SELECT e.message_id, e.from_email, e.from_name, e.subject, e.date,
                   t.form_type, t.notes
            FROM {source_table} e
            JOIN form_data_tracking t ON e.message_id = t.email_id
            WHERE t.needs_extraction = 1
            AND t.source_table = ?
            """,
            (source_table,),
        )

        results = cursor.fetchall()
        pending: list[FormSubmission] = []

        for result in results:
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
                source_table=source_table,
            )
            pending.append(submission)

        return pending

    def __del__(self) -> None:
        """Clean up database connection on object destruction.

        Ensures database connection is properly closed when the detector is destroyed.
        """
        if hasattr(self, "conn"):
            self.conn.close()


if __name__ == "__main__":
    """Main execution block for form detection.

    When run directly, this script will:
    1. Initialize form detector.
    2. Process new emails for form submissions.
    3. Display pending extractions.
    """
    detector: FormDetector = FormDetector()
    processed: list[FormSubmission] = detector.process_emails()

    pending: list[FormSubmission] = detector.get_pending_extractions()
    if pending:
        for submission in pending:
            if submission.metadata.get("notes"):
                pass
    else:
        pass
