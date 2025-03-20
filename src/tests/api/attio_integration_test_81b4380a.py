```python
"""Test script for Attio API integration following official documentation examples."""

import logging
import os
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from requests import Response
from requests.exceptions import RequestException

def configure_logging() -> logging.Logger:
    """Configures logging for the application.

    Returns:
        logging.Logger: The configured logger.
    """
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)


def load_api_key(logger: logging.Logger) -> str | None:
    """Loads the Attio API key from the environment.

    Args:
        logger: The logger instance.

    Returns:
        The API key if found, otherwise None.
    """
    load_dotenv()
    api_key = os.getenv("ATTIO_API_KEY")
    if not api_key:
        logger.error("ATTIO_API_KEY environment variable not set")
        logger.info("Troubleshooting:")
        logger.info("1. Create a .env file in project root")
        logger.info("2. Add: ATTIO_API_KEY=your_live_key_here")
        return None
    return api_key


def fetch_lists_from_attio(api_key: str, logger: logging.Logger) -> List[Dict[str, Any]] | None:
    """Fetches lists from the Attio API.

    Args:
        api_key: The Attio API key.
        logger: The logger instance.

    Returns:
        A list of dictionaries representing the lists, or None if the request fails.
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    url = "https://api.attio.com/v2/lists"

    try:
        logger.info("Making API call to /v2/lists endpoint...")
        response: Response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json().get('data', [])
    except RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        logger.info("Troubleshooting steps:")
        logger.info("1. Verify API key has 'lists:read' permission")
        logger.info("2. Check network connectivity")
        logger.info("3. Validate API status at https://status.attio.com")
        return None


def process_and_display_lists(lists: List[Dict[str, Any]], logger: logging.Logger) -> None:
    """Processes and displays information about the retrieved lists.

    Args:
        lists: A list of dictionaries representing the lists.
        logger: The logger instance.
    """
    logger.info(f"Successfully retrieved {len(lists)} lists")

    for lst in lists[:3]:  # Show first 3 lists to avoid overflow
        logger.debug("Raw list structure: %s", lst)  # Help debug schema changes
        logger.debug("Full ID structure: %s", lst.get('id', {}))
        logger.info(
            "List: %s (Workspace ID: %s, List ID: %s)",
            lst.get('attributes', {}).get('name', 'Unnamed List'),
            lst.get('id', {}).get('workspace_id', 'Unknown'),
            lst.get('id', {}).get('list_id', 'Unknown')
        )


def main() -> None:
    """Main function to execute the Attio API integration."""
    logger: logging.Logger = configure_logging()
    api_key: str | None = load_api_key(logger)

    if not api_key:
        return

    lists: List[Dict[str, Any]] | None = fetch_lists_from_attio(api_key, logger)

    if lists:
        process_and_display_lists(lists, logger)


if __name__ == "__main__":
    main()
```
