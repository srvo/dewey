"""Tests for database initialization module.

This module tests the database initialization and setup functions.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import os
from datetime import datetime

import pytest

from src.dewey.core.db import (
    initialize_database,
    get_database_info,
    close_database
)

class TestDatabaseInitialization(unittest.TestCase):
    """Test database initialization module."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock modules
        self.config_patcher = patch('src.dewey.core.db.initialize_environment')
        self.mock_config = self.config_patcher.start()
        
        self.db_manager_patcher = patch('src.dewey.core.db.db_manager')
        self.mock_db_manager = self.db_manager_patcher.start()
        
        self.schema_patcher = patch('src.dewey.core.db.initialize_schema')
        self.mock_schema = self.schema_patcher.start()
        
        self.sync_patcher = patch('src.dewey.core.db.sync_all_tables')
        self.mock_sync = self.sync_patcher.start()
        
        # Mock module imports
        self.monitor_module_patcher = patch('src.dewey.core.db.monitor')
        self.mock_monitor = self.monitor_module_patcher.start()
        self.mock_monitor.stop_monitoring = MagicMock()
        self.mock_monitor.monitor_database = MagicMock()
        
        # Mock thread
        self.thread_patcher = patch('src.dewey.core.db.threading.Thread')
        self.mock_thread_class = self.thread_patcher.start()
        self.mock_thread = MagicMock()
        self.mock_thread_class.return_value = self.mock_thread
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.config_patcher.stop()
        self.db_manager_patcher.stop()
        self.schema_patcher.stop()
        self.sync_patcher.stop()
        self.monitor_module_patcher.stop()
        self.thread_patcher.stop()
    
    def test_initialize_database(self):
        """Test initialize_database function."""
        # Set up mocks
        self.mock_config.return_value = True  # initialize_environment returns True
        self.mock_schema.return_value = True  # Initialize schema directly
        
        # Initialize database
        result = initialize_database(motherduck_token="test_token")
        
        # Check result
        self.assertTrue(result)
        
        # Check that the environment was initialized with token
        self.mock_config.assert_called_once_with("test_token")
        
        # Check that schema was initialized
        self.mock_schema.assert_called_once()
        
        # Check that monitoring was started
        self.mock_thread_class.assert_called_once()
        self.mock_thread.start.assert_called_once()
    
    def test_initialize_database_failure(self):
        """Test initialize_database with failure."""
        # Set up mocks to simulate failures
        self.mock_config.side_effect = Exception("Config error")
        
        # Initialize database
        result = initialize_database()
        
        # Check result
        self.assertFalse(result)
        
        # Initialize should fail at first step
        self.mock_schema.apply_migrations.assert_not_called()
        self.mock_thread_class.assert_not_called()
        
    def test_get_database_info(self):
        """Test get_database_info function."""
        # Mock health, backup, sync functions
        mock_health = {'status': 'healthy'}
        mock_backups = [{'filename': 'backup1.duckdb'}]
        mock_sync = {'tables': [{'table_name': 'table1'}]}
        
        with patch('src.dewey.core.db.monitor.run_health_check') as mock_health_func:
            mock_health_func.return_value = mock_health
            
            with patch('src.dewey.core.db.list_backups') as mock_backup_func:
                mock_backup_func.return_value = mock_backups
                
                with patch('src.dewey.core.db.sync.get_last_sync_time') as mock_sync_func:
                    mock_sync_func.return_value = datetime.now()
                    
                    # Get database info
                    info = get_database_info()
                    
                    # Check result
                    self.assertEqual(info['health'], mock_health)
                    self.assertEqual(info['backups']['latest'], mock_backups[0])
                    
                    # Check that functions were called
                    mock_health_func.assert_called_once()
                    mock_backup_func.assert_called_once()
                    mock_sync_func.assert_called_once()
    
    def test_get_database_info_failure(self):
        """Test get_database_info with failure."""
        # Mock health function to raise an exception
        with patch('src.dewey.core.db.monitor.run_health_check') as mock_health_func:
            mock_health_func.side_effect = Exception("Health check failed")
            
            # Get database info
            info = get_database_info()
            
            # Check result
            self.assertIn('error', info)
            self.assertEqual(info['error'], 'Health check failed')
    
    def test_close_database(self):
        """Test close_database function."""
        # Close database
        close_database()
        
        # Check that db_manager.close was called
        self.mock_db_manager.close.assert_called_once()
        
        # Check that monitoring was stopped
        self.mock_monitor.stop_monitoring.assert_called_once()

if __name__ == '__main__':
    unittest.main() 