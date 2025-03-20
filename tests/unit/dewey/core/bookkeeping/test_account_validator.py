"""Tests for dewey.core.bookkeeping.account_validator."""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml

from dewey.core.bookkeeping.account_validator import AccountValidator
from dewey.core.base_script import BaseScript


class TestAccountValidator:
    """Tests for the AccountValidator class."""

    @pytest.fixture
    def account_validator(self) -> AccountValidator:
        """Fixture to create an AccountValidator instance."""
        with patch("dewey.core.bookkeeping.account_validator.BaseScript.__init__", return_value=None):
            validator = AccountValidator()
            validator.logger = MagicMock()
            validator.config = {}
            return validator

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Fixture to provide a mock configuration."""
        return {
            "bookkeeping": {
                "rules_file": "path/to/rules.json",
                "journal_file": "path/to/journal.ldg",
            },
            "core": {
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                    "date_format": "%Y-%m-%d %H:%M:%S",
                }
            },
        }

    @pytest.fixture
    def mock_rules(self) -> Dict[str, List[str]]:
        """Fixture to provide mock classification rules."""
        return {
            "categories": [
                "Assets:Bank",
                "Expenses:Food",
                "Income:Salary",
            ]
        }

    @pytest.fixture
    def mock_existing_accounts(self) -> List[str]:
        """Fixture to provide a list of mock existing accounts."""
        return [
            "Assets:Bank",
            "Expenses:Food",
            "Income:Salary",
            "Liabilities:CreditCard",
        ]

    def test_init(self, account_validator: AccountValidator) -> None:
        """Test the __init__ method."""
        assert account_validator.name == "AccountValidator"
        assert account_validator.config_section == "bookkeeping"

    @patch("json.load")
    @patch("builtins.open", new_callable=mock_open, read_data='{"categories": ["Assets:Bank"]}')
    def test_load_rules_success(
        self,
        mock_open_file: MagicMock,
        mock_json_load: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
        mock_rules: Dict[str, List[str]],
    ) -> None:
        """Test loading rules from a valid JSON file."""
        rules_file = tmp_path / "rules.json"
        mock_json_load.return_value = mock_rules

        loaded_rules = account_validator.load_rules(rules_file)
        assert loaded_rules == mock_rules
        mock_open_file.assert_called_once_with(rules_file)
        mock_json_load.assert_called_once()

    @patch("sys.exit")
    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_rules_file_not_found(
        self, mock_open_file: MagicMock, mock_exit: MagicMock, account_validator: AccountValidator, tmp_path: Path
    ) -> None:
        """Test loading rules when the file does not exist."""
        rules_file = tmp_path / "nonexistent_rules.json"
        account_validator.load_rules(rules_file)
        mock_exit.assert_called_once_with(1)
        account_validator.logger.exception.assert_called_once()

    @patch("sys.exit")
    @patch("json.load", side_effect=json.JSONDecodeError("", "", 0))
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    def test_load_rules_invalid_json(
        self, mock_open_file: MagicMock, mock_json_load: MagicMock, mock_exit: MagicMock, account_validator: AccountValidator, tmp_path: Path
    ) -> None:
        """Test loading rules from an invalid JSON file."""
        rules_file = tmp_path / "invalid_rules.json"

        account_validator.load_rules(rules_file)
        mock_exit.assert_called_once_with(1)
        account_validator.logger.exception.assert_called_once()

    @patch("subprocess.run")
    def test_validate_accounts_success(
        self,
        mock_run: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
        mock_rules: Dict[str, List[str]],
        mock_existing_accounts: List[str],
    ) -> None:
        """Test successful account validation."""
        journal_file = tmp_path / "journal.ldg"

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "\n".join(mock_existing_accounts)

        is_valid = account_validator.validate_accounts(journal_file, mock_rules)
        assert is_valid is True
        mock_run.assert_called_once_with(
            ["hledger", "accounts", "-f", journal_file, "--declared", "--used"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_validate_accounts_missing_accounts(
        self,
        mock_run: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
        mock_rules: Dict[str, List[str]],
    ) -> None:
        """Test account validation with missing accounts."""
        journal_file = tmp_path / "journal.ldg"
        existing_accounts = ["Assets:Bank", "Expenses:Food"]  # Missing "Income:Salary"

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "\n".join(existing_accounts)

        is_valid = account_validator.validate_accounts(journal_file, mock_rules)
        assert is_valid is False
        mock_run.assert_called_once()
        assert account_validator.logger.error.call_count >= 3

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "hledger"))
    def test_validate_accounts_hledger_command_fails(
        self,
        mock_run: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
        mock_rules: Dict[str, List[str]],
    ) -> None:
        """Test when the hledger command fails."""
        journal_file = tmp_path / "journal.ldg"

        is_valid = account_validator.validate_accounts(journal_file, mock_rules)
        assert is_valid is False
        mock_run.assert_called_once()
        account_validator.logger.exception.assert_called_once()

    @patch("subprocess.run", side_effect=Exception("Some error"))
    def test_validate_accounts_general_exception(
        self,
        mock_run: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
        mock_rules: Dict[str, List[str]],
    ) -> None:
        """Test when a general exception occurs during validation."""
        journal_file = tmp_path / "journal.ldg"

        is_valid = account_validator.validate_accounts(journal_file, mock_rules)
        assert is_valid is False
        mock_run.assert_called_once()
        account_validator.logger.exception.assert_called_once()

    @patch("sys.argv", ["account_validator.py", "journal.ldg", "rules.json"])
    @patch.object(AccountValidator, "load_rules")
    @patch.object(AccountValidator, "validate_accounts")
    @patch("sys.exit")
    @patch("pathlib.Path.exists", return_value=True)
    def test_run_success(
        self,
        mock_path_exists: MagicMock,
        mock_exit: MagicMock,
        mock_validate_accounts: MagicMock,
        mock_load_rules: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
        mock_rules: Dict[str, List[str]],
    ) -> None:
        """Test successful execution of the run method."""
        journal_file = tmp_path / "journal.ldg"
        rules_file = tmp_path / "rules.json"

        mock_load_rules.return_value = mock_rules
        mock_validate_accounts.return_value = True

        account_validator.run()

        mock_load_rules.assert_called_once_with(rules_file)
        mock_validate_accounts.assert_called_once_with(journal_file, mock_rules)
        mock_exit.assert_not_called()

    @patch("sys.argv", ["account_validator.py", "journal.ldg", "rules.json"])
    @patch.object(AccountValidator, "load_rules")
    @patch.object(AccountValidator, "validate_accounts")
    @patch("sys.exit")
    @patch("pathlib.Path.exists", return_value=True)
    def test_run_validation_fails(
        self,
        mock_path_exists: MagicMock,
        mock_exit: MagicMock,
        mock_validate_accounts: MagicMock,
        mock_load_rules: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
        mock_rules: Dict[str, List[str]],
    ) -> None:
        """Test run method when account validation fails."""
        journal_file = tmp_path / "journal.ldg"
        rules_file = tmp_path / "rules.json"

        mock_load_rules.return_value = mock_rules
        mock_validate_accounts.return_value = False

        account_validator.run()

        mock_load_rules.assert_called_once_with(rules_file)
        mock_validate_accounts.assert_called_once_with(journal_file, mock_rules)
        mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["account_validator.py", "journal.ldg", "rules.json"])
    @patch.object(AccountValidator, "load_rules")
    @patch.object(AccountValidator, "validate_accounts")
    @patch("sys.exit")
    @patch("pathlib.Path.exists", side_effect=[False, True])
    def test_run_missing_journal_file(
        self,
        mock_path_exists: MagicMock,
        mock_exit: MagicMock,
        mock_validate_accounts: MagicMock,
        mock_load_rules: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
        mock_rules: Dict[str, List[str]],
    ) -> None:
        """Test run method when journal file is missing."""
        rules_file = tmp_path / "rules.json"

        account_validator.run()

        mock_load_rules.assert_not_called()
        mock_validate_accounts.assert_not_called()
        mock_exit.assert_called_once_with(1)
        account_validator.logger.error.assert_called_once()

    @patch("sys.argv", ["account_validator.py", "journal.ldg", "rules.json"])
    @patch.object(AccountValidator, "load_rules")
    @patch.object(AccountValidator, "validate_accounts")
    @patch("sys.exit")
    @patch("pathlib.Path.exists", side_effect=[True, False])
    def test_run_missing_rules_file(
        self,
        mock_path_exists: MagicMock,
        mock_exit: MagicMock,
        mock_validate_accounts: MagicMock,
        mock_load_rules: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
        mock_rules: Dict[str, List[str]],
    ) -> None:
        """Test run method when rules file is missing."""
        journal_file = tmp_path / "journal.ldg"

        account_validator.run()

        mock_load_rules.assert_not_called()
        mock_validate_accounts.assert_not_called()
        mock_exit.assert_called_once_with(1)
        account_validator.logger.error.assert_called_once()

    @patch("sys.argv", ["account_validator.py"])
    @patch("sys.exit")
    def test_run_incorrect_arguments(
        self, mock_exit: MagicMock, account_validator: AccountValidator
    ) -> None:
        """Test run method with incorrect number of arguments."""
        account_validator.run()
        mock_exit.assert_called_once_with(1)
        account_validator.logger.error.assert_called_once()

    @patch.object(AccountValidator, "parse_args")
    @patch.object(AccountValidator, "run")
    @patch.object(AccountValidator, "_cleanup")
    def test_execute_success(
        self,
        mock_cleanup: MagicMock,
        mock_run: MagicMock,
        mock_parse_args: MagicMock,
        account_validator: AccountValidator,
    ) -> None:
        """Test successful execution of the execute method."""
        mock_parse_args.return_value = MagicMock()

        account_validator.execute()

        mock_parse_args.assert_called_once()
        mock_run.assert_called_once()
        mock_cleanup.assert_called_once()

    @patch.object(AccountValidator, "parse_args")
    @patch.object(AccountValidator, "run")
    @patch.object(AccountValidator, "_cleanup")
    @patch("sys.exit")
    def test_execute_keyboard_interrupt(
        self,
        mock_exit: MagicMock,
        mock_cleanup: MagicMock,
        mock_run: MagicMock,
        mock_parse_args: MagicMock,
        account_validator: AccountValidator,
    ) -> None:
        """Test execute method when a KeyboardInterrupt occurs."""
        mock_parse_args.return_value = MagicMock()
        mock_run.side_effect = KeyboardInterrupt

        account_validator.execute()

        mock_parse_args.assert_called_once()
        mock_run.assert_called_once()
        mock_cleanup.assert_called_once()
        mock_exit.assert_called_once_with(1)
        account_validator.logger.warning.assert_called_once()

    @patch.object(AccountValidator, "parse_args")
    @patch.object(AccountValidator, "run")
    @patch.object(AccountValidator, "_cleanup")
    @patch("sys.exit")
    def test_execute_exception(
        self,
        mock_exit: MagicMock,
        mock_cleanup: MagicMock,
        mock_run: MagicMock,
        mock_parse_args: MagicMock,
        account_validator: AccountValidator,
    ) -> None:
        """Test execute method when a general exception occurs."""
        mock_parse_args.return_value = MagicMock()
        mock_run.side_effect = Exception("Some error")

        account_validator.execute()

        mock_parse_args.assert_called_once()
        mock_run.assert_called_once()
        mock_cleanup.assert_called_once()
        mock_exit.assert_called_once_with(1)
        account_validator.logger.error.assert_called_once()

    def test_cleanup_db_conn_none(self, account_validator: AccountValidator) -> None:
        """Test cleanup method when db_conn is None."""
        account_validator._cleanup()  # db_conn is None by default
        # Assert that no exception is raised

    def test_cleanup_db_conn_close_success(
        self, account_validator: AccountValidator
    ) -> None:
        """Test cleanup method when db_conn is successfully closed."""
        mock_db_conn = MagicMock()
        account_validator.db_conn = mock_db_conn
        account_validator._cleanup()
        mock_db_conn.close.assert_called_once()

    def test_cleanup_db_conn_close_exception(
        self, account_validator: AccountValidator
    ) -> None:
        """Test cleanup method when closing db_conn raises an exception."""
        mock_db_conn = MagicMock()
        mock_db_conn.close.side_effect = Exception("Failed to close connection")
        account_validator.db_conn = mock_db_conn
        account_validator._cleanup()
        mock_db_conn.close.assert_called_once()
        account_validator.logger.warning.assert_called_once()

    def test_get_path_absolute(self, account_validator: AccountValidator) -> None:
        """Test get_path method with an absolute path."""
        absolute_path = "/absolute/path/to/file.txt"
        result = account_validator.get_path(absolute_path)
        assert result == Path(absolute_path)

    def test_get_path_relative(self, account_validator: AccountValidator) -> None:
        """Test get_path method with a relative path."""
        relative_path = "relative/path/to/file.txt"
        expected_path = BaseScript.PROJECT_ROOT / relative_path
        result = account_validator.get_path(relative_path)
        assert result == expected_path

    def test_get_config_value_exists(
        self, account_validator: AccountValidator, mock_config: Dict[str, Any]
    ) -> None:
        """Test get_config_value method when the key exists."""
        account_validator.config = mock_config
        account_validator.config = mock_config["core"]
        value = account_validator.get_config_value("logging.level")
        assert value == "INFO"

    def test_get_config_value_does_not_exist(
        self, account_validator: AccountValidator, mock_config: Dict[str, Any]
    ) -> None:
        """Test get_config_value method when the key does not exist."""
        account_validator.config = mock_config
        value = account_validator.get_config_value("nonexistent.key", "default_value")
        assert value == "default_value"

    def test_get_config_value_nested_key_does_not_exist(
        self, account_validator: AccountValidator, mock_config: Dict[str, Any]
    ) -> None:
        """Test get_config_value method when a nested key does not exist."""
        account_validator.config = mock_config
        value = account_validator.get_config_value(
            "core.nonexistent.key", "default_value"
        )
        assert value == "default_value"

    def test_setup_argparse(self, account_validator: AccountValidator) -> None:
        """Test the setup_argparse method."""
        parser = account_validator.setup_argparse()
        assert parser.description == account_validator.description
        assert parser.format_help()  # Ensure help message can be generated

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_log_level(
        self,
        mock_parse_args: MagicMock,
        account_validator: AccountValidator,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test parse_args method with log level argument."""
        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_args.config = None
        mock_parse_args.return_value = mock_args

        account_validator.parse_args()

        assert account_validator.logger.level == logging.DEBUG
        assert "Log level set to DEBUG" in str(account_validator.logger.debug.call_args)

    @patch("argparse.ArgumentParser.parse_args")
    @patch("yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open, read_data="test_key: test_value")
    def test_parse_args_config_file(
        self,
        mock_open_file: MagicMock,
        mock_yaml_load: MagicMock,
        mock_parse_args: MagicMock,
        account_validator: AccountValidator,
        tmp_path: Path,
    ) -> None:
        """Test parse_args method with config file argument."""
        config_data = {"test_key": "test_value"}
        config_file = tmp_path / "test_config.yaml"
        mock_yaml_load.return_value = config_data

        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = str(config_file)
        mock_parse_args.return_value = mock_args

        account_validator.parse_args()

        assert account_validator.config == config_data
        mock_open_file.assert_called_once_with(str(config_file), 'r')
        mock_yaml_load.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("sys.exit")
    def test_parse_args_config_file_not_found(
        self, mock_exit: MagicMock, mock_parse_args: MagicMock, account_validator: AccountValidator
    ) -> None:
        """Test parse_args method when config file is not found."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = "nonexistent_config.yaml"
        mock_parse_args.return_value = mock_args

        account_validator.parse_args()

        mock_exit.assert_called_once_with(1)
        account_validator.logger.error.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.core.bookkeeping.account_validator.get_connection")
    def test_parse_args_db_connection_string(
        self, mock_get_connection: MagicMock, mock_parse_args: MagicMock, account_validator: AccountValidator
    ) -> None:
        """Test parse_args method with db_connection_string argument."""
        account_validator.requires_db = True
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.db_connection_string = "test_connection_string"
        mock_parse_args.return_value = mock_args

        account_validator.parse_args()
        mock_get_connection.assert_called_once_with(
            {"connection_string": "test_connection_string"}
        )

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.core.bookkeeping.account_validator.get_llm_client")
    def test_parse_args_llm_model(
        self, mock_get_llm_client: MagicMock, mock_parse_args: MagicMock, account_validator: AccountValidator
    ) -> None:
        """Test parse_args method with llm_model argument."""
        account_validator.enable_llm = True
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.llm_model = "test_llm_model"
        mock_parse_args.return_value = mock_args

        account_validator.parse_args()
        mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})

    def test_run_abstract(self, account_validator: AccountValidator) -> None:
        """Test that the run method is abstract."""
        with pytest.raises(TypeError):
            BaseScript.run(account_validator)
