#!/usr/bin/env python
"""Run the Unified Email Processor.
This script launches the UnifiedEmailProcessor which handles Gmail synchronization,
email analysis, and contact extraction.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Set up project paths - project root should be /Users/srvo/dewey
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def setup_logging(debug=False):
    """Set up logging to both console and file."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Set the log level based on the debug flag
    log_level = logging.DEBUG if debug else logging.INFO

    # Configure logging to file
    log_file = os.path.join(log_dir, "unified_processor.log")
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    # Set specific loggers to debug level if requested
    if debug:
        logging.getLogger("dewey.core.crm.gmail").setLevel(logging.DEBUG)
        logging.getLogger("EmailEnrichment").setLevel(logging.DEBUG)
        logging.getLogger("UnifiedEmailProcessor").setLevel(logging.DEBUG)
        logging.getLogger("gmail_sync").setLevel(logging.DEBUG)

    logging.info("Logging set up at level: %s", "DEBUG" if debug else "INFO")


def run_processor(batch_size=None, max_emails=None, debug=False):
    """Run the UnifiedEmailProcessor with the specified parameters."""
    try:
        # Import here to avoid circular imports
        from dewey.core.crm.gmail.unified_email_processor import UnifiedEmailProcessor

        # Set up logging
        setup_logging(debug)

        # Create processor with batch size if specified
        processor_args = {}
        if batch_size is not None:
            processor_args["batch_size"] = batch_size
        if max_emails is not None:
            processor_args["max_emails"] = max_emails

        # Initialize and run processor
        processor = UnifiedEmailProcessor(**processor_args)
        processor.execute()

    except Exception as e:
        logging.exception(
            "Error initializing or running UnifiedEmailProcessor: %s", e
        )
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run the Unified Email Processor")
    parser.add_argument(
        "--batch-size", type=int, help="Number of emails to process in each batch",
    )
    parser.add_argument(
        "--max-emails", type=int, help="Maximum number of emails to process",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Run the processor with the specified arguments
    run_processor(args.batch_size, args.max_emails, args.debug)


if __name__ == "__main__":
    main()
