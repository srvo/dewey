import logging
from unittest.mock import patch

import pytest
from dewey.core.crm.gmail.setup_auth import SetupAuth


class TestSetupAuth:
    """Unit tests for the SetupAuth class."""

    @pytest.fixture
    def setup_auth(self):
        """Fixture to create an instance of SetupAuth."""
        return SetupAuth()

    def test_init(self, setup_auth: SetupAuth):
        """Test the initialization of the SetupAuth class."""
        assert setup_auth.name == "SetupAuth"
        assert setup_auth.config_section == "gmail_auth"
        assert setup_auth.requires_db is False
        assert setup_auth.enable_llm is False
        assert setup_auth.logger is not None

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.get_config_value")
    def test_run(self, mock_get_config_value, setup_auth: SetupAuth, caplog):
        """Test the run method of the SetupAuth class."""
        mock_get_config_value.return_value = "test_client_id"
        with caplog.at_level(logging.DEBUG):
            setup_auth.run()
        assert "Starting Gmail authentication setup..." in caplog.text
        assert "Client ID: test_client_id" in caplog.text
        assert "Gmail authentication setup completed (placeholder)." in caplog.text
        mock_get_config_value.assert_called_once_with("client_id")

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.get_config_value")
    def test_run_config_value_error(
        self, mock_get_config_value, setup_auth: SetupAuth, caplog
    ):
        """Test the run method when get_config_value raises an exception."""
        mock_get_config_value.side_effect = ValueError("Config value not found")
        with caplog.at_level(logging.ERROR):
            setup_auth.run()
        assert "Starting Gmail authentication setup..." in caplog.text
        assert "Gmail authentication setup completed (placeholder)." in caplog.text
        mock_get_config_value.assert_called_once_with("client_id")

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.get_config_value")
    def test_run_no_client_id(
        self, mock_get_config_value, setup_auth: SetupAuth, caplog
    ):
        """Test the run method when client_id is not found in config."""
        mock_get_config_value.return_value = None
        with caplog.at_level(logging.DEBUG):
            setup_auth.run()
        assert "Starting Gmail authentication setup..." in caplog.text
        assert "Client ID: None" in caplog.text
        assert "Gmail authentication setup completed (placeholder)." in caplog.text
        mock_get_config_value.assert_called_once_with("client_id")

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.parse_args")
    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.run")
    def test_execute(self, mock_run, mock_parse_args, setup_auth: SetupAuth, caplog):
        """Test the execute method of the SetupAuth class."""
        mock_parse_args.return_value = None  # Simulate no command-line arguments
        with caplog.at_level(logging.INFO):
            setup_auth.execute()
        assert "Starting execution of SetupAuth" in caplog.text
        assert "Completed execution of SetupAuth" in caplog.text
        mock_run.assert_called_once()

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.parse_args")
    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.run")
    def test_execute_keyboard_interrupt(
        self, mock_run, mock_parse_args, setup_auth: SetupAuth, caplog
    ):
        """Test the execute method when a KeyboardInterrupt is raised."""
        mock_parse_args.return_value = None
        mock_run.side_effect = KeyboardInterrupt
        with caplog.at_level(logging.WARNING):
            with pytest.raises(SystemExit) as exc_info:
                setup_auth.execute()
            assert exc_info.value.code == 1
        assert "Script interrupted by user" in caplog.text

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.parse_args")
    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.run")
    def test_execute_exception(
        self, mock_run, mock_parse_args, setup_auth: SetupAuth, caplog
    ):
        """Test the execute method when an exception is raised."""
        mock_parse_args.return_value = None
        mock_run.side_effect = ValueError("Test exception")
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                setup_auth.execute()
            assert exc_info.value.code == 1
        assert "Error executing script: Test exception" in caplog.text

    def test_cleanup(self, setup_auth: SetupAuth, caplog):
        """Test the _cleanup method of the SetupAuth class."""
        setup_auth.db_conn = pytest.mock.MagicMock()
        with caplog.at_level(logging.DEBUG):
            setup_auth._cleanup()
        assert "Closing database connection" in caplog.text
        setup_auth.db_conn.close.assert_called_once()

    def test_cleanup_no_db_conn(self, setup_auth: SetupAuth, caplog):
        """Test the _cleanup method when db_conn is None."""
        setup_auth.db_conn = None
        with caplog.at_level(logging.DEBUG):
            setup_auth._cleanup()
        assert "Closing database connection" not in caplog.text

    def test_cleanup_db_conn_exception(self, setup_auth: SetupAuth, caplog):
        """Test the _cleanup method when db_conn.close() raises an exception."""
        setup_auth.db_conn = pytest.mock.MagicMock()
        setup_auth.db_conn.close.side_effect = ValueError("Close error")
        with caplog.at_level(logging.WARNING):
            setup_auth._cleanup()
        assert "Error closing database connection: Close error" in caplog.text
        setup_auth.db_conn.close.assert_called_once()

    def test_get_path_absolute(self, setup_auth: SetupAuth):
        """Test the get_path method with an absolute path."""
        absolute_path = "/absolute/path"
        result = setup_auth.get_path(absolute_path)
        assert str(result) == absolute_path

    def test_get_path_relative(self, setup_auth: SetupAuth):
        """Test the get_path method with a relative path."""
        relative_path = "relative/path"
        expected_path = setup_auth.PROJECT_ROOT / relative_path
        result = setup_auth.get_path(relative_path)
        assert result == expected_path

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.config", new_callable=dict)
    def test_get_config_value(self, mock_config, setup_auth: SetupAuth):
        """Test the get_config_value method."""
        mock_config["llm"] = {"model": "test_model"}
        result = setup_auth.get_config_value("llm.model")
        assert result == "test_model"

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.config", new_callable=dict)
    def test_get_config_value_default(self, mock_config, setup_auth: SetupAuth):
        """Test the get_config_value method with a default value."""
        result = setup_auth.get_config_value("llm.unknown", "default_model")
        assert result == "default_model"

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.config", new_callable=dict)
    def test_get_config_value_nested(self, mock_config, setup_auth: SetupAuth):
        """Test the get_config_value method with a nested key."""
        mock_config["nested"] = {"level1": {"level2": "nested_value"}}
        result = setup_auth.get_config_value("nested.level1.level2")
        assert result == "nested_value"

    @patch("dewey.core.crm.gmail.setup_auth.SetupAuth.config", new_callable=dict)
    def test_get_config_value_missing_intermediate(
        self, mock_config, setup_auth: SetupAuth
    ):
        """Test the get_config_value method when an intermediate key is missing."""
        mock_config["nested"] = {}
        result = setup_auth.get_config_value("nested.level1.level2", "default_value")
        assert result == "default_value"

    def test_setup_argparse(self, setup_auth: SetupAuth):
        """Test the setup_argparse method."""
        parser = setup_auth.setup_argparse()
        assert parser.description == setup_auth.description
        assert parser.format_help()  # Ensure help message can be generated

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_log_level(self, mock_parse_args, setup_auth: SetupAuth, caplog):
        """Test the parse_args method with a log level argument."""
        mock_parse_args.return_value = pytest.mock.MagicMock(
            log_level="DEBUG", config=None, db_connection_string=None, llm_model=None
        )
        args = setup_auth.parse_args()
        assert args.log_level == "DEBUG"
        assert setup_auth.logger.level == logging.DEBUG
        assert "Log level set to DEBUG" in caplog.text

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config(self, mock_parse_args, setup_auth: SetupAuth, caplog):
        """Test the parse_args method with a config argument."""
        mock_parse_args.return_value = pytest.mock.MagicMock(
            log_level=None,
            config="config/dewey.yaml",
            db_connection_string=None,
            llm_model=None,
        )
        with patch("dewey.core.crm.gmail.setup_auth.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                "test: value"
            )
            args = setup_auth.parse_args()
        assert args.config == "config/dewey.yaml"
        assert setup_auth.config == {"test": "value"}
        assert "Loaded configuration from config/dewey.yaml" in caplog.text

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config_not_found(
        self, mock_parse_args, setup_auth: SetupAuth, caplog
    ):
        """Test the parse_args method when the config file is not found."""
        mock_parse_args.return_value = pytest.mock.MagicMock(
            log_level=None,
            config="nonexistent_config.yaml",
            db_connection_string=None,
            llm_model=None,
        )
        with pytest.raises(SystemExit) as exc_info:
            setup_auth.parse_args()
        assert exc_info.value.code == 1
        assert "Configuration file not found: nonexistent_config.yaml" in caplog.text

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_db_connection_string(
        self, mock_parse_args, setup_auth: SetupAuth, caplog
    ):
        """Test the parse_args method with a db_connection_string argument."""
        mock_parse_args.return_value = pytest.mock.MagicMock(
            log_level=None,
            config=None,
            db_connection_string="test_db_string",
            llm_model=None,
        )
        setup_auth.requires_db = True
        with patch(
            "dewey.core.crm.gmail.setup_auth.get_connection"
        ) as mock_get_connection:
            mock_get_connection.return_value = "test_db_connection"
            args = setup_auth.parse_args()
        assert args.db_connection_string == "test_db_string"
        assert setup_auth.db_conn == "test_db_connection"
        assert "Using custom database connection" in caplog.text

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_llm_model(self, mock_parse_args, setup_auth: SetupAuth, caplog):
        """Test the parse_args method with an llm_model argument."""
        mock_parse_args.return_value = pytest.mock.MagicMock(
            log_level=None,
            config=None,
            db_connection_string=None,
            llm_model="test_llm_model",
        )
        setup_auth.enable_llm = True
        with patch(
            "dewey.core.crm.gmail.setup_auth.get_llm_client"
        ) as mock_get_llm_client:
            mock_get_llm_client.return_value = "test_llm_client"
            args = setup_auth.parse_args()
        assert args.llm_model == "test_llm_model"
        assert setup_auth.llm_client == "test_llm_client"
        assert "Using custom LLM model: test_llm_model" in caplog.text
