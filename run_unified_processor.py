#!/usr/bin/env python

"""Run the unified email processor that handles Gmail sync and contact enrichment."""

import argparse
import logging
import signal
import sys
from pathlib import Path

# Set up project paths
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def setup_logging(debug=False):
    """Set up logging to both console and file."""
    # Create logs directory if it doesn't exist
    log_dir = project_root / "logs"
    if not log_dir.exists():
        log_dir.mkdir(parents=True)

    # Set the log level based on the debug flag
    log_level = logging.DEBUG if debug else logging.INFO

    # Configure logging to file
    log_file = log_dir / "unified_processor.log"
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

    logger = logging.getLogger(__name__)
    logger.info("Logging set up at level: %s", "DEBUG" if debug else "INFO")
    return logger


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Run the Unified Email Processor")
    parser.add_argument(
        "--batch-size", type=int, help="Number of emails to process in each batch",
    )
    parser.add_argument(
        "--max-emails", type=int, help="Maximum number of emails to process",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Set up logging
    logger = setup_logging(args.debug)

    try:
        # Import here to avoid circular imports
        from dewey.core.crm.gmail.unified_email_processor import UnifiedEmailProcessor

        # Setup graceful exit handler for the wrapper script
        def signal_handler(sig, frame):
            logger.info(
                "Received interrupt signal in wrapper, forwarding to processor...",
            )
            # The processor will handle the actual shutdown

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("🔄 Starting unified email processor...")
        logger.info(
            "✨ This process will sync new emails, extract contacts, and calculate priorities",
        )
        logger.info("ℹ️ Use Ctrl+C to gracefully exit at any time")

        # Create and run processor with arguments
        processor_args = {}
        if args.batch_size is not None:
            processor_args["batch_size"] = args.batch_size
        if args.max_emails is not None:
            processor_args["max_emails"] = args.max_emails

        processor = UnifiedEmailProcessor(**processor_args)
        processor.execute()

    except KeyboardInterrupt:
        print("\n⏹️ Process interrupted by user. Shutting down gracefully...")
    except Exception as e:
        print("❌ Error: %s", str(e))
        import traceback

        traceback.print_exc()
    finally:
        print("✅ Process completed.")


if __name__ == "__main__":
    main()
