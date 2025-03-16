import logging

import requests

logger = logging.getLogger(__name__)


def search_pypi(package_name: str) -> bool:
    """Searches PyPI for a package and logs the results."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logger.info(
            f"Package: {data['info']['name']}\n"
            f"Version: {data['info']['version']}\n"
            f"Summary: {data['info']['summary']}\n"
            f"Project URL: {data['info']['project_url']}",
        )
        return True
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Package '{package_name}' not found on PyPI")
        else:
            logger.exception(f"HTTP error searching PyPI: {e}")
        return False
    except Exception as e:
        logger.exception(f"Error searching PyPI: {e}")
        return False


def search_pypi_general(query: str) -> list[dict]:
    """Search PyPI for packages matching a general query."""
    url = "https://pypi.org/search/"
    try:
        response = requests.get(url, params={"q": query})
        response.raise_for_status()
        results = []

        # Parse HTML response (PyPI doesn't have a public JSON API for search)
        # This is a simplified parser - consider using BeautifulSoup for robustness
        for result in response.text.split('<a class="package-snippet"')[1:]:
            name = result.split('href="')[1].split('"')[0].split("/")[2]
            version = result.split('class="package-snippet__version">')[1].split("<")[0]
            description = result.split('class="package-snippet__description">')[
                1
            ].split("<")[0]
            results.append(
                {"name": name, "version": version, "description": description}
            )

        return results
    except Exception as e:
        logger.exception(f"Error searching PyPI: {e}")
        return []
