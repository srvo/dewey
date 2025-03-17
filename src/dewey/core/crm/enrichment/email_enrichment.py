"""Email enrichment service for the Dewey CRM system.

This module provides functionality to enrich emails with:
1. Full message content extraction (plain text and HTML)
2. Priority scoring using the prioritization module
3. Contact information extraction
4. Opportunity detection

The enrichment process is designed to be:
- Incremental: Processes emails in batches
- Resilient: Handles errors gracefully
- Extensible: Supports adding new enrichment types
- Auditable: Logs all enrichment activities
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union

import structlog

from src.dewey.core.db import get_duckdb_connection
from src.dewey.core.crm.gmail.gmail_service import GmailService
from .prioritization import EmailPrioritizer

logger = structlog.get_logger(__name__)


class EmailEnrichmentService:
    """Service for enriching email metadata like message bodies and priorities."""

    def __init__(self) -> None:
        """Initialize the email enrichment service."""
        self.gmail_service = GmailService()
        self.prioritizer = EmailPrioritizer()
        self.logger = logger.bind(service="email_enrichment")

    def extract_message_bodies(self, message_data: Dict[str, Any]) -> Tuple[str, str]:
        """Extract plain and HTML message bodies from Gmail message data.
        
        Args:
            message_data: The full message data from Gmail API
            
        Returns:
            A tuple containing (plain_body, html_body)
        """
        plain_body = ""
        html_body = ""

        if "payload" in message_data:
            payload = message_data["payload"]

            # Handle simple messages (body directly in payload)
            if "body" in payload and "data" in payload["body"]:
                if payload.get("mimeType") == "text/plain":
                    plain_body = base64.urlsafe_b64decode(
                        payload["body"]["data"],
                    ).decode(errors="replace")
                elif payload.get("mimeType") == "text/html":
                    html_body = base64.urlsafe_b64decode(
                        payload["body"]["data"],
                    ).decode(errors="replace")

            # Handle multipart messages (body in parts)
            if "parts" in payload:
                for part in payload["parts"]:
                    if (
                        part.get("mimeType") == "text/plain"
                        and "body" in part
                        and "data" in part["body"]
                    ):
                        plain_body = base64.urlsafe_b64decode(
                            part["body"]["data"],
                        ).decode(errors="replace")
                    elif (
                        part.get("mimeType") == "text/html"
                        and "body" in part
                        and "data" in part["body"]
                    ):
                        html_body = base64.urlsafe_b64decode(
                            part["body"]["data"],
                        ).decode(errors="replace")

        return plain_body, html_body

    def extract_headers(self, message_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract relevant headers from Gmail message data.
        
        Args:
            message_data: The full message data from Gmail API
            
        Returns:
            A dictionary of header values
        """
        headers = {}
        
        if "payload" in message_data and "headers" in message_data["payload"]:
            for header in message_data["payload"]["headers"]:
                name = header.get("name", "").lower()
                value = header.get("value", "")
                
                if name in ["from", "to", "cc", "bcc", "subject", "date", "message-id", "in-reply-to", "references"]:
                    headers[name] = value
        
        return headers

    def enrich_email(self, email_id: str) -> bool:
        """Enrich an email with message body content and priority score.

        Args:
            email_id: The ID of the email to enrich

        Returns:
            bool: True if enrichment was successful
        """
        try:
            self.logger.info("Starting email enrichment", email_id=email_id)
            
            # Get email data from database
            with get_duckdb_connection() as conn:
                result = conn.execute(
                    """
                    SELECT id, gmail_id, subject, from_email, metadata
                    FROM emails
                    WHERE id = ?
                    """,
                    (email_id,)
                ).fetchone()
                
                if not result:
                    self.logger.warning("Email not found", email_id=email_id)
                    return False
                
                db_id, gmail_id, subject, from_email, metadata_str = result
                metadata = json.loads(metadata_str) if metadata_str else {}
            
            # Get full message data from Gmail API
            message_data = self.gmail_service.get_message(gmail_id)
            
            if not message_data:
                self.logger.warning("Failed to fetch message from Gmail", email_id=email_id, gmail_id=gmail_id)
                return False
            
            # Extract message content
            plain_body, html_body = self.extract_message_bodies(message_data)
            
            # Extract headers
            headers = self.extract_headers(message_data)
            
            # Prepare email data for prioritization
            email_data = {
                "id": email_id,
                "gmail_id": gmail_id,
                "subject": subject,
                "from_email": from_email,
                "plain_body": plain_body,
                "html_body": html_body,
                "headers": headers,
                "metadata": metadata
            }
            
            # Score the email with prioritization
            priority, confidence, reason = self.prioritizer.score_email(email_data)
            
            # Store enrichment results in database
            with get_duckdb_connection() as conn:
                # Update email with content and metadata
                conn.execute(
                    """
                    UPDATE emails
                    SET plain_body = ?,
                        html_body = ?,
                        priority = ?,
                        metadata = json_insert(
                            COALESCE(metadata, '{}'),
                            '$.priority_confidence', ?,
                            '$.priority_reason', ?,
                            '$.priority_updated_at', ?,
                            '$.enriched_at', ?,
                            '$.headers', ?
                        ),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        plain_body,
                        html_body,
                        priority,
                        confidence,
                        reason,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        json.dumps(headers),
                        email_id
                    )
                )
                
                # Store analysis result
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS email_analyses (
                        id INTEGER PRIMARY KEY,
                        email_id VARCHAR,
                        analysis_type VARCHAR,
                        priority INTEGER,
                        confidence FLOAT,
                        reason VARCHAR,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(email_id, analysis_type)
                    )
                    """
                )
                
                conn.execute(
                    """
                    INSERT OR REPLACE INTO email_analyses (
                        email_id, analysis_type, priority, confidence, reason
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (email_id, "priority", priority, confidence, reason)
                )
                
                # Log enrichment activity
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS activity_log (
                        id INTEGER PRIMARY KEY,
                        entity_type VARCHAR,
                        entity_id VARCHAR,
                        activity_type VARCHAR,
                        details VARCHAR,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                
                conn.execute(
                    """
                    INSERT INTO activity_log (
                        entity_type, entity_id, activity_type, details
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        "email",
                        email_id,
                        "enrichment",
                        json.dumps({
                            "plain_body_length": len(plain_body) if plain_body else 0,
                            "html_body_length": len(html_body) if html_body else 0,
                            "priority": priority,
                            "confidence": confidence,
                            "reason": reason
                        })
                    )
                )
            
            self.logger.info(
                "Email enriched successfully",
                email_id=email_id,
                gmail_id=gmail_id,
                priority=priority,
                confidence=confidence
            )
            return True

        except Exception as e:
            self.logger.exception(
                "Email enrichment failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


def enrich_emails(batch_size: int = 50) -> int:
    """Process a batch of emails for enrichment.
    
    Args:
        batch_size: Number of emails to process in this batch
        
    Returns:
        Number of emails successfully enriched
    """
    enrichment_service = EmailEnrichmentService()
    logger.info("Starting email enrichment batch", batch_size=batch_size)
    
    try:
        with get_duckdb_connection() as conn:
            # Get emails that haven't been enriched yet (no plain_body or html_body)
            result = conn.execute("""
                SELECT id
                FROM emails
                WHERE (plain_body IS NULL OR html_body IS NULL)
                AND gmail_id IS NOT NULL
                LIMIT ?
            """, (batch_size,)).fetchall()
            
            if not result:
                logger.info("No emails to enrich")
                return 0
                
            logger.info(f"Found {len(result)} emails to enrich")
            
            success_count = 0
            for row in result:
                email_id = row[0]
                
                try:
                    if enrichment_service.enrich_email(email_id):
                        success_count += 1
                except Exception as e:
                    logger.exception(
                        "Email enrichment failed",
                        email_id=email_id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
            
            logger.info(
                "Completed email enrichment batch",
                processed=len(result),
                successful=success_count
            )
            return success_count
            
    except Exception as e:
        logger.exception(
            "Email enrichment batch failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich emails in the database")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of emails to process")
    args = parser.parse_args()
    
    enrich_emails(args.batch_size) 