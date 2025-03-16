# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""Database Data Processing.
====================

Handles data processing, transformation, and validation for database operations.
Provides consistent interfaces for converting between different data formats.
"""

from datetime import datetime
from typing import Any

from ..core.logger import setup_logger

logger = setup_logger("db_processor", "logs/db_processor.log")


class DataProcessor:
    """General-purpose data processor for database operations.
    Handles raw data processing, validation, and transformation.
    """

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process raw data into database-ready format.

        Args:
        ----
            data: Raw data to process

        Returns:
        -------
            Processed data ready for database insertion

        Raises:
        ------
            ValueError: If data format is invalid
            TypeError: If data types don't match expected schema

        """
        if data is None:
            msg = "Data cannot be None"
            raise ValueError(msg)

        if not isinstance(data, dict):
            msg = "Data must be a dictionary"
            raise ValueError(msg)

        if not data:
            msg = "Data dictionary cannot be empty"
            raise ValueError(msg)

        try:
            logger.debug("Processing data: %s", type(data))

            if self._is_workflow_data(data):
                logger.info("Processing workflow data")
                return self._process_workflow_data(data)

            if self._is_research_data(data):
                logger.info("Processing research data")
                return self._process_research_data(data)

            if any(value is None for value in data.values()):
                msg = "Data values cannot be None"
                raise TypeError(msg)

            logger.info("Processing generic data")
            return self._process_generic_data(data)

        except (ValueError, TypeError) as e:
            logger.error("Error processing data: %s", str(e), exc_info=True)
            raise
        except Exception as e:
            logger.error("Unexpected error processing data: %s", str(e), exc_info=True)
            msg = f"Data processing failed: {e!s}"
            raise ValueError(msg)

    def _is_workflow_data(self, data: dict[str, Any]) -> bool:
        """Check if data is from analysis workflow."""
        return (
            isinstance(data, dict)
            and all(k in data for k in ["tags", "summary"])
            and data["tags"] is not None
            and data["summary"] is not None
        )

    def _is_research_data(self, data: dict[str, Any]) -> bool:
        """Check if data is from research process."""
        return isinstance(data, dict) and all(k in data for k in ["content", "source"])

    def _process_workflow_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process workflow data into database format.

        Handles:
        - Analysis tags
        - Summaries
        - Metadata
        """
        logger.debug("Processing workflow data with keys: %s", data.keys())

        # Convert workflow format to database format
        from .converters import workflow_to_database

        return workflow_to_database(data)

    def _process_research_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process research data into database format.

        Handles:
        - Research content
        - Source information
        - Timestamps
        """
        logger.debug(
            "Processing research data: %s",
            data.get("source", "unknown source"),
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

    def _process_generic_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process non-specific data format."""
        logger.debug("Processing generic data")

        return {
            "processed": True,
            "original_data": data,
            "processed_at": datetime.now().isoformat(),
            "format": "generic",
        }

    def _determine_source_type(self, data: dict[str, Any]) -> str:
        """Determine the type of research source."""
        source = data.get("source", "").lower()
        if "api" in source:
            return "api_data"
        if "research" in source:
            return "research_data"
        return "unknown"
