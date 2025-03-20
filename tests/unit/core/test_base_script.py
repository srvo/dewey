"""Test suite for the BaseScript class."""

import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from dewey.core.base_script import BaseScript, PROJECT_ROOT


class TestScript(BaseScript):
    """Test implementation of BaseScript for testing purposes."""
    
    def __init__(
        """Function __init__."""
        self,
        name='test_script',
        description='Test script for unit tests',
        config_section=None,
        requires_db=False,
        enable_llm=False,
    ):
        self.run_called = False
        super().__init__(
            name=name,
            description=description,
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )
    
    def run(self):
        """Implementation of the required run method."""
        self.run_called = True
        return "Test run completed"


class BaseScriptTests(unittest.TestCase):
    """Test cases for BaseScript class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary config file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_config_path = Path(self.temp_dir.name) / "test_config.yaml"
        self.test_config = {
            'core': {
                'logging': {
                    'level': 'INFO',
                    'format': '%(levelname)s - %(message)s',
                    'date_format': '%Y-%m-%d'
                },
                'database': {
                    'connection_string': 'mock://database'
                }
            },
            'llm': {
                'model': 'test-model',
                'api_key': 'test-key'
            },
            'test_section': {
                'test_key': 'test_value'
            }
        }
        
        with open(self.temp_config_path, 'w') as f:
            yaml.dump(self.test_config, f)
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    @patch('dewey.core.base_script.load_dotenv')
    def test_initialization(self, mock_load_dotenv, mock_config_path):
        """Test basic initialization of BaseScript."""
        mock_config_path.return_value = self.temp_config_path
        
        # Test basic initialization
        script = TestScript()
        
        self.assertEqual(script.name, 'test_script')
        self.assertEqual(script.description, 'Test script for unit tests')
        self.assertIsNone(script.config_section)
        self.assertFalse(script.requires_db)
        self.assertFalse(script.enable_llm)
        self.assertIsNotNone(script.logger)
        self.assertIsNotNone(script.config)
        self.assertIsNone(script.db_conn)
        self.assertIsNone(script.llm_client)
        
        # Verify dotenv was loaded
        mock_load_dotenv.assert_called_once()
    
    @patch('dewey.core.base_script.CONFIG_PATH', new_callable=lambda: Path('nonexistent_file.yaml'))
    def test_config_loading_failure(self, _):
        """Test behavior when config file doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            TestScript()
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    def test_section_specific_config(self, mock_config_path):
        """Test loading a specific config section."""
        mock_config_path.return_value = self.temp_config_path
        
        # Test with a valid section
        script = TestScript(config_section='test_section')
        self.assertEqual(script.config, {'test_key': 'test_value'})
        
        # Test with a non-existent section
        script = TestScript(config_section='nonexistent_section')
        self.assertEqual(script.config, self.test_config)
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    @patch('dewey.core.db.connection.get_connection')
    def test_db_initialization(self, mock_get_connection, mock_config_path):
        """Test database connection initialization."""
        mock_config_path.return_value = self.temp_config_path
        mock_db_conn = MagicMock()
        mock_get_connection.return_value = mock_db_conn
        
        script = TestScript(requires_db=True)
        
        mock_get_connection.assert_called_once_with(self.test_config['core']['database'])
        self.assertEqual(script.db_conn, mock_db_conn)
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    @patch('dewey.llm.llm_utils.get_llm_client')
    def test_llm_initialization(self, mock_get_llm_client, mock_config_path):
        """Test LLM client initialization."""
        mock_config_path.return_value = self.temp_config_path
        mock_llm_client = MagicMock()
        mock_get_llm_client.return_value = mock_llm_client
        
        script = TestScript(enable_llm=True)
        
        mock_get_llm_client.assert_called_once_with(self.test_config['llm'])
        self.assertEqual(script.llm_client, mock_llm_client)
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    def test_argparse_setup(self, mock_config_path):
        """Test argument parser setup."""
        mock_config_path.return_value = self.temp_config_path
        
        # Basic script
        script = TestScript()
        parser = script.setup_argparse()
        
        self.assertIsInstance(parser, argparse.ArgumentParser)
        self.assertEqual(parser.description, 'Test script for unit tests')
        
        # Script with database
        script_with_db = TestScript(requires_db=True)
        parser_with_db = script_with_db.setup_argparse()
        
        # Verify db-specific arguments
        self.assertTrue(any(action.dest == 'db_connection_string' for action in parser_with_db._actions))
        
        # Script with LLM
        script_with_llm = TestScript(enable_llm=True)
        parser_with_llm = script_with_llm.setup_argparse()
        
        # Verify llm-specific arguments
        self.assertTrue(any(action.dest == 'llm_model' for action in parser_with_llm._actions))
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    @patch('argparse.ArgumentParser.parse_args')
    def test_parse_args(self, mock_parse_args, mock_config_path):
        """Test argument parsing."""
        mock_config_path.return_value = self.temp_config_path
        
        # Create mock args
        mock_args = MagicMock()
        mock_args.log_level = 'DEBUG'
        mock_args.config = None
        mock_parse_args.return_value = mock_args
        
        script = TestScript()
        args = script.parse_args()
        
        self.assertEqual(args, mock_args)
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    @patch('sys.exit')
    def test_execute_method(self, mock_exit, mock_config_path):
        """Test execute method."""
        mock_config_path.return_value = self.temp_config_path
        
        script = TestScript()
        script.execute()
        
        self.assertTrue(script.run_called)
        mock_exit.assert_not_called()
        
        # Test with exception
        script_with_error = TestScript()
        script_with_error.run = MagicMock(side_effect=Exception("Test error"))
        
        script_with_error.execute()
        mock_exit.assert_called_once_with(1)
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    def test_get_path(self, mock_config_path):
        """Test get_path method."""
        mock_config_path.return_value = self.temp_config_path
        
        script = TestScript()
        
        # Test with relative path
        relative_path = script.get_path('relative/path')
        self.assertEqual(relative_path, PROJECT_ROOT / 'relative/path')
        
        # Test with absolute path
        abs_path = '/absolute/path'
        absolute_path = script.get_path(abs_path)
        self.assertEqual(str(absolute_path), abs_path)
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    def test_get_config_value(self, mock_config_path):
        """Test get_config_value method."""
        mock_config_path.return_value = self.temp_config_path
        
        script = TestScript()
        
        # Test with existing nested key
        value = script.get_config_value('core.logging.level')
        self.assertEqual(value, 'INFO')
        
        # Test with non-existent key
        value = script.get_config_value('nonexistent.key', 'default')
        self.assertEqual(value, 'default')
        
        # Test with non-existent nested key
        value = script.get_config_value('core.nonexistent.key', 'default')
        self.assertEqual(value, 'default')
    
    @patch('dewey.core.base_script.CONFIG_PATH')
    def test_cleanup(self, mock_config_path):
        """Test cleanup method."""
        mock_config_path.return_value = self.temp_config_path
        
        script = TestScript(requires_db=True)
        script.db_conn = MagicMock()
        
        script._cleanup()
        
        script.db_conn.close.assert_called_once()
        
        # Test with exception during close
        script.db_conn.close.side_effect = Exception("Close error")
        
        # This should not raise an exception
        script._cleanup()


if __name__ == '__main__':
    unittest.main() 