import json
import logging
import os
from typing import Any, Dict, List, Tuple

import duckdb
from dotenv import load_dotenv

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import db_manager
from dewey.utils.database import execute_query, fetch_all, fetch_one


class EmailEnrichment(BaseScript):
    """Enriches email data with additional metadata.

    This class provides methods to enrich email data with:
    - Message priority scores
    - Contact information extracted from email content
    - Business opportunity detection
    - Full message bodies (plain text and HTML)
    """

    def __init__(self):
        """Initializes the EmailEnrichment script."""
        super().__init__(
            name="EmailEnrichment",
            description="Process and enrich email data from Gmail",
            config_section="core",
            requires_db=False,  # We'll manage our connection differently
            enable_llm=False,
        )

        # Set up logging
        self.logger = logging.getLogger("EmailEnrichment")

        # Set up database connection - use MotherDuck by default
        load_dotenv()
        self.motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
        if self.motherduck_token:
            os.environ["motherduck_token"] = self.motherduck_token

        self.db_path = "md:dewey"  # Always use MotherDuck as primary
        self.connection = None
        self.use_gmail_api = False  # Default to not using Gmail API

        # Initialize database tables right away
        try:
            with self._get_connection() as conn:
                self._setup_database_tables(conn)
                self.logger.info(
                    "Database tables for email enrichment initialized during startup"
                )
        except Exception as e:
            self.logger.error(f"Error setting up database tables: {e}")

        # Random emoji set for processing feedback
        self.emojis = ["✉️", "📩", "📬", "📮", "📧", "📨", "📪", "📫", "📭", "📤", "📥"]

    def _get_connection(self):
        """Get a connection to the database using a context manager.

        Returns:
            Context manager for database connection

        """
        return ConnectionManager(self)

    def execute(self) -> None:
        """Execute the email enrichment process with proper error handling."""
        self.logger.info("Starting email enrichment process")

        try:
            # Use the database manager's context manager
            with db_manager.get_connection() as conn:
                # Setup database tables
                self._setup_database_tables(conn)

                # Process emails that need enrichment
                self._process_emails_for_enrichment(conn)

            self.logger.info("Email enrichment process completed successfully")

        except Exception as e:
            self.logger.error(f"Error in email enrichment process: {e}")
            raise

    def _setup_database_tables(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Set up the necessary database tables for email enrichment.

        Args:
            conn: Database connection

        """
        try:
            # Create or validate email enrichment status table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS email_enrichment_status (
                email_id VARCHAR PRIMARY KEY,
                status VARCHAR,
                priority_score FLOAT,
                priority_reason VARCHAR,
                priority_confidence FLOAT,
                body_enriched BOOLEAN,
                contact_info_enriched BOOLEAN,
                opportunity_detected BOOLEAN,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Create or validate email content table for storing enriched content
            conn.execute("""
            CREATE TABLE IF NOT EXISTS email_content (
                email_id VARCHAR PRIMARY KEY,
                plain_body TEXT,
                html_body TEXT,
                extracted_contact_info JSON,
                business_opportunities JSON,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            self.logger.info("Database tables for email enrichment created or verified")

        except Exception as e:
            self.logger.error(f"Error setting up database tables: {e}")
            raise

    def _process_emails_for_enrichment(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Process emails that need enrichment.

        Args:
            conn: Database connection

        """
        try:
            # Get emails that need enrichment - using msg_id as primary identifier instead of draft_id
            query = """
            SELECT msg_id, from_address, NULL as from_name, subject, import_timestamp
            FROM emails e
            LEFT JOIN email_enrichment_status s ON e.msg_id = s.email_id
            WHERE s.email_id IS NULL OR s.status = 'pending'
            ORDER BY import_timestamp DESC
            LIMIT ?
            """
            params = [self.batch_size]
            emails = fetch_all(conn, query, params)

            self.logger.info(f"Found {len(emails)} emails to enrich")

            for email in emails:
                msg_id, from_address, from_name, subject, import_timestamp = email

                # Skip if msg_id is null
                if msg_id is None:
                    self.logger.warning("Skipping email with null msg_id")
                    continue

                # Process the email
                try:
                    # Fetch email body from Gmail if needed
                    self._fetch_email_body(conn, msg_id)

                    # Extract contact information
                    contact_info = self._extract_contact_info(conn, msg_id)

                    # Detect business opportunities
                    opportunities = self._detect_opportunities(conn, msg_id)

                    # Calculate priority score
                    priority_score, confidence, reason = self._calculate_priority(
                        conn, msg_id, from_address, subject, contact_info, opportunities
                    )

                    # Update enrichment status
                    self._update_enrichment_status(
                        conn,
                        msg_id,
                        priority_score,
                        reason,
                        confidence,
                        bool(contact_info),
                        bool(opportunities),
                    )

                    self.logger.info(f"Successfully enriched email {msg_id}")

                except Exception as e:
                    self.logger.error(f"Error enriching email {msg_id}: {e}")
                    # Mark this email as having failed enrichment
                    try:
                        self._update_enrichment_status(
                            conn,
                            msg_id,
                            0.0,
                            f"Error: {str(e)}",
                            0.0,
                            False,
                            False,
                            status="failed",
                        )
                    except Exception as inner_e:
                        self.logger.error(
                            f"Failed to update status for email {msg_id}: {inner_e}"
                        )

        except Exception as e:
            self.logger.error(f"Error processing emails for enrichment: {e}")
            raise

    def _fetch_email_body(
        self, conn: duckdb.DuckDBPyConnection, email_id: str
    ) -> tuple[str, str]:
        """Fetch email body content from the database or Gmail API as fallback.

        Args:
            conn: Database connection
            email_id: ID of the email to fetch

        Returns:
            Tuple of (plain_text_body, html_body)

        """
        # First check if we already have the content in email_content
        query = """
        SELECT plain_body, html_body FROM email_content
        WHERE email_id = ?
        """
        params = [email_id]
        result = fetch_one(conn, query, params)

        if result:
            plain_body, html_body = result
            self.logger.debug(f"Found existing email content for {email_id}")
            return plain_body, html_body

        # Try to get from raw_emails table first (should be faster than API)
        try:
            query = """
            SELECT body, headers, subject, sender
            FROM raw_emails
            WHERE message_id = ?
            """
            params = [email_id]
            raw_result = fetch_one(conn, query, params)

            if raw_result and raw_result[0]:  # If we have a body in raw_emails
                body, headers, subject, sender = raw_result
                self.logger.info(f"Using body from raw_emails for {email_id}")

                # If body has HTML content, try to extract it
                if body and "<html" in body.lower():
                    html_body = body
                    # Extract plain text from HTML
                    plain_text = body
                    try:
                        # Remove HTML tags if possible
                        import re

                        plain_text = re.sub(r"<[^>]+>", " ", html_body)
                        plain_text = re.sub(r"\s+", " ", plain_text).strip()
                    except Exception as e:
                        self.logger.warning(
                            f"Error extracting plain text from HTML: {e}"
                        )
                else:
                    # Plain text only
                    plain_text = body
                    html_body = f"<html><body><pre>{body}</pre></body></html>"

                # Store the content
                self._store_email_content(conn, email_id, plain_text, html_body)
                return plain_text, html_body
        except Exception as e:
            self.logger.warning(f"Error getting body from raw_emails: {e}")

        # Try to fetch from Gmail API if client is available
        if self.use_gmail_api and self.gmail_client:
            try:
                self.logger.info(f"Fetching email {email_id} from Gmail API")
                message = self.gmail_client.fetch_message(email_id)

                if message:
                    # Extract body
                    plain_body, html_body = self.gmail_client.extract_body(message)

                    if plain_body or html_body:
                        self.logger.info(
                            f"Successfully fetched email body from Gmail API for {email_id}"
                        )

                        # Get subject from headers
                        headers = {
                            header["name"].lower(): header["value"]
                            for header in message.get("payload", {}).get("headers", [])
                        }

                        subject = headers.get("subject", "")

                        # Add subject to plain text if available
                        if plain_body and subject:
                            plain_body = f"Subject: {subject}\n\n{plain_body}"

                        # Add subject to HTML if available
                        if html_body and subject:
                            # If html_body has <body> tag, add subject inside it
                            if "<body" in html_body.lower():
                                html_body = html_body.replace(
                                    "<body", f"<body><h3>{subject}</h3>", 1
                                )
                            else:
                                html_body = f"<html><body><h3>{subject}</h3>{html_body}</body></html>"

                        # Store the content
                        self._store_email_content(conn, email_id, plain_body, html_body)
                        return plain_body, html_body
            except Exception as e:
                self.logger.error(f"Error fetching email from Gmail API: {e}")
                # Continue to fallback methods

        # Fall back to snippet if no body found
        query = """
        SELECT snippet, subject FROM raw_emails
        WHERE message_id = ?
        """
        params = [email_id]
        result = fetch_one(conn, query, params)

        if not result or not result[0]:
            self.logger.warning(f"No content found for email {email_id}")
            plain_body = f"No content available for email {email_id}"
            html_body = (
                f"<html><body>No content available for email {email_id}</body></html>"
            )
        else:
            snippet, subject = result
            # Use snippet and subject for body
            plain_body = f"Subject: {subject or 'No subject'}\n\n{snippet}"
            html_body = f"<html><body><h3>{subject or 'No subject'}</h3><p>{snippet}</p></body></html>"
            self.logger.info(f"Using snippet as body for email {email_id}")

        # Store the content
        self._store_email_content(conn, email_id, plain_body, html_body)
        return plain_body, html_body

    def _store_email_content(
        self,
        conn: duckdb.DuckDBPyConnection,
        email_id: str,
        plain_body: str,
        html_body: str,
    ) -> None:
        """Store email content in the database.

        Args:
            conn: Database connection
            email_id: ID of the email
            plain_body: Plain text body
            html_body: HTML body

        """
        # Check if record exists first
        check_query = """
        SELECT 1 FROM email_content WHERE email_id = ? LIMIT 1
        """
        exists = fetch_one(conn, check_query, [email_id])

        if exists:
            # Update existing record
            query = """
            UPDATE email_content SET
                plain_body = ?,
                html_body = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE email_id = ?
            """
            params = [plain_body, html_body, email_id]
        else:
            # Insert new record
            query = """
            INSERT INTO email_content (email_id, plain_body, html_body, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """
            params = [email_id, plain_body, html_body]

        execute_query(conn, query, params)

    def _extract_contact_info(
        self, conn: duckdb.DuckDBPyConnection, email_id: str
    ) -> dict[str, Any]:
        """Extract contact information from email content.

        Args:
            conn: Database connection
            email_id: ID of the email to process

        Returns:
            Dictionary containing extracted contact information

        """
        # Get the email body
        query = """
        SELECT plain_body, html_body FROM email_content
        WHERE email_id = ?
        """
        params = [email_id]
        result = fetch_one(conn, query, params)

        if not result:
            return {}

        plain_body, html_body = result

        # In a real implementation, this would use regex or NLP to extract contact info
        # For testing, we'll just create some placeholder data
        contact_info = {
            "name": "Example Contact",
            "phone": "555-123-4567",
            "job_title": "Test Position",
            "company": "Sample Corp",
            "confidence": 0.85,
        }

        # Store the extracted contact info
        query = """
        UPDATE email_content
        SET extracted_contact_info = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE email_id = ?
        """
        params = [json.dumps(contact_info), email_id]
        execute_query(conn, query, params)

        return contact_info

    def _detect_opportunities(
        self, conn: duckdb.DuckDBPyConnection, email_id: str
    ) -> list[dict[str, Any]]:
        """Detect business opportunities in email content.

        Args:
            conn: Database connection
            email_id: ID of the email to process

        Returns:
            List of detected opportunities

        """
        # Get the email body and subject
        query = """
        SELECT e.subject, c.plain_body
        FROM emails e
        JOIN email_content c ON e.msg_id = c.email_id
        WHERE e.msg_id = ?
        """
        params = [email_id]
        result = fetch_one(conn, query, params)

        if not result:
            return []

        subject, plain_body = result

        # In a real implementation, this would use NLP to identify opportunities
        # For testing, we'll just create some placeholder data
        if (
            "proposal" in (subject or "").lower()
            or "opportunity" in (plain_body or "").lower()
        ):
            opportunities = [
                {
                    "type": "business_lead",
                    "confidence": 0.75,
                    "details": "Potential business opportunity detected",
                    "keywords": ["proposal", "opportunity"],
                }
            ]
        else:
            opportunities = []

        # Store the detected opportunities
        query = """
        UPDATE email_content
        SET business_opportunities = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE email_id = ?
        """
        params = [json.dumps(opportunities), email_id]
        execute_query(conn, query, params)

        return opportunities

    def _calculate_priority(
        self,
        conn: duckdb.DuckDBPyConnection,
        email_id: str,
        from_address: str,
        subject: str,
        contact_info: dict[str, Any],
        opportunities: list[dict[str, Any]],
    ) -> tuple[float, float, str]:
        """Calculate priority score for an email.

        Args:
            conn: Database connection
            email_id: ID of the email
            from_address: Sender's email address
            subject: Email subject
            contact_info: Extracted contact information
            opportunities: Detected business opportunities

        Returns:
            Tuple of (priority_score, confidence, reason)

        """
        # Simple priority logic - in a real implementation, this would be more sophisticated
        priority = 0.0
        confidence = 0.5
        reason = "Default priority"

        # Check if it's from an important domain
        important_domains = ["gmail.com", "example.com"]
        sender_domain = from_address.split("@")[-1] if from_address else ""

        if sender_domain in important_domains:
            priority += 0.2
            reason = f"Sender from important domain: {sender_domain}"
            confidence = 0.7

        # Check for business opportunities
        if opportunities:
            priority += 0.4
            reason = "Business opportunity detected"
            confidence = 0.8

        # Check for contact information
        if contact_info:
            priority += 0.2
            if "company" in contact_info:
                reason = f"Contact from {contact_info['company']}"
                confidence = 0.75

        # Check for urgent keywords in subject
        urgent_keywords = ["urgent", "important", "asap", "deadline"]
        if subject and any(keyword in subject.lower() for keyword in urgent_keywords):
            priority += 0.3
            reason = "Urgent subject"
            confidence = 0.9

        # Normalize priority score
        priority = min(1.0, priority)

        return priority, confidence, reason

    def _update_enrichment_status(
        self,
        conn: duckdb.DuckDBPyConnection,
        email_id: str,
        priority_score: float,
        priority_reason: str,
        priority_confidence: float,
        contact_info_enriched: bool,
        opportunity_detected: bool,
        status: str = "completed",
    ) -> None:
        """Update the enrichment status for an email.

        Args:
            conn: Database connection
            email_id: ID of the email
            priority_score: Calculated priority score
            priority_reason: Reason for the priority score
            priority_confidence: Confidence in the priority score
            contact_info_enriched: Whether contact info was extracted
            opportunity_detected: Whether business opportunities were detected
            status: Status of the enrichment process

        """
        # Check if record exists first
        check_query = """
        SELECT 1 FROM email_enrichment_status WHERE email_id = ? LIMIT 1
        """
        exists = fetch_one(conn, check_query, [email_id])

        if exists:
            # Update existing record
            query = """
            UPDATE email_enrichment_status SET
                status = ?,
                priority_score = ?,
                priority_reason = ?,
                priority_confidence = ?,
                body_enriched = ?,
                contact_info_enriched = ?,
                opportunity_detected = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE email_id = ?
            """
            params = [
                status,
                priority_score,
                priority_reason,
                priority_confidence,
                True,
                contact_info_enriched,
                opportunity_detected,
                email_id,
            ]
        else:
            # Insert new record
            query = """
            INSERT INTO email_enrichment_status (
                email_id, status, priority_score, priority_reason, priority_confidence,
                body_enriched, contact_info_enriched, opportunity_detected, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            params = [
                email_id,
                status,
                priority_score,
                priority_reason,
                priority_confidence,
                True,
                contact_info_enriched,
                opportunity_detected,
            ]

        execute_query(conn, query, params)

    def enrich_email(self, email_id: str) -> bool:
        """Enrich a single email with additional metadata and analysis.

        Args:
            email_id: The email ID to enrich

        Returns:
            True if enrichment was successful, False otherwise

        """
        try:
            self.logger.info(f"Enriching single email: {email_id}")

            with self._get_connection() as conn:
                # Check if this email has already been enriched
                status = conn.execute(
                    "SELECT status FROM email_enrichment_status WHERE email_id = ?",
                    [email_id],
                ).fetchone()

                if status and status[0] == "completed":
                    self.logger.info(
                        f"Email {email_id} already fully enriched, skipping"
                    )
                    return True

                # Fetch email body
                plain_body, html_body = self._fetch_email_body(conn, email_id)

                if not plain_body and not html_body:
                    self.logger.warning(f"No email body found for {email_id}")
                    self._update_enrichment_status(
                        conn,
                        email_id,
                        0,
                        "No email body found",
                        0,
                        False,
                        False,
                        "failed",
                    )
                    return False

                # Extract contact information
                contact_info = self._extract_contact_info(conn, email_id)

                # Detect opportunities
                opportunities = self._detect_opportunities(conn, email_id)

                # Get email metadata
                from_address = ""
                subject = ""
                try:
                    email_data = conn.execute(
                        "SELECT from_address, subject FROM raw_emails WHERE message_id = ?",
                        [email_id],
                    ).fetchone()

                    if email_data:
                        from_address = email_data[0]
                        subject = email_data[1]
                except Exception:
                    self.logger.warning(f"No metadata found for email {email_id}")

                # Calculate priority
                priority_score, priority_confidence, priority_reason = (
                    self._calculate_priority(
                        conn,
                        email_id,
                        from_address,
                        subject,
                        contact_info,
                        opportunities,
                    )
                )

                # Update enrichment status
                self._update_enrichment_status(
                    conn,
                    email_id,
                    priority_score,
                    priority_reason,
                    priority_confidence,
                    bool(contact_info),
                    bool(opportunities),
                )

                self.logger.info(f"Successfully enriched email {email_id}")
                return True

        except Exception as e:
            self.logger.error(f"Error enriching email {email_id}: {e}", exc_info=True)

            # Try to update status to indicate failure
            try:
                with self._get_connection() as conn:
                    self._update_enrichment_status(
                        conn, email_id, 0, f"Error: {str(e)}", 0, False, False, "failed"
                    )
            except:
                pass

            return False


class ConnectionManager:
    """Context manager for database connections."""

    def __init__(self, enrichment):
        self.enrichment = enrichment
        self.connection = None
        self.created_new = False

    def __enter__(self):
        # If connection exists and is open, use it
        if self.enrichment.connection is not None and not getattr(
            self.enrichment.connection, "closed", False
        ):
            self.connection = self.enrichment.connection
            self.created_new = False
        else:
            # Use MotherDuck token if available
            config = None
            if self.enrichment.motherduck_token and self.enrichment.db_path.startswith(
                "md:"
            ):
                config = {"motherduck_token": self.enrichment.motherduck_token}
                self.enrichment.logger.debug(
                    f"Connecting to MotherDuck database: {self.enrichment.db_path}"
                )
            else:
                self.enrichment.logger.debug(
                    f"Connecting to local database: {self.enrichment.db_path}"
                )

            # Create new connection
            self.connection = duckdb.connect(self.enrichment.db_path, config=config)
            self.enrichment.connection = self.connection
            self.created_new = True
            self.enrichment.logger.debug("Database connection established")

        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close connection only if we created a new one
        if self.created_new and self.connection is not None:
            try:
                self.connection.close()
                self.enrichment.connection = None
                self.enrichment.logger.debug("Database connection closed")
            except Exception as e:
                self.enrichment.logger.warning(
                    f"Error closing database connection: {e}"
                )


if __name__ == "__main__":
    """Run the email enrichment process."""
    enrichment = EmailEnrichment()
    enrichment.execute()
