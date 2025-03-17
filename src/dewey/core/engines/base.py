"""Base Engine Classes
================

Provides base classes for all engine implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseEngine(ABC):
    """Base class for all data engines.
    
    Provides common functionality and interface requirements for all engines.
    """
    
    def __init__(self) -> None:
        """Initialize the base engine."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the engine."""
        pass
    
    def get_version(self) -> str:
        """Get the version of the engine."""
        return "1.0.0"
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about the engine."""
        return {
            "name": self.get_name(),
            "version": self.get_version(),
            "class": self.__class__.__name__
        }


class SearchEngine(BaseEngine):
    """Base class for search engines.
    
    Provides common functionality for search operations.
    """
    
    @abstractmethod
    def search(self, query: str, max_results: int = 10, **kwargs: Any) -> List[Dict[str, Any]]:
        """Search for information using the engine.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            **kwargs: Additional engine-specific parameters
            
        Returns:
            List of search results as dictionaries
        """
        pass
    
    def _process_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and normalize search results.
        
        Args:
            results: Raw search results
            
        Returns:
            Processed search results
        """
        return results 