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

import argparse  # Added
import json
import re
import os
import sys  # Added
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import structlog

from src.dewey.core.db import get_duckdb_connection
from dewey.utils import get_logger
from dewey.core.engines import MotherDuckEngine

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


def detect_opportunities(engine, dedup_strategy='update'):
    """Detect opportunities in email and contact data."""
    # Extract opportunities from emails
    engine.execute_query("""
        UPDATE emails e
        SET opportunities = llm_detect_opportunities(body)
        WHERE opportunities IS NULL
        AND body IS NOT NULL
    """)
    
    # Create opportunity records
    engine.execute_query("""
        INSERT INTO opportunities (
            email_id,
            contact_id,
            company_id,
            type,
            description,
            detected_at,
            status
        )
        SELECT 
            e.id,
            e.contact_id,
            e.company_id,
            o.type,
            o.description,
            CURRENT_TIMESTAMP,
            'new'
        FROM emails e
        CROSS JOIN UNNEST(e.opportunities) AS o(type, description)
        LEFT JOIN opportunities op ON 
            e.id = op.email_id AND 
            o.type = op.type AND 
            o.description = op.description
        WHERE op.id IS NULL
        AND e.opportunities IS NOT NULL
    """)
    
    # Update opportunity scores
    engine.execute_query("""
        UPDATE opportunities o
        SET 
            priority_score = llm_calculate_priority(o.description),
            value_estimate = llm_estimate_value(o.description)
        WHERE priority_score IS NULL
        OR value_estimate IS NULL
    """)

