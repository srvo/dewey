import logging
from unittest.mock import patch

import pytest

from dewey.core.research.analysis.financial_pipeline import FinancialPipeline


class TestFinancialPipeline:
    """Unit tests for the FinancialPipeline class."""

    @pytest.fixture
    def financial_pipeline(self) -> FinancialPipeline:
        """Fixture to create a FinancialPipeline instance."""
        return FinancialPipeline()

    def test_init(self, financial_pipeline: FinancialPipeline) -> None:
        """Test the __init__ method."""
        assert financial_pipeline.name == "FinancialPipeline"
        assert financial_pipeline.description == "Manages financial analysis"
        assert financial_pipeline.logger.name == "FinancialPipeline"

    @patch.object(FinancialPipeline, "get_config_value")
    def test_run_api_key_found(
        self, mock_get_config_value: pytest.fixture, financial_pipeline: FinancialPipeline, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method when the API key is found in the configuration."""
        mock_get_config_value.return_value = "test_api_key"
        with caplog.at_level(logging.INFO):
            financial_pipeline.run()
        assert "Starting financial analysis pipeline..." in caplog.text
        assert "API key loaded successfully." in caplog.text
        assert "Financial analysis completed." in caplog.text
        mock_get_config_value.assert_called_once_with("financial_api_key")

    @patch.object(FinancialPipeline, "get_config_value")
    def test_run_api_key_not_found(
        self, mock_get_config_value: pytest.fixture, financial_pipeline: FinancialPipeline, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method when the API key is not found in the configuration."""
        mock_get_config_value.return_value = None
        with caplog.at_level(logging.WARNING):
            financial_pipeline.run()
        assert "Starting financial analysis pipeline..." in caplog.text
        assert "API key not found in configuration." in caplog.text
        assert "Financial analysis completed." in caplog.text
        mock_get_config_value.assert_called_once_with("financial_api_key")

    @patch.object(FinancialPipeline, "get_config_value")
    def test_run_exception(
        self, mock_get_config_value: pytest.fixture, financial_pipeline: FinancialPipeline, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method when an exception occurs."""
        mock_get_config_value.side_effect = Exception("Test exception")
        with caplog.at_level(logging.ERROR):
            financial_pipeline.run()
        assert "Starting financial analysis pipeline..." in caplog.text
        assert "Test exception" not in caplog.text  # Exception should be caught in BaseScript.execute
        # The exception is caught by the execute method, so it won't be logged directly in the run method.

    def test_get_config_value_existing_key(self, financial_pipeline: FinancialPipeline) -> None:
        """Test get_config_value method with an existing key."""
        financial_pipeline.config = {"section": {"key": "value"}}
        value = financial_pipeline.get_config_value("section.key")
        assert value == "value"

    def test_get_config_value_missing_key(self, financial_pipeline: FinancialPipeline) -> None:
        """Test get_config_value method with a missing key."""
        financial_pipeline.config = {"section": {"key": "value"}}
        value = financial_pipeline.get_config_value("section.missing_key", "default")
        assert value == "default"

    def test_get_config_value_nested_missing_key(self, financial_pipeline: FinancialPipeline) -> None:
        """Test get_config_value method with a nested missing key."""
        financial_pipeline.config = {"section": {"key": "value"}}
        value = financial_pipeline.get_config_value("missing_section.key", "default")
        assert value == "default"

    def test_get_path_absolute_path(self, financial_pipeline: FinancialPipeline) -> None:
        """Test get_path method with an absolute path."""
        absolute_path = "/absolute/path"
        path = financial_pipeline.get_path(absolute_path)
        assert str(path) == absolute_path

    def test_get_path_relative_path(self, financial_pipeline: FinancialPipeline) -> None:
        """Test get_path method with a relative path."""
        relative_path = "relative/path"
        path = financial_pipeline.get_path(relative_path)
        expected_path = financial_pipeline.PROJECT_ROOT / relative_path
        assert path == expected_path

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_log_level(self, mock_parse_args: pytest.fixture, financial_pipeline: FinancialPipeline) -> None:
        """Test parse_args method with log level argument."""
        mock_parse_args.return_value = pytest.Namespace(log_level="DEBUG", config=None, db_connection_string=None, llm_model=None)
        args = financial_pipeline.parse_args()
        assert args.log_level == "DEBUG"
        assert financial_pipeline.logger.level == logging.DEBUG

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config_file(self, mock_parse_args: pytest.fixture, financial_pipeline: FinancialPipeline, tmp_path: Path) -> None:
        """Test parse_args method with config file argument."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test_key: test_value")
        mock_parse_args.return_value = pytest.Namespace(log_level=None, config=str(config_file), db_connection_string=None, llm_model=None)
        args = financial_pipeline.parse_args()
        assert args.config == str(config_file)
        assert financial_pipeline.config == {"test_key": "test_value"}

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_db_connection_string(self, mock_parse_args: pytest.fixture, financial_pipeline: FinancialPipeline) -> None:
        """Test parse_args method with db connection string argument."""
        financial_pipeline.requires_db = True
        mock_parse_args.return_value = pytest.Namespace(log_level=None, config=None, db_connection_string="test_db_string", llm_model=None)
        with patch("dewey.core.research.analysis.financial_pipeline.get_connection") as mock_get_connection:
            financial_pipeline.parse_args()
            mock_get_connection.assert_called_once_with({"connection_string": "test_db_string"})

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_llm_model(self, mock_parse_args: pytest.fixture, financial_pipeline: FinancialPipeline) -> None:
        """Test parse_args method with llm model argument."""
        financial_pipeline.enable_llm = True
        mock_parse_args.return_value = pytest.Namespace(log_level=None, config=None, db_connection_string=None, llm_model="test_llm_model")
        with patch("dewey.core.research.analysis.financial_pipeline.get_llm_client") as mock_get_llm_client:
            financial_pipeline.parse_args()
            mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})

    @patch.object(FinancialPipeline, "_cleanup")
    @patch.object(FinancialPipeline, "run")
    @patch.object(FinancialPipeline, "parse_args")
    def test_execute_success(
        self,
        mock_parse_args: pytest.fixture,
        mock_run: pytest.fixture,
        mock_cleanup: pytest.fixture,
        financial_pipeline: FinancialPipeline,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test execute method with successful run."""
        mock_parse_args.return_value = pytest.Namespace()
        with caplog.at_level(logging.INFO):
            financial_pipeline.execute()
        assert "Starting execution of FinancialPipeline" in caplog.text
        assert "Completed execution of FinancialPipeline" in caplog.text
        mock_run.assert_called_once()
        mock_cleanup.assert_called_once()

    @patch.object(FinancialPipeline, "_cleanup")
    @patch.object(FinancialPipeline, "run")
    @patch.object(FinancialPipeline, "parse_args")
    def test_execute_keyboard_interrupt(
        self,
        mock_parse_args: pytest.fixture,
        mock_run: pytest.fixture,
        mock_cleanup: pytest.fixture,
        financial_pipeline: FinancialPipeline,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test execute method with KeyboardInterrupt."""
        mock_parse_args.return_value = pytest.Namespace()
        mock_run.side_effect = KeyboardInterrupt
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.WARNING):
                financial_pipeline.execute()
        assert exc_info.value.code == 1
        assert "Script interrupted by user" in caplog.text
        mock_cleanup.assert_called_once()

    @patch.object(FinancialPipeline, "_cleanup")
    @patch.object(FinancialPipeline, "run")
    @patch.object(FinancialPipeline, "parse_args")
    def test_execute_exception(
        self,
        mock_parse_args: pytest.fixture,
        mock_run: pytest.fixture,
        mock_cleanup: pytest.fixture,
        financial_pipeline: FinancialPipeline,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test execute method with exception."""
        mock_parse_args.return_value = pytest.Namespace()
        mock_run.side_effect = Exception("Test exception")
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.ERROR):
                financial_pipeline.execute()
        assert exc_info.value.code == 1
        assert "Error executing script: Test exception" in caplog.text
        mock_cleanup.assert_called_once()

    @patch("dewey.core.research.analysis.financial_pipeline.get_connection")
    def test_cleanup_db_connection(self, mock_get_connection: pytest.fixture, financial_pipeline: FinancialPipeline) -> None:
        """Test _cleanup method closes db connection."""
        financial_pipeline.requires_db = True
        financial_pipeline._initialize_db_connection()
        financial_pipeline._cleanup()
        # Assert that close was called on the connection object
        financial_pipeline.db_conn.close.assert_called_once()

    def test_cleanup_no_db_connection(self, financial_pipeline: FinancialPipeline) -> None:
        """Test _cleanup method with no db connection."""
        financial_pipeline.db_conn = None
        financial_pipeline._cleanup()
        # Assert that no exception is raised

