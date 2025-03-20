from __future__ import annotations

import json
import re
import uuid
import logging
from typing import Any, Dict, Optional

import yaml

from dewey.core.base_script import BaseScript
from dewey.utils.database import get_db_connection


class ContactEnrichment(BaseScript):
    """Contact Enrichment System with Task Tracking and Multiple Data Sources.

    This module provides comprehensive contact enrichment capabilities by:
    - Extracting contact information from email signatures and content
    - Managing enrichment tasks with status tracking
    - Storing enrichment results with confidence scoring
    - Integrating with multiple data sources
    - Providing detailed logging and error handling

    The system is designed to be:
    - Scalable: Processes emails in batches with configurable size
    - Reliable: Implements task tracking and retry mechanisms
    - Extensible: Supports adding new data sources and extraction patterns
    - Auditable: Maintains detailed logs and task history

    Key Features:
    - Regex-based contact information extraction
    - Task management system with status tracking
    - Confidence scoring for extracted data
    - Source versioning and validation
    - Comprehensive logging and error handling
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the ContactEnrichment module."""
        super().__init__(*args, **kwargs)
        self.patterns: Dict[str, str] = self.get_config_value("regex_patterns")["contact_info"]
        self.enrichment_batch_size: int = self.get_config_value("enrichment_batch_size")

    def run(self, batch_size: Optional[int] = None) -> None:
        """Runs the contact enrichment process.

        Args:
            batch_size: Number of emails to process in this batch. If None, uses default from config.
        """
        self.enrich_contacts(batch_size)

    def create_enrichment_task(
        self,
        conn,
        entity_type: str,
        entity_id: str,
        task_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new enrichment task in the database.

        Args:
            conn: Database connection object.
            entity_type: Type of entity being enriched (e.g., 'email', 'contact').
            entity_id: Unique identifier for the entity.
            task_type: Type of enrichment task (e.g., 'contact_info').
            metadata: Optional dictionary of task metadata.

        Returns:
            Unique task ID (UUID).

        Raises:
            Exception: If database operation fails.

        Example:
            task_id = self.create_enrichment_task(
                conn,
                entity_type="email",
                entity_id="12345",
                task_type="contact_info",
                metadata={"source": "email_signature"}
            )
        """
        task_id = str(uuid.uuid4())
        cursor = conn.cursor()

        self.logger.info(f"[TASK] Creating new {task_type} task for {entity_type}:{entity_id}")
        self.logger.debug(f"[TASK] Task metadata: {json.dumps(metadata or {})}")

        try:
            # Insert new task record with initial status 'pending'
            cursor.execute(
                """
                INSERT INTO enrichment_tasks (
                    id, entity_type, entity_id, task_type, status, metadata
                ) VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (task_id, entity_type, entity_id, task_type, json.dumps(metadata or {})),
            )

            self.logger.info(f"[TASK] Created task {task_id}")
            return task_id
        except Exception as e:
            self.logger.error(f"[TASK] Failed to create task: {e!s}", exc_info=True)
            raise

    def update_task_status(
        self,
        conn,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update the status and details of an enrichment task.

        Args:
            conn: Database connection object.
            task_id: Unique identifier of the task to update.
            status: New status for the task (e.g., 'completed', 'failed').
            result: Optional dictionary of task results.
            error: Optional error message if task failed.

        Raises:
            Exception: If database operation fails.

        Notes:
            - Increments the attempt counter on each update.
            - Updates timestamps for last attempt and modification.
            - Maintains both success results and error messages.

        Example:
            self.update_task_status(
                conn,
                task_id="12345",
                status="completed",
                result={"name": "John Doe", "company": "ACME Inc"},
                error=None
            )
        """
        cursor = conn.cursor()

        self.logger.info(f"[TASK] Updating task {task_id} to status: {status}")
        if result:
            self.logger.debug(f"[TASK] Task result: {json.dumps(result)}")
        if error:
            self.logger.warning(f"[TASK] Task error: {error}")

        try:
            # Update task record with new status and results
            cursor.execute(
                """
                UPDATE enrichment_tasks
                SET status = ?,
                    attempts = attempts + 1,
                    last_attempt = CURRENT_TIMESTAMP,
                    result = ?,
                    error_message = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, json.dumps(result or {}), error, task_id),
            )

            if cursor.rowcount == 0:
                self.logger.error(f"[TASK] Task {task_id} not found for status update")
            else:
                self.logger.debug(f"[TASK] Successfully updated task {task_id}")

        except Exception as e:
            self.logger.error(f"[TASK] Failed to update task status: {e!s}", exc_info=True)
            raise

    def store_enrichment_source(
        self,
        conn,
        source_type: str,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any],
        confidence: float,
    ) -> str:
        """Store enrichment data from a specific source with version control.

        Args:
            conn: Database connection object.
            source_type: Type of enrichment source (e.g., 'email_signature').
            entity_type: Type of entity being enriched (e.g., 'contact').
            entity_id: Unique identifier for the entity.
            data: Dictionary of enrichment data.
            confidence: Confidence score (0.0 to 1.0) for the data quality.

        Returns:
            Unique source ID (UUID).

        Raises:
            Exception: If database operation fails.

        Notes:
            - Implements version control by marking previous sources as invalid.
            - Maintains a complete history of enrichment sources.
            - Supports multiple sources for the same entity.

        Example:
            source_id = self.store_enrichment_source(
                conn,
                source_type="email_signature",
                entity_type="contact",
                entity_id="12345",
                data={"name": "John Doe", "company": "ACME Inc"},
                confidence=0.85
            )
        """
        source_id = str(uuid.uuid4())
        cursor = conn.cursor()

        self.logger.info(f"[SOURCE] Storing {source_type} data for {entity_type}:{entity_id}")
        self.logger.debug(f"[SOURCE] Data: {json.dumps(data)}, Confidence: {confidence}")

        try:
            # Mark previous source as invalid by setting valid_to timestamp
            cursor.execute(
                """
                UPDATE enrichment_sources
                SET valid_to = CURRENT_TIMESTAMP
                WHERE entity_type = ? AND entity_id = ? AND source_type = ? AND valid_to IS NULL
                """,
                (entity_type, entity_id, source_type),
            )

            if cursor.rowcount > 0:
                self.logger.info(
                    f"[SOURCE] Marked {cursor.rowcount} previous sources as invalid",
                )

            # Insert new source with current timestamp
            cursor.execute(
                """
                INSERT INTO enrichment_sources (
                    id, source_type, entity_type, entity_id,
                    data, confidence, valid_from
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    source_id,
                    source_type,
                    entity_type,
                    entity_id,
                    json.dumps(data),
                    confidence,
                ),
            )

            self.logger.info(f"[SOURCE] Successfully stored source {source_id}")
            return source_id
        except Exception as e:
            self.logger.error(f"[SOURCE] Failed to store source: {e!s}", exc_info=True)
            raise

    def extract_contact_info(self, message_text: str) -> Optional[Dict[str, Any]]:
        r"""Extract contact information from email message text using regex patterns.

        Args:
            message_text: Raw text content of the email message.

        Returns:
            Dictionary containing extracted contact information with keys:
                - name: Full name
                - job_title: Job title
                - company: Company name
                - phone: Phone number
                - linkedin_url: LinkedIn profile URL
                - confidence: Confidence score (0.0 to 1.0)
            Returns None if insufficient information is found.

        Notes:
            - Uses predefined regex patterns to extract information.
            - Calculates confidence score based on number of fields found.
            - Requires at least 2 valid fields to return results.
            - Handles various text formats and edge cases.

        Example:
            info = self.extract_contact_info("John Doe\nCEO at ACME Inc\nPhone: 555-1234")
            # Returns: {
            #     "name": "John Doe",
            #     "job_title": "CEO",
            #     "company": "ACME Inc",
            #     "phone": "555-1234",
            #     "linkedin_url": None,
            #     "confidence": 0.75
            # }
        """
        if not message_text:
            self.logger.warning("[EXTRACT] Empty message text provided")
            return None

        self.logger.debug(f"[EXTRACT] Processing message of length {len(message_text)}")

        # Initialize result dictionary with default values
        info: Dict[str, Any] = {
            "name": None,
            "job_title": None,
            "company": None,
            "phone": None,
            "linkedin_url": None,
            "confidence": 0.0,
        }

        try:
            # Apply each regex pattern to extract information
            for field, pattern_str in self.patterns.items():
                pattern = re.compile(pattern_str)
                match = re.search(pattern, message_text)
                if match:
                    # Extract value from the first matching group
                    value = match.group(1).strip()
                    info[field] = value
                    self.logger.debug(f"[EXTRACT] Found {field}: {value}")
                else:
                    self.logger.debug(f"[EXTRACT] No match for {field}")

            # Calculate confidence score based on number of fields found
            found_fields = sum(1 for v in info.values() if v is not None)
            info["confidence"] = found_fields / (len(info) - 1)  # -1 for confidence field

            self.logger.info(
                f"[EXTRACT] Extraction completed with confidence {info['confidence']}",
            )
            self.logger.debug(f"[EXTRACT] Extracted info: {json.dumps(info)}")

            # Return results only if we found at least 2 valid fields
            if found_fields >= 2:
                return info
            self.logger.warning("[EXTRACT] Insufficient fields found (need at least 2)")
            return None

        except Exception as e:
            self.logger.error(
                f"[EXTRACT] Error extracting contact info: {e!s}",
                exc_info=True,
            )
            return None

    def process_email_for_enrichment(self, conn, email_id: str) -> bool:
        """Process a single email for contact enrichment.

        Args:
            conn: Database connection object.
            email_id: Unique identifier of the email to process.

        Returns:
            True if enrichment was successful, False otherwise.

        Notes:
            - Retrieves email content from database.
            - Creates enrichment task for tracking.
            - Extracts contact information from email body.
            - Updates contact record with new information.
            - Maintains task status and error handling.

        Workflow:
            1. Retrieve email content from database.
            2. Create enrichment task.
            3. Extract contact information.
            4. Store enrichment source.
            5. Update contact record.
            6. Update task status.

        Example:
            success = self.process_email_for_enrichment(conn, "email_12345")
        """
        self.logger.info(f"[PROCESS] Starting enrichment for email {email_id}")
        cursor = conn.cursor()

        try:
            # Retrieve email content from database
            cursor.execute(
                """
                SELECT id, from_email, from_name, plain_body, html_body
                FROM raw_emails WHERE id = ?
                """,
                (email_id,),
            )

            result = cursor.fetchone()
            if not result:
                self.logger.error(f"[PROCESS] Email {email_id} not found")
                return False

            email_id, from_email, from_name, plain_body, html_body = result
            self.logger.info(f"[PROCESS] Processing email from {from_email} ({from_name})")

            # Create enrichment task for tracking
            task_id = self.create_enrichment_task(
                conn,
                "email",
                email_id,
                "contact_info",
                {"from_email": from_email},
            )

            try:
                # Extract contact information from plain text body
                self.logger.info("[PROCESS] Attempting contact info extraction")
                contact_info = self.extract_contact_info(plain_body or "")

                if contact_info:
                    self.logger.info("[PROCESS] Contact info found, storing enrichment source")
                    # Store extracted information as enrichment source
                    self.store_enrichment_source(
                        conn,
                        "email_signature",
                        "contact",
                        from_email,
                        contact_info,
                        contact_info["confidence"],
                    )

                    self.logger.info("[PROCESS] Updating contact record")
                    # Update contact record with new information
                    cursor.execute(
                        """
                        UPDATE contacts
                        SET name = COALESCE(?, name),
                            job_title = COALESCE(?, job_title),
                            company = COALESCE(?, company),
                            phone = COALESCE(?, phone),
                            linkedin_url = COALESCE(?, linkedin_url),
                            enrichment_status = 'enriched',
                            last_enriched = CURRENT_TIMESTAMP,
                            enrichment_source = 'email_signature',
                            confidence_score = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE email = ?
                        """,
                        (
                            contact_info.get("name"),
                            contact_info.get("job_title"),
                            contact_info.get("company"),
                            contact_info.get("phone"),
                            contact_info.get("linkedin_url"),
                            contact_info["confidence"],
                            from_email,
                        ),
                    )

                    if cursor.rowcount == 0:
                        self.logger.warning(
                            f"[PROCESS] No contact record found for {from_email}",
                        )
                    else:
                        self.logger.info(f"[PROCESS] Updated contact record for {from_email}")

                    # Update task status to completed
                    self.update_task_status(conn, task_id, "completed", contact_info)
                    return True

                self.logger.info("[PROCESS] No contact info found in email")
                self.update_task_status(
                    conn,
                    task_id,
                    "skipped",
                    {"reason": "No contact info found"},
                )
                return False

            except Exception as e:
                self.logger.error(
                    f"[PROCESS] Error processing email {email_id}: {e!s}",
                    exc_info=True,
                )
                self.update_task_status(conn, task_id, "failed", error=str(e))
                return False

        except Exception as e:
            self.logger.error(
                f"[PROCESS] Fatal error processing email {email_id}: {e!s}",
                exc_info=True,
            )
            return False

    def enrich_contacts(self, batch_size: Optional[int] = None) -> None:
        """Process a batch of emails for contact enrichment.

        Args:
            batch_size: Number of emails to process in this batch. If None, uses default from config.

        Notes:
            - Processes emails in batches for better performance and resource management.
            - Only processes emails that haven't been enriched before.
            - Tracks success rate and provides detailed logging.
            - Uses database transactions for atomic operations.

        Workflow:
            1. Get batch of unprocessed emails.
            2. Process each email individually.
            3. Track success/failure statistics.
            4. Log results and handle errors.

        Example:
            self.enrich_contacts(batch_size=100)  # Process 100 emails
        """
        batch_size = batch_size or self.enrichment_batch_size

        self.logger.info(f"[BATCH] Starting contact enrichment batch (size={batch_size})")

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Get batch of unprocessed emails
                self.logger.info("[BATCH] Querying for unprocessed emails")
                cursor.execute(
                    """
                    SELECT e.id
                    FROM raw_emails e
                    LEFT JOIN enrichment_tasks t ON
                        t.entity_type = 'email' AND
                        t.entity_id = e.id AND
                        t.task_type = 'contact_info'
                    WHERE t.id IS NULL
                    LIMIT ?
                    """,
                    (batch_size,),
                )

                email_ids = [row[0] for row in cursor.fetchall()]

                if not email_ids:
                    self.logger.info("[BATCH] No new emails to process")
                    return

                self.logger.info(f"[BATCH] Found {len(email_ids)} emails to process")

                # Process each email in the batch
                success_count = 0
                for i, email_id in enumerate(email_ids, 1):
                    self.logger.info(f"[BATCH] Processing email {i}/{len(email_ids)}")
                    if self.process_email_for_enrichment(conn, email_id):
                        success_count += 1

                # Log batch completion statistics
                self.logger.info(
                    f"[BATCH] Enrichment completed. Processed {len(email_ids)} emails, {success_count} successful",
                )

        except Exception as e:
            self.logger.error(
                f"[BATCH] Fatal error in enrichment batch: {e!s}",
                exc_info=True,
            )
            raise
