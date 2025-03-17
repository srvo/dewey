"""
Database Data Processing
====================

Handles data processing, transformation, and validation for database operations.
Provides consistent interfaces for converting between different data formats.
"""

from typing import Dict, Any
from datetime import datetime
from ..core.logger import setup_logger

logger = setup_logger("db_processor", "logs/db_processor.log")


class DataProcessor:
    """
    General-purpose data processor for database operations.
    Handles raw data processing, validation, and transformation.
    """

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw data into database-ready format.

        Args:
            data: Raw data to process

        Returns:
            Processed data ready for database insertion

        Raises:
            ValueError: If data format is invalid
            TypeError: If data types don't match expected schema
        """
        if data is None:
            raise ValueError("Data cannot be None")
            
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
            
        if not data:
            raise ValueError("Data dictionary cannot be empty")
            
        try:
            logger.debug("Processing data: %s", type(data))

            if self._is_workflow_data(data):
                logger.info("Processing workflow data")
                return self._process_workflow_data(data)

            if self._is_research_data(data):
                logger.info("Processing research data")
                return self._process_research_data(data)
                
            if any(value is None for value in data.values()):
                raise TypeError("Data values cannot be None")

            logger.info("Processing generic data")
            return self._process_generic_data(data)

        except (ValueError, TypeError) as e:
            logger.error("Error processing data: %s", str(e), exc_info=True)
            raise
        except Exception as e:
            logger.error("Unexpected error processing data: %s", str(e), exc_info=True)
            raise ValueError(f"Data processing failed: {str(e)}")

    def _is_workflow_data(self, data: Dict[str, Any]) -> bool:
        """Check if data is from analysis workflow."""
        return isinstance(data, dict) and all(k in data for k in ["tags", "summary"]) and data["tags"] is not None and data["summary"] is not None

    def _is_research_data(self, data: Dict[str, Any]) -> bool:
        """Check if data is from research process."""
        return isinstance(data, dict) and all(k in data for k in ["content", "source"])

    def _process_workflow_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process workflow data into database format.

        Handles:
        - Analysis tags
        - Summaries
        - Metadata
        """
        logger.debug("Processing workflow data with keys: %s", data.keys())

        # Convert workflow format to database format
        from .converters import workflow_to_database

        return workflow_to_database(data)

    def _process_research_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process research data into database format.

        Handles:
        - Research content
        - Source information
        - Timestamps
        """
        logger.debug(
            "Processing research data: %s", data.get("source", "unknown source")
        )

        return {
            "content": data["content"],
            "source": data["source"],
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "original_format": "research_data",
                "source_type": self._determine_source_type(data),
            },
        }

    def _process_generic_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process non-specific data format."""
        logger.debug("Processing generic data")

        return {
            "processed": True,
            "original_data": data,
            "processed_at": datetime.now().isoformat(),
            "format": "generic",
        }

    def _determine_source_type(self, data: Dict[str, Any]) -> str:
        """Determine the type of research source."""
        source = data.get("source", "").lower()
        if "api" in source:
            return "api_data"
        if "research" in source:
            return "research_data"
        return "unknown"