def main():
    """Entrypoint for opportunity detection CLI tool."""
    parser = argparse.ArgumentParser(description='Detect opportunities in email and contact data')
    parser.add_argument('--target_db', help='Target database name', default='dewey')
    parser.add_argument('--dedup_strategy', choices=['none', 'update', 'ignore'], default='update',
                       help='Deduplication strategy: none, update, or ignore')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('opportunity_detection', log_dir)

    try:
        engine = MotherDuckEngine(args.target_db)
        
        logger.info("Starting opportunity detection process", extra={"process": "opportunity_detection"})
        
        # Get initial counts
        email_count = engine.execute_query("SELECT COUNT(*) FROM emails").fetchone()[0]
        processed_count = engine.execute_query("""
            SELECT COUNT(*) FROM emails 
            WHERE opportunities IS NOT NULL
        """).fetchone()[0]
        opportunity_count = engine.execute_query("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        
        logger.info(f"Total emails: {email_count}", metric="email_count")
        logger.info(f"Emails processed: {processed_count}", metric="processed_count")
        logger.info(f"Existing opportunities: {opportunity_count}", metric="existing_opportunities")
        
        # Perform detection
        detect_opportunities(engine, args.dedup_strategy)
        
        # Get final counts
        final_processed = engine.execute_query("""
            SELECT COUNT(*) FROM emails 
            WHERE opportunities IS NOT NULL
        """).fetchone()[0]
        final_opportunities = engine.execute_query("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        
        logger.info("\nDetection completed", status="completed")
        logger.info(f"Total emails processed: {email_count}", metric="total_processed")
        logger.info(f"Newly processed emails: {final_processed - processed_count}", metric="new_processed")
        logger.info(f"New opportunities detected: {final_opportunities - opportunity_count}", metric="new_opportunities")
        logger.info(f"Total opportunities: {final_opportunities}", metric="total_opportunities")
        
    except Exception as e:
        logger.error(f"Error during opportunity detection: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if 'engine' in locals():
            engine.close()

if __name__ == '__main__':
    main()
import pytest
import structlog
from pathlib import Path
import duckdb
import json
import datetime
from contextlib import contextmanager

from src.dewey.core.crm.enrichment.opportunity_detection_service import OpportunityDetectionService
from src.dewey.core.db import get_duckdb_connection

# Fixtures
@pytest.fixture
def tmp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / "dewey" / "config" / "opportunity"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

@pytest.fixture
def service(tmp_config_dir):
    """OpportunityDetectionService instance with temporary config."""
    return OpportunityDetectionService(config_dir=tmp_config_dir)

@pytest.fixture
def mock_duckdb_connection(tmp_path, monkeypatch):
    """Patch get_duckdb_connection to use in-memory DuckDB."""
    conn = duckdb.connect(database=':memory:')
    
    def mock_get_duckdb_connection():
        return conn
    
    monkeypatch.setattr('src.dewey.core.db.get_duckdb_connection', mock_get_duckdb_connection)
    return conn

# Test _load_patterns
def test__load_patterns_existing_file(service, tmp_config_dir):
    """Verify loading existing patterns file."""
    patterns = {"test_pattern": "test regex"}
    patterns_file = tmp_config_dir / "opportunity_patterns.json"
    with open(patterns_file, 'w') as f:
        json.dump(patterns, f)
        
    loaded = service._load_patterns()
    assert loaded == patterns

def test__load_patterns_no_file(service, tmp_config_dir):
    """Verify default patterns created when file missing."""
    patterns_file = tmp_config_dir / "opportunity_patterns.json"
    assert not patterns_file.exists()
    
    loaded = service._load_patterns()
    default_patterns = {
        "demo_request": r"(?i)(?:would like|interested in|request|schedule|book)(?:.{0,30})(?:demo|demonstration|product tour|walkthrough)",
        "cancellation": r"(?i)(?:cancel|terminate|end|discontinue)(?:.{0,30})(?:subscription|service|account|contract)",
        "speaking_opportunity": r"(?i)(?:speak|talk|present|keynote|panel)(?:.{0,30})(?:conference|event|webinar|meetup|summit)",
        "publicity_opportunity": r"(?i)(?:feature|highlight|showcase|interview|article)(?:.{0,30})(?:blog|publication|magazine|podcast|press)",
        "partnership_request": r"(?i)(?:partner|collaborate|alliance|joint venture|work together)(?:.{0,30})(?:opportunity|proposal|idea|initiative)",
        "pricing_inquiry": r"(?i)(?:pricing|quote|cost|price|fee)(?:.{0,30})(?:information|details|structure|model|plan)"
    }
    assert loaded == default_patterns
    assert patterns_file.exists()

def test__load_patterns_invalid_json(service, tmp_config_dir):
    """Verify error handling for invalid JSON patterns file."""
    patterns_file = tmp_config_dir / "opportunity_patterns.json"
    with open(patterns_file, 'w') as f:
        f.write("invalid json")
        
    with pytest.raises(json.JSONDecoderror):
        service._load_patterns()

# Test detect_opportunities
def test_detect_opportunities_demo_request(service):
    """Verify demo request detection."""
    email_text = "I would like to schedule a product tour."
    result = service.detect_opportunities(email_text)
    assert result["demo_request"] is True
    assert all(v is False for k, v in result.items() if k != "demo_request")

def test_detect_opportunities_empty(service, caplog):
    """Verify empty email handling."""
    result = service.detect_opportunities("")
    assert result == {}
    assert "Empty email text provided" in caplog.text

def test_detect_opportunities_multiple_matches(service):
    """Verify multiple opportunity types detected."""
    email_text = "Cancel my account and schedule a demo."
    result = service.detect_opportunities(email_text)
    assert result["cancellation"] is True
    assert result["demo_request"] is True

# Test update_contact_opportunities
def test_update_contact_opportunities_new_record(service, mock_duckdb_connection):
    """Verify new contact insertion."""
    opportunities = {"demo_request": True}
    email = "test@example.com"
    
    result = service.update_contact_opportunities(email, opportunities)
    assert result is True
    
    row = mock_duckdb_connection.execute(
        "SELECT * FROM contact_opportunities WHERE email = ?",
        (email,)
    ).fetchone()
    assert row["demo_request"] is True

def test_update_contact_opportunities_existing(service, mock_duckdb_connection):
    """Verify existing contact update."""
    mock_duckdb_connection.execute("INSERT INTO contact_opportunities (email) VALUES ('existing@example.com')")
    
    opportunities = {"cancellation": True}
    service.update_contact_opportunities("existing@example.com", opportunities)
    
    row = mock_duckdb_connection.execute(
        "SELECT * FROM contact_opportunities WHERE email = ?",
        ("existing@example.com",)
    ).fetchone()
    assert row["cancellation"] is True

# Test process_email
def test_process_email_success(service, mock_duckdb_connection):
    """Verify end-to-end email processing."""
    mock_duckdb_connection.execute("""
        CREATE TABLE emails (id VARCHAR PRIMARY KEY, from_email VARCHAR, subject VARCHAR, plain_body VARCHAR);
        INSERT INTO emails VALUES ('123', 'test@example.com', 'Demo Request', 'Please schedule a demo');
    """)
    
    service.process_email("123")
    
    # Check contact_opportunities
    row = mock_duckdb_connection.execute(
        "SELECT * FROM contact_opportunities WHERE email = 'test@example.com'"
    ).fetchone()
    assert row["demo_request"] is True
    
    # Check activity log
    log_row = mock_duckdb_connection.execute(
        "SELECT * FROM activity_log WHERE entity_id = '123'"
    ).fetchone()
    assert log_row["activity_type"] == "opportunity_detection"

# Integration test for detect_opportunities function
def test_detect_opportunities_function(mock_duckdb_connection):
    """Verify SQL-based opportunity detection."""
    engine = MotherDuckEngine()  # Assuming MotherDuckEngine uses mock connection
    
    # Create test emails
    mock_duckdb_connection.execute("""
        CREATE TABLE emails (id VARCHAR, body VARCHAR, opportunities JSON);
        INSERT INTO emails VALUES ('1', 'Cancel my account', NULL);
    """)
    
    detect_opportunities(engine)
    
    # Verify opportunities field populated
    row = mock_duckdb_connection.execute("SELECT opportunities FROM emails WHERE id = '1'").fetchone()
    assert row[0]["cancellation"] is True

    def test_update_contact_opportunities_no_opportunities(service, mock_duckdb_connection):
        """Verify returns False when no opportunities provided."""
        opportunities = {}
        result = service.update_contact_opportunities("test@example.com", opportunities)
        assert result is False

    def test_process_email_email_not_found(service, mock_duckdb_connection, caplog):
        """Verify handling of non-existent email ID."""
        result = service.process_email("999")
        assert result is False
        assert "Email 999 not found" in caplog.text

    def test_process_email_no_plain_body(service, mock_duckdb_connection, caplog):
        """Verify handling when email has no plain body."""
        mock_duckdb_connection.execute("INSERT INTO emails (id, from_email, subject, plain_body) VALUES ('456', 'test@example.com', 'Subject', NULL)")
        result = service.process_email("456")
        assert result is False
        assert "Email 456 has no plain body text" in caplog.text

    def test_detect_opportunities_no_matches(service, caplog):
        """Verify no opportunities detected when no matches."""
        email_text = "This email has no relevant content."
        result = service.detect_opportunities(email_text)
        assert not any(result.values())
        assert "No opportunities detected" in caplog.text

    def test_detect_opportunities_function_demo_request(mock_duckdb_connection):
        """Verify detection of demo_request via SQL."""
        engine = MotherDuckEngine()
        mock_duckdb_connection.execute("INSERT INTO emails (id, body) VALUES ('2', 'Please schedule a product tour')")
        detect_opportunities(engine)
        row = mock_duckdb_connection.execute("SELECT opportunities FROM emails WHERE id='2'").fetchone()
        assert row[0]["demo_request"] is True

    def test_process_email_activity_log(service, mock_duckdb_connection):
        """Verify activity log entry creation."""
        mock_duckdb_connection.execute("INSERT INTO emails (id, from_email, subject, plain_body) VALUES ('123', 'test@example.com', 'Demo', 'Schedule a demo')")
        service.process_email("123")
        log_row = mock_duckdb_connection.execute("SELECT * FROM activity_log WHERE entity_id='123'").fetchone()
        assert log_row is not None

    def test_update_contacts_table(service, mock_duckdb_connection):
        """Verify metadata update in contacts table."""
        mock_duckdb_connection.execute("CREATE TABLE contacts (id INTEGER PRIMARY KEY, email VARCHAR, metadata JSON)")
        mock_duckdb_connection.execute("INSERT INTO contacts (id, email) VALUES (1, 'test@example.com')")
        opportunities = {"demo_request": True}
        service.update_contact_opportunities("test@example.com", opportunities)
        metadata_row = mock_duckdb_connection.execute("SELECT metadata FROM contacts WHERE email='test@example.com'").fetchone()
        assert 'opportunities' in metadata_row[0]
        assert 'opportunities_updated_at' in metadata_row[0]
