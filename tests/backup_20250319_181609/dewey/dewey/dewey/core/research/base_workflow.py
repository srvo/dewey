#!/usr/bin/env python3
"""Base workflow for research tasks."""

import csv
from pathlib import Path
from typing import Any, Dict, Iterator, Optional
from abc import ABC, abstractmethod

from .engines.base_engine import BaseEngine
from .output_handler import ResearchOutputHandler
from dewey.core.base_script import BaseScript


class BaseWorkflow(BaseScript, ABC):
    """Base class for research workflows."""

    def __init__(
        self,
        search_engine: Optional[BaseEngine] = None,
        analysis_engine: Optional[BaseEngine] = None,
        output_handler: Optional[ResearchOutputHandler] = None,
    ) -> None:
        """Initialize the workflow.

        Args:
            search_engine: Engine for searching information.
            analysis_engine: Engine for analyzing search results.
            output_handler: Handler for research output.
        """
        super().__init__()
        self.search_engine = search_engine or BaseEngine()
        self.analysis_engine = analysis_engine or BaseEngine()
        self.output_handler = output_handler or ResearchOutputHandler()

    def read_companies(self, file_path: Path) -> Iterator[Dict[str, str]]:
        """Read companies from CSV file.

        Args:
            file_path: Path to CSV file.

        Yields:
            Iterator[Dict[str, str]]: Iterator of company data dictionaries.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield row
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading file: {file_path} - {e}")
            raise

    @abstractmethod
    def execute(self, data_dir: Optional[str] = None) -> Dict[str, Any]:
        """Execute the workflow.

        Args:
            data_dir: Optional directory for data files.

        Returns:
            Dictionary containing results and statistics.
        """
        pass

    @abstractmethod
    def run(self) -> None:
        """
        Run the script.
        """
        raise NotImplementedError("The run method must be implemented")
