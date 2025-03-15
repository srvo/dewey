import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def search_pypi(package_name):
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
            logger.error(f"Error: {e}")
    except json.JSONDecodeError:
        logger.error("Error: Invalid JSON response from PyPI.")

def search_pypi_general(query):
    """Searches PyPI for packages based on a general query and logs the results."""
    url = f"https://pypi.org/search/?q={query}&format=json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            logger.info(f"No results found for query: '{query}'")
            return
        for result in results:
            package_info = (
                f"Package: {result['name']}\n"
                f"Version: {result['version']}\n"
                f"Summary: {result['summary']}\n"
                f"Project URL: {result['url']}\n"
                f"{'-' * 20}"
            )
            logger.info(package_info)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error: {e}")
    except json.JSONDecodeError:
        logger.error("Error: Invalid JSON response from PyPI.")

# Example usage:
search_pypi("pandas")
logger.info("\nGeneral search for 'data analysis':")
search_pypi_general("data analysis")
