import logging
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.research.port.tic_delta_workflow import TicDeltaWorkflow


class TestTicDeltaWorkflow:
    """Unit tests for the TicDeltaWorkflow class."""

    @pytest.fixture
    def mock_base_script(self):
        """Mocks the BaseScript class."""
        with patch(
            "dewey.core.research.port.tic_delta_workflow.BaseScript", autospec=True
        ) as MockBaseScript:
            yield MockBaseScript

    @pytest.fixture
    def tic_delta_workflow(self, mock_base_script):
        """Fixture for creating a TicDeltaWorkflow instance with mocked dependencies."""
        workflow = TicDeltaWorkflow()
        workflow.logger = MagicMock(spec=logging.Logger)
        workflow.config = {
            "tic_delta_workflow": {
                "input_table": "test_input_table",
                "output_table": "test_output_table",
            },
            "database": {},
        }
        return workflow

    def test_init(self):
        """Test the __init__ method of TicDeltaWorkflow."""
        workflow = TicDeltaWorkflow()
        assert workflow.config_section == "tic_delta_workflow"

    def test_run_success(self, tic_delta_workflow):
        """Test the run method with successful database operations."""
        mock_connection = MagicMock()
        mock_create_table = MagicMock()
        mock_execute_query = MagicMock()

        with (
            patch(
                "dewey.core.research.port.tic_delta_workflow.get_connection",
                return_value=mock_connection,
            ),
            patch(
                "dewey.core.research.port.tic_delta_workflow.create_table",
                mock_create_table,
            ),
            patch(
                "dewey.core.research.port.tic_delta_workflow.execute_query",
                mock_execute_query,
            ),
        ):
            tic_delta_workflow.run()

            tic_delta_workflow.logger.info.assert_called()
            mock_create_table.assert_called_once()
            mock_execute_query.assert_called_once()

    def test_run_exception(self, tic_delta_workflow):
        """Test the run method when an exception occurs during database operations."""
        mock_connection = MagicMock()

        with (
            patch(
                "dewey.core.research.port.tic_delta_workflow.get_connection",
                return_value=mock_connection,
            ),
            pytest.raises(Exception) as exc_info,
        ):
            mock_connection.__enter__.side_effect = Exception("Test exception")
            with pytest.raises(Exception):
                tic_delta_workflow.run()

            tic_delta_workflow.logger.error.assert_called()
            assert "Test exception" in str(exc_info.value)

    def test_get_config_value(self, tic_delta_workflow):
        """Test the get_config_value method."""
        input_table = tic_delta_workflow.get_config_value("input_table")
        assert input_table == "test_input_table"

        output_table = tic_delta_workflow.get_config_value(
            "output_table", "default_output_table"
        )
        assert output_table == "test_output_table"

        non_existent_value = tic_delta_workflow.get_config_value(
            "non_existent", "default_value"
        )
        assert non_existent_value == "default_value"

    def test_run_with_empty_config(self):
        """Test the run method with an empty configuration."""
        workflow = TicDeltaWorkflow()
        workflow.logger = MagicMock(spec=logging.Logger)
        workflow.config = {}

        with pytest.raises(AttributeError):
            workflow.run()

    def test_run_with_missing_db_utils(self, tic_delta_workflow):
        """Test the run method when database utilities are missing."""
        with patch.dict(
            "sys.modules",
            {"dewey.core.db.connection": None, "dewey.core.db.utils": None},
        ):
            with pytest.raises(NameError) as exc_info:
                tic_delta_workflow.run()
            assert "name 'get_connection' is not defined" in str(exc_info.value)

    def test_execute(self, tic_delta_workflow):
        """Test the execute method."""
        tic_delta_workflow.parse_args = MagicMock()
        tic_delta_workflow.run = MagicMock()
        tic_delta_workflow._cleanup = MagicMock()

        tic_delta_workflow.execute()

        tic_delta_workflow.parse_args.assert_called_once()
        tic_delta_workflow.run.assert_called_once()
        tic_delta_workflow._cleanup.assert_called_once()

    def test_execute_keyboard_interrupt(self, tic_delta_workflow):
        """Test the execute method when a KeyboardInterrupt occurs."""
        tic_delta_workflow.parse_args = MagicMock()
        tic_delta_workflow.run = MagicMock(side_effect=KeyboardInterrupt)
        tic_delta_workflow._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            tic_delta_workflow.execute()

        assert exc_info.value.code == 1
        tic_delta_workflow.logger.warning.assert_called_with(
            "Script interrupted by user"
        )
        tic_delta_workflow._cleanup.assert_called_once()

    def test_execute_exception(self, tic_delta_workflow):
        """Test the execute method when an exception occurs."""
        tic_delta_workflow.parse_args = MagicMock()
        tic_delta_workflow.run = MagicMock(side_effect=Exception("Test exception"))
        tic_delta_workflow._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            tic_delta_workflow.execute()

        assert exc_info.value.code == 1
        tic_delta_workflow.logger.error.assert_called()
        tic_delta_workflow._cleanup.assert_called_once()

    def test_cleanup(self, tic_delta_workflow):
        """Test the _cleanup method."""
        tic_delta_workflow.db_conn = MagicMock()
        tic_delta_workflow._cleanup()
        tic_delta_workflow.db_conn.close.assert_called_once()

    def test_cleanup_no_db_conn(self, tic_delta_workflow):
        """Test the _cleanup method when db_conn is None."""
        tic_delta_workflow.db_conn = None
        tic_delta_workflow._cleanup()

    def test_cleanup_db_conn_exception(self, tic_delta_workflow):
        """Test the _cleanup method when closing the database connection raises an exception."""
        tic_delta_workflow.db_conn = MagicMock()
        tic_delta_workflow.db_conn.close.side_effect = Exception("Test exception")
        tic_delta_workflow._cleanup()
        tic_delta_workflow.logger.warning.assert_called()

    def test_get_path(self, tic_delta_workflow):
        """Test the get_path method."""
        relative_path = "data/test.txt"
        absolute_path = "/tmp/test.txt"

        resolved_relative_path = tic_delta_workflow.get_path(relative_path)
        assert str(resolved_relative_path) == str(
            tic_delta_workflow.PROJECT_ROOT / relative_path
        )

        resolved_absolute_path = tic_delta_workflow.get_path(absolute_path)
        assert str(resolved_absolute_path) == absolute_path

    def test_setup_logging_from_config(self, tic_delta_workflow, mock_base_script):
        """Test that logging is configured from the config file."""
        mock_config_path = MagicMock()
        with patch("dewey.core.base_script.CONFIG_PATH", mock_config_path):
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value = yaml.dump(
                    {
                        "core": {
                            "logging": {
                                "level": "DEBUG",
                                "format": "%(levelname)s - %(message)s",
                                "date_format": "%Y-%m-%d",
                            }
                        }
                    }
                )
                tic_delta_workflow._setup_logging()
                assert (
                    logging.getLoggerClass().root.handlers[0].formatter._fmt
                    == "%(levelname)s - %(message)s"
                )
                assert logging.getLoggerClass().root.level == logging.DEBUG

    def test_setup_logging_default(self, tic_delta_workflow, mock_base_script):
        """Test that logging is configured with default values if config loading fails."""
        mock_config_path = MagicMock()
        with patch("dewey.core.base_script.CONFIG_PATH", mock_config_path):
            with patch("builtins.open", create=True) as mock_open:
                mock_open.side_effect = FileNotFoundError
                tic_delta_workflow._setup_logging()
                assert (
                    logging.getLoggerClass().root.handlers[0].formatter._fmt
                    == "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
                )
                assert logging.getLoggerClass().root.level == logging.INFO

    def test_parse_args_log_level(self, tic_delta_workflow):
        """Test that the log level can be set via command line arguments."""
        with patch(
            "argparse.ArgumentParser.parse_args",
            return_value=MagicMock(log_level="DEBUG"),
        ):
            tic_delta_workflow.parse_args()
            assert tic_delta_workflow.logger.level == logging.DEBUG

    def test_parse_args_config_file(self, tic_delta_workflow):
        """Test that a config file can be loaded via command line arguments."""
        mock_config_path = MagicMock()
        with patch(
            "argparse.ArgumentParser.parse_args",
            return_value=MagicMock(config=mock_config_path),
        ):
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value = yaml.dump(
                    {"test": "value"}
                )
                tic_delta_workflow.parse_args()
                assert tic_delta_workflow.config == {"test": "value"}

    def test_parse_args_config_file_not_found(self, tic_delta_workflow):
        """Test that an error is raised if the config file specified via command line arguments is not found."""
        mock_config_path = MagicMock()
        with patch(
            "argparse.ArgumentParser.parse_args",
            return_value=MagicMock(config=mock_config_path),
        ):
            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    tic_delta_workflow.parse_args()
                assert exc_info.value.code == 1

    def test_parse_args_db_connection_string(self, tic_delta_workflow):
        """Test that a database connection string can be set via command line arguments."""
        tic_delta_workflow.requires_db = True
        with patch(
            "argparse.ArgumentParser.parse_args",
            return_value=MagicMock(db_connection_string="test_connection_string"),
        ):
            with patch(
                "dewey.core.db.connection.get_connection", return_value=MagicMock()
            ) as mock_get_connection:
                tic_delta_workflow.parse_args()
                mock_get_connection.assert_called_with(
                    {"connection_string": "test_connection_string"}
                )

    def test_parse_args_llm_model(self, tic_delta_workflow):
        """Test that an LLM model can be set via command line arguments."""
        tic_delta_workflow.enable_llm = True
        with patch(
            "argparse.ArgumentParser.parse_args",
            return_value=MagicMock(llm_model="test_llm_model"),
        ):
            with patch(
                "dewey.llm.llm_utils.get_llm_client", return_value=MagicMock()
            ) as mock_get_llm_client:
                tic_delta_workflow.parse_args()
                mock_get_llm_client.assert_called_with({"model": "test_llm_model"})
