"""Unit tests for the ResearchScript class."""

import unittest
from unittest.mock import MagicMock, patch

import pytest
from dewey.core.base_script import BaseScript
from dewey.core.research import ResearchScript


class TestResearchScript(unittest.TestCase):
    """Test suite for the ResearchScript class."""

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

        # We need to create a concrete implementation since ResearchScript is abstract
        class ConcreteResearchScript(ResearchScript):
            def run(self):
                return "success"

        self.mock_config = {"test_key": "test_value"}
        mock_load_config.return_value = self.mock_config

        # Initialize the script
        self.script = ConcreteResearchScript(config_section="test_research")

        # Restore the original method
        BaseScript._setup_logging = original_setup_logging

    def test_initialization(self):
        """Test that the script initializes correctly."""
        self.assertEqual(self.script.config_section, "test_research")
        self.assertEqual(self.script.config, self.mock_config)

    def test_example_method(self):
        """Test the example_method method."""
        # Test with default config
        result = self.script.example_method("test input")

        # Verify the result
        self.assertEqual(result, "Processed: test input - None")

        # Verify that the logger was called
        self.script.logger.info.assert_called_with(
            "Processing data: test input with config: None",
        )

    @patch("dewey.core.base_script.BaseScript._load_config")
    def test_run_not_implemented(self, mock_load_config):
        """Test that run method raises NotImplementedError if not overridden."""
        # Create a mock logger
        mock_logger = MagicMock()

        # Monkey patch the BaseScript._setup_logging method
        original_setup_logging = BaseScript._setup_logging

        def mock_setup_logging(instance):
            instance.logger = mock_logger

        # Apply the patch
        BaseScript._setup_logging = mock_setup_logging

        try:
            mock_load_config.return_value = {}

            script = ResearchScript(config_section="test_research")

            with pytest.raises(NotImplementedError):
                script.run()
        finally:
            # Restore the original method
            BaseScript._setup_logging = original_setup_logging
