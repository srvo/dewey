"""Tests for database configuration."""
import pytest
from unittest.mock import patch
import os
from pathlib import Path

from dewey.core.db.config import (
    get_db_config,
    get_connection_string
)

class TestDatabaseConfig:
    """Test suite for database configuration."""

    def test_get_db_config_defaults(self):
        """Test getting database configuration with defaults."""
        config = get_db_config()
        
        # Verify required keys
        assert 'local_db_path' in config
        assert 'motherduck_db' in config
        assert 'pool_size' in config
        assert 'max_retries' in config
        assert 'retry_delay' in config
        assert 'sync_interval' in config
        assert 'max_sync_age' in config
        assert 'backup_dir' in config
        assert 'backup_retention_days' in config
        
        # Verify default values
        assert isinstance(config['pool_size'], int)
        assert isinstance(config['max_retries'], int)
        assert isinstance(config['retry_delay'], int)
        assert isinstance(config['sync_interval'], int)
        assert isinstance(config['max_sync_age'], int)
        assert isinstance(config['backup_retention_days'], int)

    def test_get_db_config_with_env(self, mock_env_vars):
        """Test configuration with environment variables."""
        config = get_db_config()
        
        # Verify environment variables were used
        assert config['local_db_path'] == ':memory:'
        assert config['motherduck_db'] == 'md:dewey_test'
        assert config['pool_size'] == 2
        assert config['max_retries'] == 2
        assert config['retry_delay'] == 0.1
        assert config['sync_interval'] == 60
        assert config['max_sync_age'] == 3600
        assert config['backup_retention_days'] == 1

    def test_get_connection_string_local(self):
        """Test getting local connection string."""
        conn_str = get_connection_string(local_only=True)
        assert isinstance(conn_str, str)
        assert not conn_str.startswith('md:')

    def test_get_connection_string_motherduck(self):
        """Test getting MotherDuck connection string."""
        conn_str = get_connection_string(local_only=False)
        assert isinstance(conn_str, str)
        assert conn_str.startswith('md:')

    def test_config_path_expansion(self):
        """Test path expansion in configuration."""
        with patch.dict('os.environ', {'DEWEY_LOCAL_DB': '~/dewey.duckdb'}):
            config = get_db_config()
            assert '~' not in config['local_db_path']
            assert str(Path.home()) in config['local_db_path']

    def test_config_validation(self):
        """Test configuration validation."""
        with patch.dict('os.environ', {'DEWEY_DB_POOL_SIZE': 'invalid'}):
            # Should fall back to default value
            config = get_db_config()
            assert isinstance(config['pool_size'], int)
            assert config['pool_size'] > 0

    def test_backup_dir_creation(self):
        """Test backup directory creation."""
        test_backup_dir = '/tmp/dewey_test_backups'
        with patch.dict('os.environ', {'DEWEY_BACKUP_DIR': test_backup_dir}):
            config = get_db_config()
            assert os.path.exists(config['backup_dir'])
            os.rmdir(test_backup_dir)  # Clean up

@pytest.mark.integration
class TestDatabaseConfigIntegration:
    """Integration tests for database configuration."""

    def test_full_config_workflow(self, tmp_path):
        """Test complete configuration workflow."""
        # Set up test environment
        test_env = {
            'DEWEY_LOCAL_DB': str(tmp_path / 'test.duckdb'),
            'DEWEY_MOTHERDUCK_DB': 'md:dewey_test',
            'MOTHERDUCK_TOKEN': 'test_token',
            'DEWEY_DB_POOL_SIZE': '3',
            'DEWEY_BACKUP_DIR': str(tmp_path / 'backups')
        }
        
        with patch.dict('os.environ', test_env):
            # Get configuration
            config = get_db_config()
            
            # Verify paths were created
            assert os.path.exists(os.path.dirname(config['local_db_path']))
            assert os.path.exists(config['backup_dir'])
            
            # Test connection strings
            local_conn = get_connection_string(local_only=True)
            assert local_conn == str(tmp_path / 'test.duckdb')
            
            cloud_conn = get_connection_string(local_only=False)
            assert cloud_conn == 'md:dewey_test' 