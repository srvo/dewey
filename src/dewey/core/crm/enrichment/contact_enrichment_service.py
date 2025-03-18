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
from dewey.utils import get_logger
from dewey.core.engines import MotherDuckEngine

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


def enrich_contacts(engine, dedup_strategy='update'):
    """Enrich contact data with additional information."""
    # Extract company information from email domains
    engine.execute_query("""
        UPDATE contacts c
        SET company = CASE 
            WHEN email LIKE '%@%' THEN 
                REGEXP_REPLACE(SPLIT_PART(email, '@', 2), '\..*$', '')
            ELSE NULL
        END
        WHERE company IS NULL
    """)
    
    # Extract job titles
    engine.execute_query("""
        UPDATE contacts c
        SET job_title = llm_extract_job_title(email_signature)
        WHERE job_title IS NULL AND email_signature IS NOT NULL
    """)
    
    # Extract phone numbers
    engine.execute_query("""
        UPDATE contacts c
        SET phone = llm_extract_phone(email_signature)
        WHERE phone IS NULL AND email_signature IS NOT NULL
    """)
    
    # Extract LinkedIn profiles
    engine.execute_query("""
        UPDATE contacts c
        SET linkedin = llm_extract_linkedin(email_signature)
        WHERE linkedin IS NULL AND email_signature IS NOT NULL
    """)
    
    # Consolidate company information
    engine.execute_query("""
        UPDATE contacts c
        SET company_id = co.id
        FROM companies co
        WHERE c.company = co.name
        AND c.company_id IS NULL
    """)

def main():
    parser = argparse.ArgumentParser(description='Enrich contact data with additional information')
    parser.add_argument('--target_db', help='Target database name', default='dewey')
    parser.add_argument('--dedup_strategy', choices=['none', 'update', 'ignore'], default='update',
                       help='Deduplication strategy: none, update, or ignore')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('contact_enrichment', log_dir)

    try:
        engine = MotherDuckEngine(args.target_db)
        
        logger.info("Starting contact enrichment process")
        
        # Get initial counts
        contact_count = engine.execute_query("SELECT COUNT(*) FROM contacts").fetchone()[0]
        enriched_count = engine.execute_query("""
            SELECT COUNT(*) FROM contacts 
            WHERE company IS NOT NULL 
            AND job_title IS NOT NULL 
            AND phone IS NOT NULL 
            AND linkedin IS NOT NULL
            AND company_id IS NOT NULL
        """).fetchone()[0]
        
        logger.info(f"Total contacts: {contact_count}")
        logger.info(f"Already enriched: {enriched_count}")
        logger.info(f"Contacts to process: {contact_count - enriched_count}")
        
        # Perform enrichment
        enrich_contacts(engine, args.dedup_strategy)
        
        # Get final counts
        final_enriched = engine.execute_query("""
            SELECT COUNT(*) FROM contacts 
            WHERE company IS NOT NULL 
            AND job_title IS NOT NULL 
            AND phone IS NOT NULL 
            AND linkedin IS NOT NULL
            AND company_id IS NOT NULL
        """).fetchone()[0]
        
        logger.info("\nEnrichment completed:")
        logger.info(f"Total contacts processed: {contact_count}")
        logger.info(f"Newly enriched: {final_enriched - enriched_count}")
        logger.info(f"Total enriched: {final_enriched}")
        
    except Exception as e:
        logger.error(f"Error during contact enrichment: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if 'engine' in locals():
            engine.close()

if __name__ == '__main__':
    main() 