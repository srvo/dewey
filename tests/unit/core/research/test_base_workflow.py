"""Unit tests for the BaseWorkflow class."""

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dewey.core.research.base_workflow import BaseWorkflow


class TestBaseWorkflow(unittest.TestCase):
    """Test suite for the BaseWorkflow class."""

    @patch("dewey.core.base_script.BaseScript._load_config")
    @patch("dewey.core.research.base_workflow.BaseEngine")
    @patch("dewey.core.research.base_workflow.ResearchOutputHandler")
    def setUp(self, mock_output_handler, mock_base_engine, mock_load_config):
        """Set up test fixtures."""
        # Import BaseScript after we've patched it
        from dewey.core.base_script import BaseScript

        # We need to create a concrete implementation since BaseWorkflow is abstract
        class ConcreteWorkflow(BaseWorkflow):
            def execute(self, data_dir=None):
                return {"status": "success"}

            def run(self):
                self.execute()

        # Create a mock logger
        self.mock_logger = MagicMock()

        # Monkey patch the BaseScript._setup_logging method
        original_setup_logging = BaseScript._setup_logging

        def mock_setup_logging(instance):
            instance.logger = self.mock_logger

        # Apply the patch
        BaseScript._setup_logging = mock_setup_logging

        self.mock_config = {"test_key": "test_value"}
        mock_load_config.return_value = self.mock_config

        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Set up mocks
        self.mock_search_engine = MagicMock()
        self.mock_analysis_engine = MagicMock()
        self.mock_output_handler = MagicMock()

        # Initialize the workflow
        self.workflow = ConcreteWorkflow(
            search_engine=self.mock_search_engine,
            analysis_engine=self.mock_analysis_engine,
            output_handler=self.mock_output_handler,
        )

        # Restore the original method
        BaseScript._setup_logging = original_setup_logging

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()

    def test_initialization(self):
        """Test that the workflow initializes correctly."""
        self.assertEqual(self.workflow.search_engine, self.mock_search_engine)
        self.assertEqual(self.workflow.analysis_engine, self.mock_analysis_engine)
        self.assertEqual(self.workflow.output_handler, self.mock_output_handler)

    def test_read_companies_success(self):
        """Test reading companies from a CSV file."""
        # Create a test CSV file
        test_file = self.temp_path / "companies.csv"
        test_data = [
            {"ticker": "AAPL", "name": "Apple Inc."},
            {"ticker": "MSFT", "name": "Microsoft Corp."},
            {"ticker": "GOOG", "name": "Alphabet Inc."},
        ]

        with open(test_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ticker", "name"])
            writer.writeheader()
            writer.writerows(test_data)

        # Read companies
        companies = list(self.workflow.read_companies(test_file))

        # Verify the data
        self.assertEqual(len(companies), 3)
        self.assertEqual(companies[0]["ticker"], "AAPL")
        self.assertEqual(companies[1]["name"], "Microsoft Corp.")

    def test_read_companies_file_not_found(self):
        """Test reading companies when the file doesn't exist."""
        # Attempt to read from a non-existent file
        with pytest.raises(FileNotFoundError):
            list(self.workflow.read_companies(self.temp_path / "non_existent.csv"))

        # Verify that an error was logged
        self.workflow.logger.error.assert_called_once()

    def test_read_companies_error(self):
        """Test error handling when reading companies."""
        # Create a test file path
        test_file = self.temp_path / "test.csv"

        # Mock open to raise an Exception
        with patch("builtins.open", side_effect=Exception("Simulated error")):
            # Attempt to read from the file
            with pytest.raises(Exception):
                list(self.workflow.read_companies(test_file))

            # Verify that an error was logged
            self.workflow.logger.error.assert_called_once()
