"""Tests for dewey.core.automation."""

import logging
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.automation import AutomationModule
from dewey.core.base_script import BaseScript


class TestAutomationModule:
    """Unit tests for the AutomationModule class."""

    @pytest.fixture
    def automation_module(self) -> AutomationModule:
        """Fixture to create an instance of AutomationModule."""
        with patch("dewey.core.automation.BaseScript.__init__", return_value=None):
            module = AutomationModule()
            module.config = {"example_config_key": "test_config_value"}
            module.logger = MagicMock()
            module.db_conn = MagicMock()
            module.llm_client = MagicMock()
            return module

    def test_inheritance(self, automation_module: AutomationModule) -> None:
        """Test that AutomationModule inherits from BaseScript."""
        assert isinstance(automation_module, BaseScript)

    def test_init_default_config_section(self) -> None:
        """Test that the default config section is 'automation'."""
        with patch("dewey.core.automation.BaseScript.__init__", return_value=None):
            module = AutomationModule()
            assert module.config_section == "automation"

    def test_init_custom_config_section(self) -> None:
        """Test initializing with a custom config section."""
        with patch("dewey.core.automation.BaseScript.__init__", return_value=None):
            module = AutomationModule(config_section="custom_section")
            assert module.config_section == "custom_section"

    @patch("dewey.core.automation.BaseScript.__init__")
    def test_init_calls_super_init(self, mock_super_init: Any) -> None:
        """Test that the __init__ method calls the superclass's __init__."""
        AutomationModule(config_section="test_section")
        mock_super_init.assert_called_once_with(
            config_section="test_section", requires_db=True, enable_llm=True
        )

    def test_run_method_no_db_no_llm(self) -> None:
        """Test the run method execution without DB and LLM."""
        with patch("dewey.core.automation.BaseScript.__init__", return_value=None):
            module = AutomationModule()
            module.config = {"example_config_key": "test_config_value"}
            module.logger = MagicMock()
            module.db_conn = None
            module.llm_client = None

            module.run()

            module.logger.info.assert_any_call("Automation module started.")
            module.logger.info.assert_any_call("Automation module finished.")
            module.logger.info.assert_any_call(
                "Example config value: test_config_value"
            )
            module.logger.warning.assert_any_call("Database connection not available.")
            module.logger.warning.assert_any_call("LLM client not available.")

    def test_run_method_with_db_and_llm(self, automation_module: AutomationModule) -> (
        None
    ):
        """Test the run method execution with DB and LLM."""
        automation_module.db_conn.execute.return_value = "test_db_result"
        automation_module.llm_client.generate_text.return_value = "test_llm_response"

        automation_module.run()

        automation_module.logger.info.assert_any_call("Automation module started.")
        automation_module.logger.info.assert_any_call("Automation module finished.")
        automation_module.logger.info.assert_any_call(
            "Example config value: test_config_value"
        )
        automation_module.db_conn.execute.assert_called_once_with("SELECT 1")
        automation_module.logger.info.assert_any_call(
            "Database query result: test_db_result"
        )
        automation_module.llm_client.generate_text.assert_called_once_with(
            "Write a short poem about automation."
        )
        automation_module.logger.info.assert_any_call(
            "LLM response: test_llm_response"
        )

    @patch("dewey.core.automation.BaseScript.get_config_value")
    def test_get_config_value(
        self, mock_super_get_config_value: Any, automation_module: AutomationModule
    ) -> None:
        """Test the get_config_value method."""
        mock_super_get_config_value.return_value = "config_value"
        value = automation_module.get_config_value("test_key", "default_value")
        assert value == "config_value"
        mock_super_get_config_value.assert_called_once_with("test_key", "default_value")

    def test_get_config_value_no_default(
        self, automation_module: AutomationModule
    ) -> None:
        """Test get_config_value without a default value."""
        automation_module.config = {"test_key": "config_value"}
        value = automation_module.get_config_value("test_key")
        assert value == "config_value"

    def test_get_config_value_default_returned(
        self, automation_module: AutomationModule
    ) -> None:
        """Test get_config_value when the key is not found and a default is provided."""
        default_value = "default_value"
        value = automation_module.get_config_value("nonexistent_key", default_value)
        assert value == default_value

    def test_get_config_value_key_not_found(
        self, automation_module: AutomationModule
    ) -> None:
        """Test get_config_value when the key is not found and no default is provided."""
        automation_module.config = {}
        value = automation_module.get_config_value("nonexistent_key")
        assert value is None

    def test_run_no_exception(self, automation_module: AutomationModule) -> None:
        """Test that the run method does not raise an exception."""
        try:
            automation_module.run()
        except Exception as e:
            assert False, f"run() raised an exception {e}"

        automation_module.logger.info.assert_any_call("Automation module started.")
        automation_module.logger.info.assert_any_call("Automation module finished.")

    def test_run_config_value(self, automation_module: AutomationModule) -> None:
        """Test that the run method retrieves and logs a config value."""
        automation_module.run()

        automation_module.logger.info.assert_any_call(
            "Example config value: test_config_value"
        )

    def test_run_exception_raised(self, automation_module: AutomationModule) -> None:
        """Test that the run method raises an exception."""
        automation_module.get_config_value = MagicMock(
            side_effect=ValueError("Test Exception")
        )
        with pytest.raises(ValueError, match="Test Exception"):
            automation_module.run()
        automation_module.logger.error.assert_called_once()

    @patch("dewey.core.automation.AutomationModule.parse_args")
    @patch("dewey.core.automation.AutomationModule.run")
    def test_execute(
        self,
        mock_run: MagicMock,
        mock_parse_args: MagicMock,
    ) -> None:
        """Test the execute method."""
        with patch("dewey.core.automation.BaseScript.__init__", return_value=None):
            module = AutomationModule()
            module.logger = MagicMock()
            mock_parse_args.return_value = MagicMock()
            module.execute()
            mock_run.assert_called_once()
            module.logger.info.assert_any_call(f"Starting execution of {module.name}")
            module.logger.info.assert_any_call(f"Completed execution of {module.name}")

    @patch("dewey.core.automation.AutomationModule.parse_args")
    @patch("dewey.core.automation.AutomationModule.run")
    def test_execute_keyboard_interrupt(
        self,
        mock_run: MagicMock,
        mock_parse_args: MagicMock,
    ) -> None:
        """Test the execute method with KeyboardInterrupt."""
        with patch("dewey.core.automation.BaseScript.__init__", return_value=None):
            module = AutomationModule()
            module.logger = MagicMock()
            mock_parse_args.return_value = MagicMock()
            mock_run.side_effect = KeyboardInterrupt
            with pytest.raises(SystemExit) as exc_info:
                module.execute()
            assert exc_info.value.code == 1
            module.logger.warning.assert_called_once_with("Script interrupted by user")

    @patch("dewey.core.automation.AutomationModule.parse_args")
    @patch("dewey.core.automation.AutomationModule.run")
    def test_execute_exception(
        self,
        mock_run: MagicMock,
        mock_parse_args: MagicMock,
    ) -> None:
        """Test the execute method with an exception."""
        with patch("dewey.core.automation.BaseScript.__init__", return_value=None):
            module = AutomationModule()
            module.logger = MagicMock()
            mock_parse_args.return_value = MagicMock()
            mock_run.side_effect = ValueError("Test Exception")
            with pytest.raises(SystemExit) as exc_info:
                module.execute()
            assert exc_info.value.code == 1
            module.logger.error.assert_called_once()

    def test_cleanup(self, automation_module: AutomationModule) -> None:
        """Test the _cleanup method."""
        automation_module.db_conn = MagicMock()
        automation_module._cleanup()
        automation_module.db_conn.close.assert_called_once()

    def test_cleanup_no_db_conn(self, automation_module: AutomationModule) -> None:
        """Test the _cleanup method when db_conn is None."""
        automation_module.db_conn = None
        automation_module._cleanup()

    def test_cleanup_db_conn_exception(self, automation_module: AutomationModule) -> (
        None
    ):
        """Test the _cleanup method when db_conn.close() raises an exception."""
        automation_module.db_conn = MagicMock()
        automation_module.db_conn.close.side_effect = ValueError("Test Exception")
        automation_module._cleanup()
        automation_module.logger.warning.assert_called_once()

    @patch("os.path.isabs")
    def test_get_path_absolute(self, mock_isabs: MagicMock, automation_module: AutomationModule) -> None:
        """Test get_path with an absolute path."""
        mock_isabs.return_value = True
        path = automation_module.get_path("/absolute/path")
        assert str(path) == "/absolute/path"

    @patch("os.path.isabs")
    def test_get_path_relative(self, mock_isabs: MagicMock, automation_module: AutomationModule) -> None:
        """Test get_path with a relative path."""
        mock_isabs.return_value = False
        path = automation_module.get_path("relative/path")
        assert str(path) == str(
            automation_module.PROJECT_ROOT / "relative" / "path"
        )

    def test_get_config_value_empty_key(self, automation_module: AutomationModule) -> None:
        """Test get_config_value with an empty key."""
        default_value = "default_value"
        value = automation_module.get_config_value("", default_value)
        assert value == default_value

    def test_get_config_value_empty_part(self, automation_module: AutomationModule) -> None:
        """Test get_config_value with an empty part in the key."""
        default_value = "default_value"
        automation_module.config = {"level1": {"": "config_value"}}
        value = automation_module.get_config_value("level1.", default_value)
        assert value == default_value

    def test_setup_argparse(self, automation_module: AutomationModule) -> None:
        """Test the setup_argparse method."""
        parser = automation_module.setup_argparse()
        assert parser is not None

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args(self, mock_parse_args: MagicMock, automation_module: AutomationModule) -> None:
        """Test the parse_args method."""
        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_args.config = None
        mock_parse_args.return_value = mock_args
        automation_module.parse_args()
        automation_module.logger.setLevel.assert_called_with(logging.DEBUG)

    @patch("argparse.ArgumentParser.parse_args")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=MagicMock)
    def test_parse_args_with_config(
        self, mock_open: MagicMock, mock_exists: MagicMock, mock_parse_args: MagicMock, automation_module: AutomationModule
    ) -> None:
        """Test the parse_args method with a config file."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = "test_config.yaml"
        mock_parse_args.return_value = mock_args
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "test: value"
        automation_module.parse_args()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("pathlib.Path.exists")
    def test_parse_args_with_config_not_found(
        self, mock_exists: MagicMock, mock_parse_args: MagicMock, automation_module: AutomationModule
    ) -> None:
        """Test the parse_args method with a config file that is not found."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = "test_config.yaml"
        mock_parse_args.return_value = mock_args
        mock_exists.return_value = False
        with pytest.raises(SystemExit) as exc_info:
            automation_module.parse_args()
        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_with_db_connection_string(
        self, mock_parse_args: MagicMock
    ) -> None:
        """Test the parse_args method with a database connection string."""
        with patch("dewey.core.automation.BaseScript.__init__", return_value=None):
            module = AutomationModule(requires_db=True)
            module.logger = MagicMock()
            mock_args = MagicMock()
            mock_args.log_level = None
            mock_args.config = None
            mock_args.db_connection_string = "test_connection_string"
            mock_parse_args.return_value = mock_args
            with patch("dewey.core.automation.get_connection") as mock_get_connection:
                module.parse_args()
                mock_get_connection.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_with_llm_model(self, mock_parse_args: MagicMock) -> None:
        """Test the parse_args method with an LLM model."""
        with patch("dewey.core.automation.BaseScript.__init__", return_value=None):
            module = AutomationModule(enable_llm=True)
            module.logger = MagicMock()
            mock_args = MagicMock()
            mock_args.log_level = None
            mock_args.config = None
            mock_args.llm_model = "test_llm_model"
            mock_parse_args.return_value = mock_args
            with patch("dewey.core.automation.get_llm_client") as mock_get_llm_client:
                module.parse_args()
                mock_get_llm_client.assert_called_once()
