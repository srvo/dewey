"""Unit tests for the BaseEngine class."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.research.engines.base import BaseEngine
from dewey.core.base_script import BaseScript


class TestBaseEngine(unittest.TestCase):
    """Test suite for the BaseEngine class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a subclass to use the engine (which has an abstract run method)
        class ConcreteEngine(BaseEngine):
            def run(self):
                return "test_run"
        
        # Setup mocks
        self.mock_logger = MagicMock()
        self.mock_config = {"test_key": "test_value"}
        
        # Monkey patch the BaseScript._setup_logging and _load_config methods
        original_setup_logging = BaseScript._setup_logging
        original_load_config = BaseScript._load_config
        
        def mock_setup_logging(instance):
            instance.logger = self.mock_logger
            
        def mock_load_config(instance):
            return self.mock_config
        
        # Apply the patches
        BaseScript._setup_logging = mock_setup_logging
        BaseScript._load_config = mock_load_config
        
        # Create the engine with our mocked methods
        self.engine = ConcreteEngine(config_section="test_engine")
        
        # Restore the original methods after creating the instance
        BaseScript._setup_logging = original_setup_logging
        BaseScript._load_config = original_load_config
        
        # Reset mock calls that happened during initialization
        self.mock_logger.reset_mock()
        
    def test_initialization(self):
        """Test that the engine initializes correctly."""
        self.assertEqual(self.engine.config_section, "test_engine")
        self.assertEqual(self.engine.config, self.mock_config)
        
    def test_get_config_value(self):
        """Test that get_config_value returns the correct values."""
        # Test getting an existing value
        value = self.engine.get_config_value("test_key")
        self.assertEqual(value, "test_value")
        
        # Test getting a non-existent value with default
        value = self.engine.get_config_value("non_existent_key", "default_value")
        self.assertEqual(value, "default_value")
        
    def test_logging_methods(self):
        """Test that the logging methods call the logger correctly."""
        # Test info method
        self.engine.info("test info message")
        self.engine.logger.info.assert_called_once_with("test info message")
        self.mock_logger.reset_mock()
        
        # Test error method
        self.engine.error("test error message")
        self.engine.logger.error.assert_called_once_with("test error message")
        self.mock_logger.reset_mock()
        
        # Test debug method
        self.engine.debug("test debug message")
        self.engine.logger.debug.assert_called_once_with("test debug message")
        self.mock_logger.reset_mock()
        
        # Test warning method
        self.engine.warning("test warning message")
        self.engine.logger.warning.assert_called_once_with("test warning message")
        
    @patch("dewey.core.base_script.BaseScript.setup_argparse")
    def test_setup_argparse(self, mock_setup_argparse):
        """Test that setup_argparse adds the correct arguments."""
        mock_parser = MagicMock()
        mock_setup_argparse.return_value = mock_parser
        
        parser = self.engine.setup_argparse()
        
        mock_parser.add_argument.assert_called_once_with(
            "--engine-config",
            help="Path to engine configuration file (overrides default config)",
        )
        self.assertEqual(parser, mock_parser)
        
    @patch("dewey.core.base_script.BaseScript.parse_args")
    def test_parse_args(self, mock_base_parse_args):
        """Test that parse_args handles engine-config argument correctly."""
        # Setup mock return value for base class parse_args
        mock_args = MagicMock()
        mock_args.engine_config = "test_config.yaml"
        mock_base_parse_args.return_value = mock_args
        
        # Mock Path.exists to return True
        with patch('pathlib.Path.exists', return_value=True):
            # Mock the engine's _load_config method
            with patch.object(self.engine, '_load_config') as mock_load_config:
                # Call parse_args
                result = self.engine.parse_args()
                
                # Verify assertions
                self.assertEqual(result, mock_args)
                mock_load_config.assert_called_once_with()  # No arguments expected here
        
    @patch("dewey.core.base_script.BaseScript.parse_args")
    def test_parse_args_file_not_found(self, mock_base_parse_args):
        """Test that parse_args raises FileNotFoundError when config file doesn't exist."""
        # Setup mock return value for base class parse_args
        mock_args = MagicMock()
        mock_args.engine_config = "non_existent_config.yaml"
        mock_base_parse_args.return_value = mock_args
        
        # Mock Path.exists to return False
        with patch('pathlib.Path.exists', return_value=False):
            # Mock the engine's _load_config method
            with patch.object(self.engine, '_load_config') as mock_load_config:
                # Call parse_args and verify that it raises FileNotFoundError
                with pytest.raises(FileNotFoundError):
                    self.engine.parse_args()
                
                # Verify that _load_config was not called
                mock_load_config.assert_not_called()
        
    def test_run_not_implemented(self):
        """Test that the run method is abstract and must be implemented by subclasses."""
        # DirectBaseEngine is a direct subclass that doesn't implement the required methods
        # We need to trick Python's abstract base class mechanism
        BaseEngine.__abstractmethods__ = frozenset()  # temporarily empty the abstractmethods
        
        try:
            engine = BaseEngine()
            with pytest.raises(NotImplementedError):
                engine.run()
        finally:
            # Restore the abstractmethods
            BaseEngine.__abstractmethods__ = frozenset(['run']) 