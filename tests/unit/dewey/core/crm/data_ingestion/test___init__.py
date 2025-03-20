import logging
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.crm.data_ingestion import DataIngestionModule


class TestDataIngestionModule:
    """Unit tests for the DataIngestionModule."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript."""
        mock=None, mock_base_script: MagicMock) -> DataIngestionModule:
        """Fixture to create a DataIngestionModule instance."""
        with patch("dewey.core.crm.data_ingestion.BaseScript.__init__", return_value=None):
            if self) -> MagicMock:
        """Fixture to mock BaseScript."""
        mock is None:
                self) -> MagicMock:
        """Fixture to mock BaseScript."""
        mock = MagicMock(spec=BaseScript)
        mock.logger = MagicMock(spec=logging.Logger)
        mock.config = {}
        mock.db_conn = None
        mock.llm_client = None
        return mock

    @pytest.fixture
    def data_ingestion_module(self
            module = DataIngestionModule(name="TestModule", description="Test Description")
            module.logger = mock_base_script.logger
            module.config = mock_base_script.config
            module.db_conn = mock_base_script.db_conn
            module.llm_client = mock_base_script.llm_client
        return module

    def test_init(self) -> None:
        """Test the __init__ method of DataIngestionModule."""
        with patch("dewey.core.crm.data_ingestion.BaseScript.__init__", return_value=None) as mock_init:
            module = DataIngestionModule(name="TestModule", description="Test Description")
            mock_init.assert_called_once_with(
                "TestModule", "Test Description", config_section="data_ingestion"
            )
            assert module.name == "TestModule"
            assert module.description == "Test Description"

    def test_run_no_db_no_llm(self, data_ingestion_module: DataIngestionModule) -> None:
        """Test the run method with no database or LLM."""
        data_ingestion_module.get_config_value = MagicMock(return_value="test_source")
        data_ingestion_module.run()

        data_ingestion_module.logger.info.assert_called()
        assert "Starting data ingestion process..." in str(
            data_ingestion_module.logger.info.call_args_list[0]
        )
        assert "Using data source: test_source" in str(
            data_ingestion_module.logger.info.call_args_list[1]
        )
        assert "Data ingestion process completed." in str(
            data_ingestion_module.logger.info.call_args_list[2]
        )
        data_ingestion_module.logger.error.assert_not_called()

    def test_run_with_db_success(self, data_ingestion_module: DataIngestionModule) -> None:
        """Test the run method with a successful database connection."""
        data_ingestion_module.get_config_value = MagicMock(return_value="test_source")
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ["test_result"]
        mock_db_conn = MagicMock()
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
        data_ingestion_module.db_conn = mock_db_conn

        data_ingestion_module.run()

        data_ingestion_module.logger.info.assert_called()
        assert "Database connection test: ['test_result']" in str(
            data_ingestion_module.logger.info.call_args_list[2]
        )
        mock_cursor.execute.assert_called_with("SELECT 1")
        data_ingestion_module.logger.error.assert_not_called()

    def test_run_with_db_failure(self, data_ingestion_module: DataIngestionModule) -> None:
        """Test the run method with a database connection failure."""
        data_ingestion_module.get_config_value = MagicMock(return_value="test_source")
        mock_db_conn = MagicMock()
        mock_db_conn.cursor.side_effect = Exception("Database error")
        data_ingestion_module.db_conn = mock_db_conn

        data_ingestion_module.run()

        data_ingestion_module.logger.error.assert_called()
        assert "Database error: Database error" in str(data_ingestion_module.logger.error.call_args)

    def test_run_with_llm_success(self, data_ingestion_module: DataIngestionModule) -> None:
        """Test the run method with a successful LLM call."""
        data_ingestion_module.get_config_value = MagicMock(return_value="test_source")
        mock_llm_client = MagicMock()
        mock_llm_client.generate_text.return_value = "LLM response"
        data_ingestion_module.llm_client = mock_llm_client

        data_ingestion_module.run()

        data_ingestion_module.logger.info.assert_called()
        assert "LLM response: LLM response" in str(data_ingestion_module.logger.info.call_args_list[2])
        mock_llm_client.generate_text.assert_called_with("Tell me a joke.")
        data_ingestion_module.logger.error.assert_not_called()

    def test_run_with_llm_failure(self, data_ingestion_module: DataIngestionModule) -> None:
        """Test the run method with an LLM call failure."""
        data_ingestion_module.get_config_value = MagicMock(return_value="test_source")
        mock_llm_client = MagicMock()
        mock_llm_client.generate_text.side_effect = Exception("LLM error")
        data_ingestion_module.llm_client = mock_llm_client

        data_ingestion_module.run()

        data_ingestion_module.logger.error.assert_called()
        assert "LLM error: LLM error" in str(data_ingestion_module.logger.error.call_args)

    def test_get_config_value_exists(self, data_ingestion_module: DataIngestionModule) -> None:
        """Test get_config_value when the key exists in the config."""
        data_ingestion_module.config = {"key": "value"}
        value = data_ingestion_module.get_config_value("key")
        assert value == "value"

    def test_get_config_value_does_not_exist(self, data_ingestion_module: DataIngestionModule) -> None:
        """Test get_config_value when the key does not exist in the config."""
        data_ingestion_module.config = {}
        value = data_ingestion_module.get_config_value("key", "default")
        assert value == "default"

    def test_get_config_value_nested_exists(self, data_ingestion_module: DataIngestionModule) -> None:
        """Test get_config_value when the nested key exists in the config."""
        data_ingestion_module.config = {"nested": {"key": "value"}}
        value = data_ingestion_module.get_config_value("nested.key")
        assert value == "value"

    def test_get_config_value_nested_does_not_exist(
        self, data_ingestion_module: DataIngestionModule
    ) -> None:
        """Test get_config_value when the nested key does not exist in the config."""
        data_ingestion_module.config = {"nested": {}}
        value = data_ingestion_module.get_config_value("nested.key", "default")
        assert value == "default"

    def test_get_config_value_intermediate_does_not_exist(
        self, data_ingestion_module: DataIngestionModule
    ) -> None:
        """Test get_config_value when an intermediate key does not exist in the config."""
        data_ingestion_module.config = {}
        value = data_ingestion_module.get_config_value("nested.key", "default")
        assert value == "default"
