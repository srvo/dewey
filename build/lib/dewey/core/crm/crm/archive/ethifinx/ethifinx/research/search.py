from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class SearchEngine(ABC):
    """Abstract base class for search engines."""

    @abstractmethod
    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Execute a search query.

        Args:
            query: The search query string
            filters: Optional filters to apply to the search

        Returns:
            List of search results
        """
        pass

    def batch_search(self, queries: List[str]) -> Dict[str, List[Any]]:
        """
        Execute multiple search queries.

        Args:
            queries: List of search queries

        Returns:
            Dictionary mapping queries to their results
        """
        return {query: self.search(query) for query in queries}


class AnalysisEngine(ABC):
    """Abstract base class for analysis engines."""

    @abstractmethod
    def analyze(self, data: List[Any]) -> Dict[str, Any]:
        """
        Analyze search results.

        Args:
            data: List of data to analyze

        Returns:
            Analysis results as a dictionary
        """
        pass


class SearchWorkflow:
    """Class for managing search and analysis workflows."""

    def __init__(self, search_engine: SearchEngine, analysis_engine: AnalysisEngine):
        """
        Initialize the workflow.

        Args:
            search_engine: Search engine implementation
            analysis_engine: Analysis engine implementation
        """
        self.search_engine = search_engine
        self.analysis_engine = analysis_engine

    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Execute a search query.

        Args:
            query: The search query string
            filters: Optional filters to apply to the search

        Returns:
            List of search results
        """
        return self.search_engine.search(query, filters=filters)

    def search_and_analyze(self, query: str) -> Dict[str, Any]:
        """
        Execute a search query and analyze the results.

        Args:
            query: The search query string

        Returns:
            Analysis results
        """
        results = self.search(query)
        return self.analysis_engine.analyze(results)

    def batch_search(self, queries: List[str]) -> Dict[str, List[Any]]:
        """
        Execute multiple search queries.

        Args:
            queries: List of search queries

        Returns:
            Dictionary mapping queries to their results
        """
        return self.search_engine.batch_search(queries)
