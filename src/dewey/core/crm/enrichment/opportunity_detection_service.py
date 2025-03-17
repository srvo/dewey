"""Opportunity detection service for the Dewey CRM system.

This module provides functionality to detect business opportunities in emails:
1. Uses regex patterns to identify different opportunity types
2. Processes emails in batches for efficiency
3. Updates contact records with opportunity flags
4. Logs detection activities for auditing

The opportunity detection process is designed to be:
- Accurate: Uses carefully crafted regex patterns
- Efficient: Processes emails in batches
- Configurable: Loads patterns from configuration files
- Extensible: Supports adding new opportunity types
"""

from __future__ import annotations

import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import structlog

from src.dewey.core.db import get_duckdb_connection

logger = structlog.get_logger(__name__)


class OpportunityDetectionService:
    """Service for detecting business opportunities in emails."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize the opportunity detection service.
        
        Args:
            config_dir: Directory containing configuration files.
                       If None, uses the default config directory.
        """
        self.config_dir = config_dir or Path(os.path.expanduser("~/dewey/config/opportunity"))
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.patterns = self._load_patterns()
        self.logger = logger.bind(service="opportunity_detection")

    def _load_patterns(self) -> Dict[str, str]:
        """Load regex patterns for opportunity detection.
        
        Returns:
            A dictionary of regex patterns for different opportunity types
        """
        patterns_file = self.config_dir / "opportunity_patterns.json"
        
        # Default patterns
        default_patterns = {
            "demo_request": r"(?i)(?:would like|interested in|request|schedule|book)(?:.{0,30})(?:demo|demonstration|product tour|walkthrough)",
            "cancellation": r"(?i)(?:cancel|terminate|end|discontinue)(?:.{0,30})(?:subscription|service|account|contract)",
            "speaking_opportunity": r"(?i)(?:speak|talk|present|keynote|panel)(?:.{0,30})(?:conference|event|webinar|meetup|summit)",
            "publicity_opportunity": r"(?i)(?:feature|highlight|showcase|interview|article)(?:.{0,30})(?:blog|publication|magazine|podcast|press)",
            "partnership_request": r"(?i)(?:partner|collaborate|alliance|joint venture|work together)(?:.{0,30})(?:opportunity|proposal|idea|initiative)",
            "pricing_inquiry": r"(?i)(?:pricing|quote|cost|price|fee)(?:.{0,30})(?:information|details|structure|model|plan)"
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
                "Failed to load opportunity patterns",
                error=str(e),
                error_type=type(e).__name__,
            )
            return default_patterns

    def detect_opportunities(self, email_text: str) -> Dict[str, bool]:
        """Detect opportunities in email text using regex patterns.
        
        Args:
            email_text: The text content of the email
            
        Returns:
            A dictionary with opportunity types as keys and boolean values
        """
        if not email_text:
            self.logger.warning("Empty email text provided")
            return {}

        opportunities = {}
        
        try:
            for opportunity_type, pattern_str in self.patterns.items():
                pattern = re.compile(pattern_str, re.IGNORECASE)
                match = pattern.search(email_text)
                opportunities[opportunity_type] = bool(match)
                
                if match:
                    self.logger.debug(
                        f"Detected {opportunity_type}",
                        match_text=email_text[max(0, match.start() - 20):min(len(email_text), match.end() + 20)]
                    )
            
            # Count detected opportunities
            detected_count = sum(1 for v in opportunities.values() if v)
            
            if detected_count > 0:
                self.logger.info(
                    f"Detected {detected_count} opportunities",
                    opportunities=", ".join(k for k, v in opportunities.items() if v)
                )
            else:
                self.logger.debug("No opportunities detected")
                
            return opportunities
            
        except Exception as e:
            self.logger.exception(
                "Error detecting opportunities",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {}

    def update_contact_opportunities(self, from_email: str, opportunities: Dict[str, bool]) -> bool:
        """Update contact record with detected opportunities.
        
        Args:
            from_email: Email address of the contact
            opportunities: Dictionary of detected opportunities
            
        Returns:
            True if the contact was updated successfully, False otherwise
        """
        if not opportunities:
            return False
            
        try:
            with get_duckdb_connection() as conn:
                # Create or update opportunities table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS contact_opportunities (
                        id INTEGER PRIMARY KEY,
                        email VARCHAR UNIQUE,
                        demo_request BOOLEAN DEFAULT FALSE,
                        cancellation BOOLEAN DEFAULT FALSE,
                        speaking_opportunity BOOLEAN DEFAULT FALSE,
                        publicity_opportunity BOOLEAN DEFAULT FALSE,
                        partnership_request BOOLEAN DEFAULT FALSE,
                        pricing_inquiry BOOLEAN DEFAULT FALSE,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Check if contact exists in opportunities table
                result = conn.execute("""
                    SELECT id FROM contact_opportunities WHERE email = ?
                """, (from_email,)).fetchone()
                
                if result:
                    # Update existing record
                    update_fields = []
                    update_values = []
                    
                    for opportunity_type, detected in opportunities.items():
                        if detected:
                            update_fields.append(f"{opportunity_type} = TRUE")
                        
                    if update_fields:
                        update_fields.append("last_updated = CURRENT_TIMESTAMP")
                        update_sql = f"""
                            UPDATE contact_opportunities
                            SET {', '.join(update_fields)}
                            WHERE email = ?
                        """
                        conn.execute(update_sql, (from_email,))
                        self.logger.info(f"Updated opportunities for {from_email}")
                else:
                    # Insert new record
                    fields = ["email"]
                    values = [from_email]
                    placeholders = ["?"]
                    
                    for opportunity_type, detected in opportunities.items():
                        if detected:
                            fields.append(opportunity_type)
                            values.append(True)
                            placeholders.append("TRUE")
                    
                    insert_sql = f"""
                        INSERT INTO contact_opportunities
                        ({', '.join(fields)})
                        VALUES ({', '.join(placeholders)})
                    """
                    conn.execute(insert_sql, values)
                    self.logger.info(f"Created opportunities record for {from_email}")
                
                # Update the main contacts table if it exists
                try:
                    # Check if contacts table exists
                    result = conn.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='contacts'
                    """).fetchone()
                    
                    if result:
                        # Check if contact exists
                        result = conn.execute("""
                            SELECT id FROM contacts WHERE email = ?
                        """, (from_email,)).fetchone()
                        
                        if result:
                            # Update metadata field with opportunities
                            conn.execute("""
                                UPDATE contacts
                                SET metadata = json_insert(
                                    COALESCE(metadata, '{}'),
                                    '$.opportunities', ?,
                                    '$.opportunities_updated_at', ?
                                ),
                                updated_at = CURRENT_TIMESTAMP
                                WHERE email = ?
                            """, (
                                json.dumps(opportunities),
                                datetime.now().isoformat(),
                                from_email
                            ))
                except Exception as e:
                    self.logger.warning(
                        "Failed to update contacts table",
                        email=from_email,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                
                return True
                
        except Exception as e:
            self.logger.exception(
                "Failed to update contact opportunities",
                email=from_email,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def process_email(self, email_id: str) -> bool:
        """Process a single email for opportunity detection.
        
        Args:
            email_id: ID of the email to process
            
        Returns:
            True if opportunities were detected and stored, False otherwise
        """
        try:
            self.logger.info(f"Processing email {email_id} for opportunity detection")
            
            # Get email data from database
            with get_duckdb_connection() as conn:
                result = conn.execute("""
                    SELECT id, from_email, subject, plain_body
                    FROM emails
                    WHERE id = ?
                """, (email_id,)).fetchone()
                
                if not result:
                    self.logger.warning(f"Email {email_id} not found")
                    return False
                
                db_id, from_email, subject, plain_body = result
                
                if not plain_body:
                    self.logger.warning(f"Email {email_id} has no plain body text")
                    return False
                
                # Combine subject and body for detection
                full_text = f"{subject}\n\n{plain_body}"
                
                # Detect opportunities
                opportunities = self.detect_opportunities(full_text)
                
                if any(opportunities.values()):
                    # Update contact opportunities
                    if self.update_contact_opportunities(from_email, opportunities):
                        # Log detection activity
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
                            "email",
                            email_id,
                            "opportunity_detection",
                            json.dumps({
                                "from_email": from_email,
                                "opportunities": {k: v for k, v in opportunities.items() if v},
                                "detected_at": datetime.now().isoformat()
                            })
                        ))
                        
                        self.logger.info(
                            "Opportunity detection successful",
                            email_id=email_id,
                            from_email=from_email,
                            opportunities=", ".join(k for k, v in opportunities.items() if v)
                        )
                        return True
                    else:
                        self.logger.warning(
                            "Failed to update contact opportunities",
                            email_id=email_id,
                            from_email=from_email
                        )
                        return False
                else:
                    self.logger.info(
                        "No opportunities detected",
                        email_id=email_id,
                        from_email=from_email
                    )
                    return False
                
        except Exception as e:
            self.logger.exception(
                "Opportunity detection failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


def detect_opportunities(batch_size: int = 50) -> int:
    """Process a batch of emails for opportunity detection.
    
    Args:
        batch_size: Number of emails to process in this batch
        
    Returns:
        Number of emails with opportunities detected
    """
    detection_service = OpportunityDetectionService()
    logger.info("Starting opportunity detection batch", batch_size=batch_size)
    
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
            
            # Get emails that haven't been processed for opportunity detection yet
            result = conn.execute("""
                SELECT e.id, e.from_email
                FROM emails e
                LEFT JOIN processed_emails p ON e.id = p.email_id AND p.process_type = 'opportunity_detection'
                WHERE p.email_id IS NULL
                AND e.plain_body IS NOT NULL
                LIMIT ?
            """, (batch_size,)).fetchall()
            
            if not result:
                logger.info("No emails to process for opportunity detection")
                return 0
                
            logger.info(f"Found {len(result)} emails to process for opportunity detection")
            
            success_count = 0
            for row in result:
                email_id, from_email = row
                
                try:
                    success = detection_service.process_email(email_id)
                    
                    # Mark email as processed regardless of success
                    conn.execute("""
                        INSERT INTO processed_emails (email_id, process_type)
                        VALUES (?, ?)
                    """, (email_id, "opportunity_detection"))
                    
                    if success:
                        success_count += 1
                except Exception as e:
                    logger.exception(
                        "Opportunity detection failed",
                        email_id=email_id,
                        from_email=from_email,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
            
            logger.info(
                "Completed opportunity detection batch",
                processed=len(result),
                successful=success_count
            )
            return success_count
            
    except Exception as e:
        logger.exception(
            "Opportunity detection batch failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Detect opportunities in emails")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of emails to process")
    args = parser.parse_args()
    
    detect_opportunities(args.batch_size) 