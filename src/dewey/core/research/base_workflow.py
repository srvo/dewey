#!/usr/bin/env python3
"""Base workflow for research tasks."""

import csv
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from dewey.core.base_script import BaseScript
from dewey.core.research.engines.base import BaseEngine
from dewey.core.research.research_output_handler import ResearchOutputHandler


class BaseWorkflow(BaseScript, ABC):
    """
    Base class for research workflows.

    Provides a foundation for building research workflows within the Dewey
    project, offering standardized configuration, logging, and database/LLM
    integration.
    """

    def __init__(
        self,
        search_engine: BaseEngine | None = None,
        analysis_engine: BaseEngine | None = None,
        output_handler: ResearchOutputHandler | None = None,
    ) -> None:
        """
        Initialize the workflow.

        Args:
        ----
            search_engine: Engine for searching information.
            analysis_engine: Engine for analyzing search results.
            output_handler: Handler for research output.

        """
        super().__init__(config_section="research_workflow")
        self.search_engine = search_engine or BaseEngine()
        self.analysis_engine = analysis_engine or BaseEngine()
        self.output_handler = output_handler or ResearchOutputHandler()

    def read_companies(self, file_path: Path) -> Iterator[dict[str, str]]:
        """
        Read companies from CSV file.

        Args:
        ----
            file_path: Path to CSV file.

        Yields:
        ------
            Iterator[Dict[str, str]]: Iterator of company data dictionaries.

        Raises:
        ------
            FileNotFoundError: If the file is not found.
            Exception: If there is an error reading the file.

        """
        try:
            with open(file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                yield from reader
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading file: {file_path} - {e}")
            raise

    @abstractmethod
    def execute(self, data_dir: str | None = None) -> dict[str, Any]:
        """
        Execute the workflow.

        Args:
        ----
            data_dir: Optional directory for data files.

        Returns:
        -------
            Dictionary containing results and statistics.

        """

    @abstractmethod
    def run(self) -> None:
        """
        Run the script.

        This method must be implemented by all subclasses.
        """
        raise NotImplementedError("The run method must be implemented")
