import json
import logging

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def search_pypi(package_name) -> None:
    """Searches PyPI for a package and logs the results."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        package_info = (
            f"Package: {data['info']['name']}\n"
            f"Version: {data['info']['version']}\n"
            f"Summary: {data['info']['summary']}\n"
            f"Project URL: {data['info']['project_url']}"
        )
        logger.info(package_info)
    except requests.exceptions.RequestException as e:
        if response and response.status_code == 404:
            logger.warning(f"Package '{package_name}' not found on PyPI.")
        else:
            logger.exception(f"Error: {e}")
    except json.JSONDecodeError:
        logger.exception("Error: Invalid JSON response from PyPI.")

# TODO: Reimplement PyPI search with proper API integration
# Temporarily disabled - see https://github.com/pypi/warehouse/issues/5897
""" 
def search_pypi_general(query) -> None:
    \"\"\"Searches PyPI for packages based on a general query and logs the results.\"\"\"
    # Implementation removed

# Example usage:
# search_pypi("pandas")
# logger.info("\nGeneral search for 'data analysis':")
# search_pypi_general("data analysis")
"""
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def search_pypi(package_name) -> bool | None:
    """Searches PyPI for a package and logs the results."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        package_info = (
            f"Package: {data['info']['name']}\n"
            f"Version: {data['info']['version']}\n"
            f"Summary: {data['info']['summary']}\n"
            f"Project URL: {data['info']['project_url']}"
        )
        logger.info(package_info)
        return True
    except requests.exceptions.RequestException as e:
        if response and response.status_code == 404:
            logger.warning(f"Package '{package_name}' not found on PyPI.")
        else:
            logger.exception(f"Error: {e}")
        return False
    except json.JSONDecodeError:
        logger.exception("Error: Invalid JSON response from PyPI.")
        return False
