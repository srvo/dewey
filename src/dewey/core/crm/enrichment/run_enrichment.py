#!/usr/bin/env python3
"""
Email Enrichment Pipeline

This script orchestrates the email enrichment pipeline, which includes:
1. Enriching email content (fetching full message bodies)
2. Detecting business opportunities
3. Extracting and enriching contact information
4. Prioritizing emails based on content and sender

Usage:
    python run_enrichment.py [--batch-size 50] [--max-emails 100]
"""

import argparse
import logging
import sys
import time
import structlog
import duckdb
import os
import importlib.util
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

def import_module_from_path(module_name, file_path):
    """Import a module from a file path."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            logger.error(f"Could not find module {module_name} at {file_path}")
            return None
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Failed to import {module_name}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def run_enrichment(batch_size=50, max_emails=100):
    """
    Run the email enrichment pipeline.
    
    Args:
        batch_size: Number of emails to process in each batch
        max_emails: Maximum number of emails to process in total
    """
    logger.info("Starting email enrichment pipeline", batch_size=batch_size, max_emails=max_emails)
    
    # Step 1: Enrich email content
    logger.info("Step 1: Enriching email content")
    try:
        # Import the email enrichment module
        module_path = os.path.join(os.path.dirname(__file__), "email_enrichment_service.py")
        email_module = import_module_from_path("email_enrichment_service", module_path)
        
        if email_module:
            # Get the EmailEnrichmentService class
            EmailEnrichmentService = getattr(email_module, "EmailEnrichmentService", None)
            if EmailEnrichmentService:
                # Initialize the service
                service = EmailEnrichmentService()
                # Enrich emails
                service.enrich_emails(batch_size=batch_size, max_emails=max_emails)
                logger.info(f"Enriched {min(batch_size, max_emails)} emails")
            else:
                logger.error("EmailEnrichmentService class not found in module")
        else:
            logger.error("Failed to import email enrichment module")
    except Exception as e:
        logger.error(f"Error enriching emails: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Step 2: Detect business opportunities
    logger.info("Step 2: Detecting business opportunities")
    try:
        # Import the opportunity detection module
        module_path = os.path.join(os.path.dirname(__file__), "opportunity_detection.py")
        opportunity_module = import_module_from_path("opportunity_detection", module_path)
        
        if opportunity_module:
            # Get the detect_opportunities function
            detect_opportunities = getattr(opportunity_module, "detect_opportunities", None)
            if detect_opportunities:
                # Detect opportunities
                detect_opportunities(batch_size=batch_size, max_emails=max_emails)
                logger.info(f"Detected opportunities in {min(batch_size, max_emails)} emails")
            else:
                logger.error("detect_opportunities function not found in module")
        else:
            logger.error("Failed to import opportunity detection module")
    except Exception as e:
        logger.error(f"Error detecting opportunities: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Step 3: Extract and enrich contacts
    logger.info("Step 3: Extracting and enriching contacts")
    try:
        # Import the contact enrichment module
        module_path = os.path.join(os.path.dirname(__file__), "contact_enrichment.py")
        contact_module = import_module_from_path("contact_enrichment", module_path)
        
        if contact_module:
            # Get the enrich_contacts function
            enrich_contacts = getattr(contact_module, "enrich_contacts", None)
            if enrich_contacts:
                # Enrich contacts
                enrich_contacts(batch_size=batch_size, max_emails=max_emails)
                logger.info(f"Enriched contacts from {min(batch_size, max_emails)} emails")
            else:
                logger.error("enrich_contacts function not found in module")
        else:
            logger.error("Failed to import contact enrichment module")
    except Exception as e:
        logger.error(f"Error enriching contacts: {str(e)}")
        logger.error(traceback.format_exc())
    
    logger.info("Email enrichment pipeline completed successfully")

def main():
    """Parse command-line arguments and run the enrichment pipeline."""
    parser = argparse.ArgumentParser(description="Run the email enrichment pipeline")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing emails")
    parser.add_argument("--max-emails", type=int, default=100, help="Maximum number of emails to process")
    
    args = parser.parse_args()
    
    run_enrichment(batch_size=args.batch_size, max_emails=args.max_emails)

if __name__ == "__main__":
    main()

# Pytest fixtures
@pytest.fixture
def temp_test_dir(tmp_path):
    """Create temporary test directory with mock modules."""
    # Create mock email enrichment module
    email_mod_path = tmp_path / "email_enrichment_service.py"
    with open(email_mod_path, "w") as f:
        f.write(
            "class EmailEnrichmentService:\n"
            "    def enrich_emails(self, batch_size, max_emails):\n"
            "        logger.info('Mock enrichment executed')"
        )

    # Create mock opportunity detection module
    opp_mod_path = tmp_path / "opportunity_detection.py"
    with open(opp_mod_path, "w") as f:
        f.write(
            "def detect_opportunities(batch_size, max_emails):\n"
            "    logger.info('Mock opportunity detection executed')"
        )

    # Create mock contact enrichment module
    contact_mod_path = tmp_path / "contact_enrichment.py"
    with open(contact_mod_path, "w") as f:
        f.write(
            "def enrich_contacts(batch_size, max_emails):\n"
            "    logger.info('Mock contact enrichment executed')"
        )

    # Set module search path
    sys.path.insert(0, str(tmp_path))
    yield tmp_path
    sys.path.pop(0)

@pytest.fixture
def duckdb_con():
    """Provide in-memory DuckDB connection for testing."""
    con = duckdb.connect(':memory:')
    yield con
    con.close()

# Test cases
def test_run_enrichment_happy_path(temp_test_dir, caplog):
    """Verify successful execution of all pipeline stages."""
    with caplog.at_level(logging.INFO):
        run_enrichment(batch_size=5, max_emails=10)
    
    assert "Starting email enrichment pipeline" in caplog.text
    assert "Mock enrichment executed" in caplog.text
    assert "Mock opportunity detection executed" in caplog.text
    assert "Mock contact enrichment executed" in caplog.text
    assert "Email enrichment pipeline completed successfully" in caplog.text

def test_missing_email_module(temp_test_dir, caplog):
    """Verify error handling when email module is missing."""
    # Remove email module
    os.remove(temp_test_dir / "email_enrichment_service.py")
    
    with caplog.at_level(logging.INFO):
        run_enrichment(batch_size=1, max_emails=1)
    
    assert "Failed to import email enrichment module" in caplog.text
    assert "Mock opportunity detection executed" in caplog.text  # Subsequent steps run

def test_invalid_opportunity_function(temp_test_dir, caplog):
    """Verify error when opportunity detection function missing."""
    # Remove function from module
    opp_mod_path = temp_test_dir / "opportunity_detection.py"
    with open(opp_mod_path, "w") as f:
        f.write("def invalid_function(): pass")  # Invalid signature
    
    with caplog.at_level(logging.INFO):
        run_enrichment(batch_size=1, max_emails=1)
    
    assert "detect_opportunities function not found in module" in caplog.text

def test_duckdb_integration(temp_test_dir, duckdb_con, caplog):
    """Verify DuckDB interaction using Ibis framework."""
    # Mock email enrichment to write to DuckDB
    email_mod_path = temp_test_dir / "email_enrichment_service.py"
    with open(email_mod_path, "w") as f:
        f.write(
            "import duckdb\n"
            "class EmailEnrichmentService:\n"
            "    def enrich_emails(self, batch_size, max_emails):\n"
            "        duckdb.sql('CREATE TABLE test (id INT); INSERT INTO test VALUES (1)')"
        )
    
    with caplog.at_level(logging.INFO):
        run_enrichment(batch_size=1, max_emails=1)
    
    # Verify using Ibis
    ibis_con = ibis.duckdb.connect(duckdb_con)
    table = ibis_con.table('test')
    assert table.count().execute() == 1

# Edge case tests
def test_zero_batch_size(temp_test_dir, caplog):
    """Verify handling of zero batch size."""
    with caplog.at_level(logging.INFO):
        run_enrichment(batch_size=0, max_emails=10)
    
    assert "Starting email enrichment pipeline" in caplog.text
    assert "Enriched 0 emails" in caplog.text  # Uses min(0,10)=0

def test_negative_max_emails(temp_test_dir):
    """Verify argument validation for invalid parameters."""
    with pytest.raises(SystemExit) as e:
        run_enrichment(batch_size=5, max_emails=-10)
    assert e.type == SystemExit
    assert e.value.code == 2  # argparse exits with 2 for invalid args
import argparse
import logging
import os
import sys
import structlog
import duckdb
import pytest
from src.dewey.core.crm.enrichment.run_enrichment import run_enrichment
from src.dewey.core.base_script import BaseScript

@pytest.fixture
def temp_test_dir(tmp_path):
    """Create temporary test directory with mock modules."""
    email_mod_path = tmp_path / "email_enrichment_service.py"
    with open(email_mod_path, "w") as f:
        f.write(
            "class EmailEnrichmentService:\n"
            "    def enrich_emails(self, batch_size: int, max_emails: int):\n"
            "        logger.info('Mock email enrichment executed')"
        )

    opp_mod_path = tmp_path / "opportunity_detection.py"
    with open(opp_mod_path, "w") as f:
        f.write(
            "def detect_opportunities(batch_size: int, max_emails: int):\n"
            "    logger.info('Mock opportunity detection executed')"
        )

    contact_mod_path = tmp_path / "contact_enrichment.py"
    with open(contact_mod_path, "w") as f:
        f.write(
            "def enrich_contacts(batch_size: int, max_emails: int):\n"
            "    logger.info('Mock contact enrichment executed')"
        )

    sys.path.insert(0, str(tmp_path))
    yield tmp_path
    sys.path.pop(0)

@pytest.fixture
def duckdb_con():
    """Provide in-memory DuckDB connection for testing."""
    con = duckdb.connect(':memory:')
    yield con
    con.close()

class TestRunEnrichment(BaseScript):
    """Test email enrichment pipeline following structured conventions."""

    def test_happy_path(self, temp_test_dir, caplog):
        """Verify all pipeline stages execute successfully."""
        with caplog.at_level(logging.INFO):
            run_enrichment(batch_size=5, max_emails=10)
        
        assert "Starting email enrichment pipeline" in caplog.text
        assert "Mock email enrichment executed" in caplog.text
        assert "Mock opportunity detection executed" in caplog.text
        assert "Mock contact enrichment executed" in caplog.text
        assert "Pipeline completed successfully" in caplog.text

    def test_missing_email_module(self, temp_test_dir, caplog):
        """Verify error handling when email module is missing."""
        os.remove(temp_test_dir / "email_enrichment_service.py")
        
        with caplog.at_level(logging.INFO):
            run_enrichment(batch_size=1, max_emails=1)
        
        assert "Failed to import email enrichment module" in caplog.text
        assert "opportunity detection executed" in caplog.text

    def test_missing_contact_module(self, temp_test_dir, caplog):
        """Verify pipeline continues after contact module failure."""
        os.remove(temp_test_dir / "contact_enrichment.py")
        
        with caplog.at_level(logging.INFO):
            run_enrichment(batch_size=1, max_emails=1)
        
        assert "Failed to import contact enrichment module" in caplog.text
        assert "Pipeline completed successfully" in caplog.text

    def test_invalid_opportunity_signature(self, temp_test_dir, caplog):
        """Verify invalid function signature handling."""
        opp_mod_path = temp_test_dir / "opportunity_detection.py"
        with open(opp_mod_path, "w") as f:
            f.write("def detect_opportunities(): pass")
        
        with caplog.at_level(logging.INFO):
            run_enrichment()
        
        assert "detect_opportunities function not found" in caplog.text

    def test_max_less_than_batch(self, temp_test_dir, caplog):
        """Verify processing when max_emails < batch_size."""
        with caplog.at_level(logging.INFO):
            run_enrichment(batch_size=10, max_emails=5)
        
        assert "Enriched 5 emails" in caplog.text
        assert "Detected opportunities in 5 emails" in caplog.text

    def test_zero_max_emails(self, temp_test_dir, caplog):
        """Verify zero max_emails handling."""
        with caplog.at_level(logging.INFO):
            run_enrichment(max_emails=0)
        
        assert "Enriched 0 emails" in caplog.text
        assert "Pipeline completed successfully" in caplog.text

    def test_negative_parameters(self):
        """Verify invalid parameters raise exceptions."""
        with pytest.raises(SystemExit) as e:
            run_enrichment(batch_size=-1, max_emails=-10)
        assert e.value.code == 2

    def test_duckdb_integration(self, temp_test_dir, duckdb_con, caplog):
        """Validate DuckDB interactions via Ibis."""
        email_mod_path = temp_test_dir / "email_enrichment_service.py"
        with open(email_mod_path, "w") as f:
            f.write(
                "import duckdb\n"
                "class EmailEnrichmentService:\n"
                "    def enrich_emails(self, batch_size, max_emails):\n"
                "        duckdb.sql('CREATE TABLE test_data (id INT); INSERT INTO test_data VALUES (1)')"
            )
        
        run_enrichment()
        
        ibis_con = ibis.duckdb.connect(duckdb_con)
        table = ibis_con.table('test_data')
        assert table.count().execute() == 1

@pytest.mark.parametrize("batch_size,max_emails", [(0, 10), (5, 0)])
def test_edge_cases(temp_test_dir, caplog, batch_size, max_emails):
    """Test parameter edge cases."""
    with caplog.at_level(logging.INFO):
        run_enrichment(batch_size=batch_size, max_emails=max_emails)
    
    assert "Enriched" in caplog.text
    assert "Pipeline completed" in caplog.text

def test_all_modules_missing(temp_test_dir, caplog):
    """Verify pipeline continues despite all module failures."""
    for module in ["email_enrichment", "opportunity_detection", "contact_enrichment"]:
        os.remove(temp_test_dir / f"{module}.py")
    
    with caplog.at_level(logging.INFO):
        run_enrichment()
    
    assert "Pipeline completed" in caplog.text
    assert "Failed to import" in caplog.text
import argparse
import logging
import os
import sys
import structlog
import duckdb
import ibis
from src.dewey.core.crm.enrichment.run_enrichment import run_enrichment
