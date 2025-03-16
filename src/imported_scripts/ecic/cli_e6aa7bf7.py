"""ECIC Command Line Interface."""

import argparse
import logging
import sys

from .app import ECICApp
from .config import create_default_config, load_config

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ECIC Terminal")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument("-c", "--config", help="Path to config file")
    args = parser.parse_args()

    # Set up logging
    setup_logging("DEBUG" if args.verbose else "INFO")

    try:
        # Create default config if it doesn't exist
        create_default_config()

        # Load configuration
        config = load_config(args.config)

        # Run application
        app = ECICApp(config)
        app.run()

    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Application error: %s", str(e))
        if args.verbose:
            logger.error("Detailed error information:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
