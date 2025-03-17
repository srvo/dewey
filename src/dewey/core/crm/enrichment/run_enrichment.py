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