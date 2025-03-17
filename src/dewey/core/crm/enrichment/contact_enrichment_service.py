"""Contact enrichment service for the Dewey CRM system.

This module provides functionality to extract and enrich contact information from emails:
1. Extracts contact details from email signatures and content
2. Stores contact information in the database
3. Tracks enrichment tasks and their status
4. Provides confidence scoring for extracted data

The contact enrichment process is designed to be:
- Reliable: Uses regex patterns for consistent extraction
- Incremental: Processes emails in batches
- Auditable: Tracks enrichment sources and confidence
- Extensible: Supports multiple data sources
"""

from __future__ import annotations

import json
import re
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import structlog

from src.dewey.core.db import get_duckdb_connection

logger = structlog.get_logger(__name__)


class ContactEnrichmentService:
    """Service for extracting and enriching contact information from emails."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize the contact enrichment service.
        
        Args:
            config_dir: Directory containing configuration files.
                       If None, uses the default config directory.
        """
        self.config_dir = config_dir or Path(os.path.expanduser("~/dewey/config/contact"))
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.patterns = self._load_patterns()
        self.logger = logger.bind(service="contact_enrichment")

    def _load_patterns(self) -> Dict[str, str]:
        """Load regex patterns for contact information extraction.
        
        Returns:
            A dictionary of regex patterns for different contact fields
        """
        patterns_file = self.config_dir / "contact_patterns.json"
        
        # Default patterns
        default_patterns = {
            "name": r"(?:^|\n)([A-Z][a-z]+(?: [A-Z][a-z]+)+)(?:\n|$)",
            "job_title": r"(?:^|\n)([A-Za-z]+(?:\s+[A-Za-z]+){0,3}?)(?:\s+at\s+|\s*[,|]\s*)",
            "company": r"(?:at|@|with)\s+([A-Z][A-Za-z0-9\s&]+(?:Inc|LLC|Ltd|Co|Corp|Corporation|Company))",
            "phone": r"(?:Phone|Tel|Mobile|Cell)(?::|.)?(?:\s+)?((?:\+\d{1,3}[-\.\s]?)?(?:\(?\d{3}\)?[-\.\s]?)?\d{3}[-\.\s]?\d{4})",
            "linkedin_url": r"(?:LinkedIn|Profile)(?::|.)?(?:\s+)?(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)"
        }
        
        # Create default patterns file if it doesn't exist
        if not patterns_file.exists():
            with open(patterns_file, 'w') as f:
                json.dump(default_patterns, f, indent=2)
            return default_patterns
            
        # Load patterns from file
        try:
            with open(patterns_file) as f:
                return json.load(f)
        except Exception as e:
            self.logger.exception(
                "Failed to load contact patterns",
                error=str(e),
                error_type=type(e).__name__,
            )
            return default_patterns

    def extract_contact_info(self, message_text: str) -> Optional[Dict[str, Any]]:
        """Extract contact information from email message text using regex patterns.
        
        Args:
            message_text: Raw text content of the email message
            
        Returns:
            Dictionary containing extracted contact information or None if insufficient data
        """
        if not message_text:
            self.logger.warning("Empty message text provided")
            return None

        self.logger.debug(f"Processing message of length {len(message_text)}")

        # Initialize result dictionary with default values
        info = {
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
                pattern = re.compile(pattern_str, re.MULTILINE)
                match = pattern.search(message_text)
                if match:
                    # Extract value from the first matching group
                    value = match.group(1).strip()
                    info[field] = value
                    self.logger.debug(f"Found {field}: {value}")
                else:
                    self.logger.debug(f"No match for {field}")

            # Calculate confidence score based on number of fields found
            found_fields = sum(1 for v in info.values() if v is not None)
            info["confidence"] = found_fields / (len(info) - 1)  # -1 for confidence field

            self.logger.info(
                f"Extraction completed with confidence {info['confidence']}",
            )

            # Return results only if we found at least 2 valid fields
            if found_fields >= 2:
                return info
            self.logger.warning("Insufficient fields found (need at least 2)")
            return None

        except Exception as e:
            self.logger.exception(
                f"Error extracting contact info: {e!s}",
                exc_info=True,
            )
            return None

    def store_contact(self, contact_info: Dict[str, Any], email_id: str, from_email: str) -> bool:
        """Store contact information in the database.
        
        Args:
            contact_info: Dictionary containing contact information
            email_id: ID of the email from which the contact was extracted
            from_email: Email address of the contact
            
        Returns:
            True if the contact was stored successfully, False otherwise
        """
        try:
            with get_duckdb_connection() as conn:
                # Create contacts table if it doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY,
                        email VARCHAR UNIQUE,
                        name VARCHAR,
                        job_title VARCHAR,
                        company VARCHAR,
                        phone VARCHAR,
                        linkedin_url VARCHAR,
                        confidence FLOAT,
                        source VARCHAR,
                        source_id VARCHAR,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create enrichment_sources table if it doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS enrichment_sources (
                        id VARCHAR PRIMARY KEY,
                        entity_type VARCHAR,
                        entity_id VARCHAR,
                        source_type VARCHAR,
                        data VARCHAR,
                        confidence FLOAT,
                        valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        valid_to TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Generate a unique source ID
                source_id = str(uuid.uuid4())
                
                # Mark previous sources as invalid
                conn.execute("""
                    UPDATE enrichment_sources
                    SET valid_to = CURRENT_TIMESTAMP
                    WHERE entity_type = 'contact'
                    AND entity_id = ?
                    AND source_type = 'email_signature'
                    AND valid_to IS NULL
                """, (from_email,))
                
                # Store new enrichment source
                conn.execute("""
                    INSERT INTO enrichment_sources (
                        id, entity_type, entity_id, source_type, data, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    source_id,
                    "contact",
                    from_email,
                    "email_signature",
                    json.dumps(contact_info),
                    contact_info["confidence"]
                ))
                
                # Check if contact already exists
                result = conn.execute("""
                    SELECT id FROM contacts WHERE email = ?
                """, (from_email,)).fetchone()
                
                if result:
                    # Update existing contact
                    conn.execute("""
                        UPDATE contacts
                        SET name = COALESCE(?, name),
                            job_title = COALESCE(?, job_title),
                            company = COALESCE(?, company),
                            phone = COALESCE(?, phone),
                            linkedin_url = COALESCE(?, linkedin_url),
                            confidence = ?,
                            source = 'email_signature',
                            source_id = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE email = ?
                    """, (
                        contact_info.get("name"),
                        contact_info.get("job_title"),
                        contact_info.get("company"),
                        contact_info.get("phone"),
                        contact_info.get("linkedin_url"),
                        contact_info["confidence"],
                        source_id,
                        from_email
                    ))
                    self.logger.info(f"Updated contact record for {from_email}")
                else:
                    # Insert new contact
                    conn.execute("""
                        INSERT INTO contacts (
                            email, name, job_title, company, phone, linkedin_url,
                            confidence, source, source_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        from_email,
                        contact_info.get("name"),
                        contact_info.get("job_title"),
                        contact_info.get("company"),
                        contact_info.get("phone"),
                        contact_info.get("linkedin_url"),
                        contact_info["confidence"],
                        "email_signature",
                        source_id
                    ))
                    self.logger.info(f"Created new contact record for {from_email}")
                
                # Log enrichment activity
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS activity_log (
                        id INTEGER PRIMARY KEY,
                        entity_type VARCHAR,
                        entity_id VARCHAR,
                        activity_type VARCHAR,
                        details VARCHAR,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    INSERT INTO activity_log (
                        entity_type, entity_id, activity_type, details
                    ) VALUES (?, ?, ?, ?)
                """, (
                    "contact",
                    from_email,
                    "enrichment",
                    json.dumps({
                        "email_id": email_id,
                        "source": "email_signature",
                        "confidence": contact_info["confidence"],
                        "fields_found": sum(1 for v in contact_info.values() if v is not None) - 1  # -1 for confidence
                    })
                ))
                
                return True
                
        except Exception as e:
            self.logger.exception(
                "Failed to store contact",
                email=from_email,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def process_email(self, email_id: str) -> bool:
        """Process a single email for contact enrichment.
        
        Args:
            email_id: ID of the email to process
            
        Returns:
            True if contact information was extracted and stored, False otherwise
        """
        try:
            self.logger.info(f"Processing email {email_id} for contact enrichment")
            
            # Get email data from database
            with get_duckdb_connection() as conn:
                result = conn.execute("""
                    SELECT id, from_email, from_name, plain_body
                    FROM emails
                    WHERE id = ?
                """, (email_id,)).fetchone()
                
                if not result:
                    self.logger.warning(f"Email {email_id} not found")
                    return False
                
                db_id, from_email, from_name, plain_body = result
                
                if not plain_body:
                    self.logger.warning(f"Email {email_id} has no plain body text")
                    return False
                
                # Extract contact information
                contact_info = self.extract_contact_info(plain_body)
                
                if contact_info:
                    # Store contact information
                    if self.store_contact(contact_info, email_id, from_email):
                        self.logger.info(
                            "Contact enrichment successful",
                            email_id=email_id,
                            from_email=from_email,
                            confidence=contact_info["confidence"]
                        )
                        return True
                    else:
                        self.logger.warning(
                            "Failed to store contact information",
                            email_id=email_id,
                            from_email=from_email
                        )
                        return False
                else:
                    self.logger.info(
                        "No contact information found",
                        email_id=email_id,
                        from_email=from_email
                    )
                    return False
                
        except Exception as e:
            self.logger.exception(
                "Contact enrichment failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


def enrich_contacts(batch_size: int = 50) -> int:
    """Process a batch of emails for contact enrichment.
    
    Args:
        batch_size: Number of emails to process in this batch
        
    Returns:
        Number of contacts successfully enriched
    """
    enrichment_service = ContactEnrichmentService()
    logger.info("Starting contact enrichment batch", batch_size=batch_size)
    
    try:
        with get_duckdb_connection() as conn:
            # Create a table to track processed emails if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    email_id VARCHAR PRIMARY KEY,
                    process_type VARCHAR,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Get emails that haven't been processed for contact enrichment yet
            result = conn.execute("""
                SELECT e.id, e.from_email
                FROM emails e
                LEFT JOIN processed_emails p ON e.id = p.email_id AND p.process_type = 'contact_enrichment'
                WHERE p.email_id IS NULL
                AND e.plain_body IS NOT NULL
                LIMIT ?
            """, (batch_size,)).fetchall()
            
            if not result:
                logger.info("No emails to process for contact enrichment")
                return 0
                
            logger.info(f"Found {len(result)} emails to process for contact enrichment")
            
            success_count = 0
            for row in result:
                email_id, from_email = row
                
                try:
                    success = enrichment_service.process_email(email_id)
                    
                    # Mark email as processed regardless of success
                    conn.execute("""
                        INSERT INTO processed_emails (email_id, process_type)
                        VALUES (?, ?)
                    """, (email_id, "contact_enrichment"))
                    
                    if success:
                        success_count += 1
                except Exception as e:
                    logger.exception(
                        "Contact enrichment failed",
                        email_id=email_id,
                        from_email=from_email,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
            
            logger.info(
                "Completed contact enrichment batch",
                processed=len(result),
                successful=success_count
            )
            return success_count
            
    except Exception as e:
        logger.exception(
            "Contact enrichment batch failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich contacts from emails in the database")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of emails to process")
    args = parser.parse_args()
    
    enrich_contacts(args.batch_size) 