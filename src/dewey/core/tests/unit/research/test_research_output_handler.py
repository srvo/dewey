"""Unit tests for the ResearchOutputHandler class."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dewey.core.research.research_output_handler import ResearchOutputHandler
from dewey.core.base_script import BaseScript


class TestResearchOutputHandler(unittest.TestCase):
    """Test suite for the ResearchOutputHandler class."""

    @patch("dewey.core.base_script.BaseScript._load_config")
    def setUp(self, mock_load_config):
        """Set up test fixtures."""
        # Create a mock logger
        self.mock_logger = MagicMock()
        
        # Monkey patch the BaseScript._setup_logging method
        original_setup_logging = BaseScript._setup_logging
        
        def mock_setup_logging(instance):
            instance.logger = self.mock_logger
            
        # Apply the patch
        BaseScript._setup_logging = mock_setup_logging
        
        self.mock_config = {"output_dir": "test_output"}
        mock_load_config.return_value = self.mock_config
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Initialize the handler with the temp directory
        self.handler = ResearchOutputHandler(output_dir=self.temp_dir.name)
        
        # Restore the original method
        BaseScript._setup_logging = original_setup_logging
        
        # Test data
        self.test_data = {"test_key": "test_value", "nested": {"key": "value"}}
        
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
        
    def test_initialization(self):
        """Test that the handler initializes correctly."""
        # Create a mock logger
        mock_logger = MagicMock()
        
        # Monkey patch the BaseScript._setup_logging method
        original_setup_logging = BaseScript._setup_logging
        
        def mock_setup_logging(instance):
            instance.logger = mock_logger
            
        # Apply the patch
        BaseScript._setup_logging = mock_setup_logging
        
        try:
            # Test with default config
            with patch("dewey.core.base_script.BaseScript._load_config") as mock_load_config:
                mock_load_config.return_value = {"output_dir": "test_output"}
                handler = ResearchOutputHandler()
                self.assertEqual(handler.output_dir, Path("test_output"))
            
            # Test with custom output_dir
            with patch("dewey.core.base_script.BaseScript._load_config") as mock_load_config:
                mock_load_config.return_value = {"output_dir": "test_output"}
                handler = ResearchOutputHandler(output_dir="/custom/path")
                self.assertEqual(handler.output_dir, Path("/custom/path"))
        finally:
            # Restore the original method
            BaseScript._setup_logging = original_setup_logging
        
    @patch("dewey.core.research.research_output_handler.ResearchOutputHandler.write_output")
    def test_run(self, mock_write_output):
        """Test the run method."""
        # Set up a mock config value for output_path
        self.handler.get_config_value = MagicMock()
        self.handler.get_config_value.side_effect = lambda key, default=None: {
            "output_path": "test_output.json",
            "output_data": {"key": "value"}
        }.get(key, default)
        
        # Run the handler
        self.handler.run()
        
        # Verify that write_output was called with the correct arguments
        mock_write_output.assert_called_once_with("test_output.json", {"key": "value"})
        
    def test_save_results(self):
        """Test saving results to a file."""
        # Generate a test output file path
        test_file = self.temp_path / "test_results.json"
        
        # Save results
        self.handler.save_results(self.test_data, test_file)
        
        # Verify the file exists
        self.assertTrue(test_file.exists())
        
        # Read the file and verify contents
        with open(test_file) as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data, self.test_data)
        
    def test_save_results_error(self):
        """Test error handling when saving results."""
        # Mock open to raise an exception
        with patch("builtins.open", side_effect=Exception("Test error")):
            # Save results
            self.handler.save_results(self.test_data, self.temp_path / "error.json")
            
            # Verify that error was logged
            self.handler.logger.error.assert_called_once()
            
    def test_load_results(self):
        """Test loading results from a file."""
        # Create a test file with known contents
        test_file = self.temp_path / "test_load.json"
        with open(test_file, "w") as f:
            json.dump(self.test_data, f)
            
        # Load results
        results = self.handler.load_results(test_file)
        
        # Verify the loaded data
        self.assertEqual(results, self.test_data)
        
    def test_load_results_file_not_found(self):
        """Test loading results when the file doesn't exist."""
        # Load results from a non-existent file
        results = self.handler.load_results(self.temp_path / "non_existent.json")
        
        # Verify that an empty dict was returned
        self.assertEqual(results, {})
        
        # Verify that a warning was logged
        self.handler.logger.warning.assert_called_once()
        
    def test_load_results_error(self):
        """Test error handling when loading results."""
        # Create a test file with invalid JSON
        test_file = self.temp_path / "invalid.json"
        with open(test_file, "w") as f:
            f.write("This is not valid JSON")
            
        # Load results
        results = self.handler.load_results(test_file)
        
        # Verify that an empty dict was returned
        self.assertEqual(results, {})
        
        # Verify that an error was logged
        self.handler.logger.error.assert_called_once()
        
    def test_write_output_json(self):
        """Test writing output to a JSON file."""
        # Generate a test output file path
        test_file = self.temp_path / "test_output.json"
        
        # Write output
        self.handler.write_output(str(test_file), self.test_data)
        
        # Verify the file exists
        self.assertTrue(test_file.exists())
        
        # Read the file and verify contents
        with open(test_file) as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data, self.test_data)
        
    def test_write_output_text(self):
        """Test writing output to a text file."""
        # Generate a test output file path
        test_file = self.temp_path / "test_output.txt"
        
        # Write output
        self.handler.write_output(str(test_file), self.test_data)
        
        # Verify the file exists
        self.assertTrue(test_file.exists())
        
        # Read the file and verify contents
        with open(test_file) as f:
            content = f.read()
        
        self.assertEqual(content, str(self.test_data))
        
    def test_write_output_error(self):
        """Test error handling when writing output."""
        # Mock open to raise an exception
        with patch("builtins.open", side_effect=Exception("Test error")):
            # Expect an exception to be raised
            with self.assertRaises(Exception):
                self.handler.write_output(str(self.temp_path / "error.txt"), self.test_data)
                
            # Verify that error was logged
            self.handler.logger.error.assert_called_once() 