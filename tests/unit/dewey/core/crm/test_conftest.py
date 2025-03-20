"""Unit tests for dewey.core.crm.conftest module."""

import os
from typing import Generator
from unittest.mock import Mock, patch

import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.crm.conftest import TestConfiguration, mock_duckdb, mock_env_vars, setup_test_db


class TestTestConfiguration:
    """Tests for the TestConfiguration class."""

    def test_init(self):
        """Test the __init__ method."""
        test_config = TestConfiguration()
        assert test_config.config_section == 'test_config'
        assert isinstance(test_config, BaseScript)

    def test_mock_env_vars(self):
        """Test the mock_env_vars method."""
        test_config = TestConfiguration()
        with patch.dict(os.environ, clear=True):
            with test_config.mock_env_vars():
                assert os.environ['MOTHERDUCK_TOKEN'] == 'test_token'
                assert os.environ['DEWEY_HOME'] == '/tmp/dewey_test'

    def test_setup_test_db(self, tmpdir):
        """Test the setup_test_db method."""
        test_config = TestConfiguration()
        test_dir = str(tmpdir.mkdir('dewey_test'))
        with patch('os.makedirs', return_value=None), \
             patch('os.remove', return_value=None), \
             patch('dewey.core.crm.conftest.TestConfiguration.logger') as mock_logger:
            with test_config.setup_test_db():
                assert os.path.exists(test_dir)
            mock_logger.info.assert_not_called()

    def test_setup_test_db_file_not_found(self, tmpdir):
        """Test the setup_test_db method when the database file is not found."""
        test_config = TestConfiguration()
        test_dir = str(tmpdir.mkdir('dewey_test'))
        db_file = os.path.join(test_dir, 'dewey.duckdb')
        with patch('os.makedirs', return_value=None), \
             patch('os.remove', side_effect=FileNotFoundError), \
             patch('dewey.core.crm.conftest.TestConfiguration.logger') as mock_logger:
            with test_config.setup_test_db():
                assert os.path.exists(test_dir)
            mock_logger.info.assert_called_once()

    def test_mock_duckdb(self):
        """Test the mock_duckdb method."""
        test_config = TestConfiguration()
        with patch('duckdb.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            with test_config.mock_duckdb() as conn:
                assert conn == mock_conn

    def test_run(self):
        """Test the run method."""
        test_config = TestConfiguration()
        test_config.run()  # The run method is a placeholder, so just call it to ensure it exists.

    def test_get_config_value(self):
        """Test the get_config_value method."""
        test_config = TestConfiguration()
        config_data = {'section': {'key1': 'value1', 'key2': 123}}
        test_config.config = config_data
        assert test_config.get_config_value('section.key1') == 'value1'
        assert test_config.get_config_value('section.key2') == 123
        assert test_config.get_config_value('section.key3', 'default') == 'default'
        assert test_config.get_config_value('nonexistent_section.key', 'default') == 'default'

    def test_get_config_value_no_default(self):
        """Test the get_config_value method when the key doesn't exist and no default is provided."""
        test_config = TestConfiguration()
        config_data = {'section': {'key1': 'value1'}}
        test_config.config = config_data
        assert test_config.get_config_value('section.nonexistent_key') is None
        assert test_config.get_config_value('nonexistent_section.key') is None


class TestFixtures:
    """Tests for the pytest fixtures."""

    def test_mock_env_vars_fixture(self):
        """Test the mock_env_vars fixture."""
        with patch.dict(os.environ, clear=True):
            with mock_env_vars():
                assert os.environ['MOTHERDUCK_TOKEN'] == 'test_token'
                assert os.environ['DEWEY_HOME'] == '/tmp/dewey_test'

    def test_setup_test_db_fixture(self, tmpdir):
        """Test the setup_test_db fixture."""
        test_dir = str(tmpdir.mkdir('dewey_test'))
        with patch('os.makedirs', return_value=None), \
             patch('os.remove', return_value=None), \
             patch('dewey.core.crm.conftest.TestConfiguration.logger') as mock_logger:
            with setup_test_db():
                assert os.path.exists(test_dir)
            mock_logger.info.assert_not_called()

    def test_mock_duckdb_fixture(self):
        """Test the mock_duckdb fixture."""
        with patch('duckdb.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            with mock_duckdb() as conn:
                assert conn == mock_conn
