"""
Base Engine Module
================

Provides base classes for all research engines in the EthiFinX platform.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ...core.llm import LLMClient


class BaseEngine(ABC):
    """
    Base class for all research engines.

    Provides common functionality like:
    - Logging setup
    - LLM client initialization
    - Basic configuration

    Attributes:
        logger: Logger instance for this engine
        llm: LLM client for text processing
    """

    def __init__(self) -> None:
        """Initializes the BaseEngine with logging and LLM client."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_logging()
        self.llm = LLMClient()

    def _setup_logging(self) -> None:
        """Sets up console and file logging for the engine."""
        if not self.logger.handlers:
            self._setup_console_logging()
            self._setup_file_logging()
            self.logger.setLevel(logging.DEBUG)

    def _setup_console_logging(self) -> None:
        """Sets up console logging with detailed formatting."""
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)

    def _setup_file_logging(self) -> None:
        """Sets up file logging for debug information."""
        try:
            file_handler = logging.FileHandler(
                f"logs/{self.__class__.__name__.lower()}.log"
            )
            file_formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s\n"
                "Path: %(pathname)s:%(lineno)d\n"
                "Function: %(funcName)s\n"
                "Message:\n%(message)s\n",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)
        except Exception as e:
            self.logger.warning(f"Could not set up file logging: {str(e)}")

    def _log_api_request(
        self, method: str, url: str, headers: Dict[str, str], data: Any
    ) -> None:
        """Logs API request details at debug level."""
        self.logger.debug("\n" + "=" * 80)
        self.logger.debug("API REQUEST")
        self.logger.debug("=" * 80)
        self.logger.debug(f"Method: {method}")
        self.logger.debug(f"URL: {url}")
        self.logger.debug("\nHeaders:")
        for key, value in headers.items():
            if key.lower() == "authorization":
                self.logger.debug(f"{key}: <redacted>")
            else:
                self.logger.debug(f"{key}: {value}")
        self.logger.debug("\nData:")
        if isinstance(data, (dict, list)):
            self.logger.debug(json.dumps(data, indent=2))
        else:
            self.logger.debug(str(data))
        self.logger.debug("=" * 80 + "\n")

    def _log_api_response(
        self, status_code: int, headers: Dict[str, str], data: Any
    ) -> None:
        """Logs API response details at debug level."""
        self.logger.debug("\n" + "=" * 80)
        self.logger.debug("API RESPONSE")
        self.logger.debug("=" * 80)
        self.logger.debug(f"Status: {status_code}")
        self.logger.debug("\nHeaders:")
        for key, value in headers.items():
            self.logger.debug(f"{key}: {value}")
        self.logger.debug("\nData:")
        if isinstance(data, (dict, list)):
            self.logger.debug(json.dumps(data, indent=2))
        else:
            self.logger.debug(str(data))
        self.logger.debug("=" * 80 + "\n")

    @abstractmethod
    async def process(self) -> Dict[str, Any]:
        """
        Main processing method to be implemented by subclasses.

        Returns:
            Dict containing the processing results

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement process method")


class SearchEngine(ABC):
    """
    Base class for search engines.

    All search engines should inherit from this class and implement
    the search method according to their specific search provider.
    """

    @abstractmethod
    def search(
        self, query: str, max_results: int = 10, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Execute a search query.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            **kwargs: Additional search parameters

        Returns:
            List of dictionaries containing search results

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement search method")


class AnalysisEngine(ABC):
    """
    Base class for analysis engines.

    All analysis engines should inherit from this class and implement
    the analyze method according to their specific analysis approach.
    """

    @abstractmethod
    def analyze(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a set of results.

        Args:
            results: List of dictionaries containing data to analyze

        Returns:
            Dictionary containing analysis results

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement analyze method")
