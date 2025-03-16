# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

#!/usr/bin/env python3
import argparse

from api_client import APIClient
from data_processor import DataProcessor
from data_store import DataStore
from database_reset import DatabaseResetter
from logger import setup_logger
from search_flow import SearchFlow

logger = setup_logger("run_background_search", "logs/run_background_search.log")


def parse_arguments():
    """Parse command line arguments."""
    logger.debug("Parsing command line arguments")
    parser = argparse.ArgumentParser(
        description="Run search flow as a background process.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the research database.",
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Search query to process",
    )
    return parser.parse_args()


def initialize_components():
    """Initialize all application components."""
    logger.debug("Initializing application components")
    return {
        "api_client": APIClient(),
        "data_store": DataStore(),
        "data_processor": DataProcessor(),
        "search_flow": SearchFlow(APIClient(), DataStore(), DataProcessor()),
    }


def main() -> None:
    args = parse_arguments()
    components = initialize_components()

    if args.reset:
        logger.warning("Resetting the research database.")
        DatabaseResetter(components["data_store"]).reset_research_tables()

    try:
        logger.info(f"Starting background search for query: {args.query}")
        components["search_flow"].process_search(args.query)
        logger.info("Background search completed successfully.")
    except Exception as e:
        logger.critical(f"Background search failed: {e}")


if __name__ == "__main__":
    main()
