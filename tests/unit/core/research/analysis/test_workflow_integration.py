"""Base classes and mocks for workflow integration tests."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from unittest.mock import MagicMock

import pytest


class BaseEngine:
    """Base class for mock engines."""

    def __init__(self, *args, **kwargs):
        """Initialize the base engine."""
        self.calls = []

    def record_call(self, method: str, *args, **kwargs) -> None:
        """Record a method call.

        Args:
            method: The name of the method called.
            *args: Positional arguments.
            **kwargs: Keyword arguments.
        """
        self.calls.append({"method": method, "args": args, "kwargs": kwargs})


class MockSearchEngine(BaseEngine):
    """Mock search engine for testing."""

    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Mock search method.

        Args:
            query: The search query.
            **kwargs: Additional search parameters.

        Returns:
            A list of mock search results.
        """
        self.record_call("search", query, **kwargs)
        return [
            {
                "title": "Mock Result 1",
                "url": "https://example.com/1",
                "snippet": "This is a mock search result.",
            },
            {
                "title": "Mock Result 2",
                "url": "https://example.com/2",
                "snippet": "Another mock search result.",
            },
        ]


class MockAnalysisEngine(BaseEngine):
    """Mock analysis engine for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize the mock analysis engine."""
        super().__init__(*args, **kwargs)
        self.templates = {}

    def add_template(self, name: str, template: str) -> None:
        """Add a template to the engine.

        Args:
            name: Template name
            template: Template content
        """
        self.templates[name] = template

    def analyze(self, text: str, **kwargs) -> Dict[str, Any]:
        """Mock analysis method.

        Args:
            text: The text to analyze.
            **kwargs: Additional analysis parameters.

        Returns:
            A mock analysis result.
        """
        self.record_call("analyze", text, **kwargs)
        return {
            "score": 85,
            "analysis": "Mock analysis result",
            "risks": ["Mock risk 1", "Mock risk 2"],
            "recommendations": ["Mock recommendation 1"],
        }


class ResearchOutputHandler:
    """Mock output handler for testing."""

    def __init__(self, output_dir: Union[str, Path]):
        """Initialize the output handler.

        Args:
            output_dir: Directory for test outputs.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_results(self, results: Dict[str, Any], filename: str) -> Path:
        """Save test results to a file.

        Args:
            results: The results to save.
            filename: The output filename.

        Returns:
            The path to the saved file.
        """
        output_path = self.output_dir / filename
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        return output_path

    def load_results(self, filename: str) -> Dict[str, Any]:
        """Load test results from a file.

        Args:
            filename: The filename to load.

        Returns:
            The loaded results.
        """
        input_path = self.output_dir / filename
        with open(input_path) as f:
            return json.load(f)


class BaseWorkflowIntegrationTest:
    """Base class for workflow integration tests."""

    workflow_class: Optional[Type] = None
    __test__ = False  # Prevent pytest from collecting this base class

    @pytest.fixture
    def mock_workflow(self, temp_data_dir: Path) -> MagicMock:
        """Create a mock workflow instance.

        Args:
            temp_data_dir: Temporary directory for test data.

        Returns:
            A mock workflow instance.
        """
        if not self.workflow_class:
            raise ValueError("workflow_class must be set in the test class")

        workflow = self.workflow_class(
            data_dir=temp_data_dir,
            search_engine=MockSearchEngine(),
            analysis_engine=MockAnalysisEngine(),
        )
        return workflow

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create a temporary data directory.

        Args:
            tmp_path: pytest's temporary path fixture.

        Returns:
            Path to the temporary data directory.
        """
        data_dir = tmp_path / "test_data"
        data_dir.mkdir()
        return data_dir

    @pytest.fixture
    def sample_companies_csv(self, temp_data_dir: Path) -> Path:
        """Create a sample companies CSV file.

        Args:
            temp_data_dir: Temporary directory for test data.

        Returns:
            Path to the sample CSV file.
        """
        csv_path = temp_data_dir / "companies.csv"
        csv_content = (
            "Company,Symbol,Category,Criteria\n"
            "Test Company 1,TC1,Test,Test Criteria 1\n"
            "Test Company 2,TC2,Test,Test Criteria 2\n"
        )
        with open(csv_path, "w") as f:
            f.write(csv_content)
        return csv_path
