"""Tests for database configuration module.

This module tests the database configuration functions.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import os
import tempfile
from pathlib import Path

import pytest

from src.dewey.core.db.config import (
    get_db_config,
    validate_config,
    initialize_environment,
    setup_logging,
    get_connection_string,
    set_test_mode
)

class TestDatabaseConfig(unittest.TestCase):
    """Test database configuration module."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for config
        self.temp_dir = tempfile.mkdtemp()
        
        # Enable test mode to skip file operations
        set_test_mode(True)
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'DEWEY_LOCAL_DB': '/path/to/db',
            'DEWEY_MOTHERDUCK_DB': 'md:test',
            'MOTHERDUCK_TOKEN': 'test_token'
        })
        self.mock_env = self.env_patcher.start()
        
        # Mock dotenv load
        self.dotenv_patcher = patch('src.dewey.core.db.config.load_dotenv')
        self.mock_dotenv = self.dotenv_patcher.start()
        self.mock_dotenv.return_value = True
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Disable test mode
        set_test_mode(False)
        
        self.env_patcher.stop()
        self.dotenv_patcher.stop()
        
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_get_db_config(self):
        """Test getting database configuration."""
        # Get config
        config = get_db_config()
        
        # Check that config contains expected values
        self.assertEqual(config['local_db_path'], '/path/to/db')
        self.assertEqual(config['motherduck_db'], 'md:test')
        self.assertEqual(config['motherduck_token'], 'test_token')
    
    def test_validate_config(self):
        """Test validating configuration."""
        # Valid config
        result = validate_config()
        self.assertTrue(result)
        
        # Test with missing required values
        with patch.dict('os.environ', {'DEWEY_LOCAL_DB': '', 'DEWEY_MOTHERDUCK_DB': ''}):
            with self.assertRaises(Exception):
                validate_config()
    
    def test_initialize_environment(self):
        """Test initializing environment."""
        # Initialize environment
        result = initialize_environment()
        
        # Check result
        self.assertTrue(result)
        
        # Check that dotenv was loaded
        self.mock_dotenv.assert_called_once()
    
    def test_setup_logging(self):
        """Test setting up logging."""
        # Set up logging
        with patch('logging.basicConfig') as mock_config:
            setup_logging()
            
            # Check that basicConfig was called
            mock_config.assert_called_once()
    
    def test_get_connection_string(self):
        """Test getting connection string."""
        # Get local connection string
        conn_str = get_connection_string(local_only=True)
        self.assertEqual(conn_str, '/path/to/db')
        
        # Get MotherDuck connection string
        conn_str = get_connection_string(local_only=False)
        self.assertEqual(conn_str, 'md:test?motherduck_token=test_token')
        
        # Test with no token
        with patch.dict('os.environ', {'MOTHERDUCK_TOKEN': ''}):
            conn_str = get_connection_string(local_only=False)
            self.assertEqual(conn_str, 'md:test')

if __name__ == '__main__':
    unittest.main() 