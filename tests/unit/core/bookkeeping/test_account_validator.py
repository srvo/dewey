"""Test module for account_validator.py."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from dewey.core.bookkeeping.account_validator import (
    AccountValidator,
    FileSystemInterface,
    RealFileSystem,
)


class MockFileSystem(FileSystemInterface):
    """Mock implementation of FileSystemInterface for testing."""

    def __init__(
        self, files: dict[str, str] = None, existing_files: set = None,
    ) -> None:
        """Initialize with optional files dictionary and existing files set."""
        self.files = files or {}
        self.existing_files = existing_files or set()

    def open(self, path: Path, mode: str = "r") -> object:
        """Mock file open operation."""
        path_str = str(path)
        if path_str not in self.files and "r" in mode:
            raise FileNotFoundError(f"File not found: {path_str}")
        return mock_open(read_data=self.files.get(path_str, ""))(str(path), mode)

    def exists(self, path: Path) -> bool:
        """Mock file existence check."""
        return str(path) in self.existing_files


@pytest.fixture()
def mock_fs() -> MockFileSystem:
    """Fixture providing a mock file system."""
    sample_rules = json.dumps(
        {
            "categories": [
                "Assets:Checking",
                "Income:Salary",
                "Expenses:Food",
                "Expenses:Utilities",
            ],
        },
    )

    fs = MockFileSystem(
        files={"rules.json": sample_rules},
        existing_files={"journal.hledger", "rules.json"},
    )

    return fs


@pytest.fixture()
def validator(mock_fs: MockFileSystem) -> AccountValidator:
    """Fixture providing an AccountValidator with mock file system."""
    return AccountValidator(fs=mock_fs)


@pytest.fixture()
def mock_sys_exit() -> MagicMock:
    """Fixture to provide a mock for sys.exit."""
    with patch("sys.exit") as mock_exit:
        yield mock_exit


class TestFileSystemInterface:
    """Tests for the FileSystemInterface Protocol implementation."""

    def test_real_file_system_implements_interface(self) -> None:
        """Test that RealFileSystem implements FileSystemInterface."""
        fs = RealFileSystem()

        # Test interface methods exist
        assert hasattr(fs, "open")
        assert hasattr(fs, "exists")


class TestAccountValidator:
    """Tests for the AccountValidator class."""

    def test_init(self) -> None:
        """Test initialization of AccountValidator."""
        # Test with default values
        validator = AccountValidator()
        assert isinstance(validator.fs, RealFileSystem)

        # Test with mock file system
        mock_fs = MockFileSystem()
        validator = AccountValidator(fs=mock_fs)
        assert validator.fs == mock_fs

    def test_load_rules(self, validator: AccountValidator) -> None:
        """Test loading classification rules."""
        rules = validator.load_rules(Path("rules.json"))

        assert rules is not None
        assert "categories" in rules
        assert len(rules["categories"]) == 4
        assert "Assets:Checking" in rules["categories"]
        assert "Expenses:Food" in rules["categories"]

    def test_load_rules_file_not_found(self, validator: AccountValidator) -> None:
        """Test error handling when rules file is not found."""
        with pytest.raises(Exception):
            validator.load_rules(Path("nonexistent_file.json"))

    @patch("json.load")
    def test_load_rules_invalid_json(
        self, mock_json_load: MagicMock, validator: AccountValidator,
    ) -> None:
        """Test error handling when rules file contains invalid JSON."""
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with pytest.raises(Exception):
            validator.load_rules(Path("rules.json"))

    def test_validate_accounts_success(self, validator: AccountValidator) -> None:
        """Test successful account validation."""
        # Mock subprocess.run to return accounts matching the rules
        mock_result = MagicMock()
        mock_result.stdout = (
            "Assets:Checking\nIncome:Salary\nExpenses:Food\nExpenses:Utilities\n"
        )

        mock_run = MagicMock(return_value=mock_result)

        rules = validator.load_rules(Path("rules.json"))
        result = validator.validate_accounts(
            Path("journal.hledger"), rules, run_command=mock_run,
        )

        assert result is True
        mock_run.assert_called_once()

        # Verify the hledger command was called correctly
        args, kwargs = mock_run.call_args
        assert args[0][0] == "hledger"
        assert args[0][1] == "accounts"
        assert args[0][2] == "-f"
        assert "journal.hledger" in str(args[0][3])

    def test_validate_accounts_missing_accounts(
        self, validator: AccountValidator,
    ) -> None:
        """Test validation with missing accounts."""
        # Mock subprocess.run to return only some of the accounts
        mock_result = MagicMock()
        mock_result.stdout = "Assets:Checking\nIncome:Salary\n"

        mock_run = MagicMock(return_value=mock_result)

        rules = validator.load_rules(Path("rules.json"))
        result = validator.validate_accounts(
            Path("journal.hledger"), rules, run_command=mock_run,
        )

        assert result is False
        mock_run.assert_called_once()

    def test_validate_accounts_hledger_error(self, validator: AccountValidator) -> None:
        """Test error handling when hledger command fails."""
        # Mock subprocess.run to raise CalledProcessError
        mock_run = MagicMock(
            side_effect=subprocess.CalledProcessError(1, "hledger", "Command failed"),
        )

        rules = validator.load_rules(Path("rules.json"))

        with pytest.raises(subprocess.CalledProcessError):
            validator.validate_accounts(
                Path("journal.hledger"), rules, run_command=mock_run,
            )

    def test_validate_accounts_other_error(self, validator: AccountValidator) -> None:
        """Test error handling for other errors during validation."""
        # Mock subprocess.run to raise another exception
        mock_run = MagicMock(side_effect=Exception("Unexpected error"))

        rules = validator.load_rules(Path("rules.json"))

        with pytest.raises(Exception):
            validator.validate_accounts(
                Path("journal.hledger"), rules, run_command=mock_run,
            )

    @patch("sys.argv", ["account_validator.py", "journal.hledger", "rules.json"])
    @patch("sys.exit")
    def test_run_success(
        self, mock_exit: MagicMock, validator: AccountValidator,
    ) -> None:
        """Test successful execution of run method."""
        with patch.object(validator, "load_rules") as mock_load:
            with patch.object(
                validator, "validate_accounts", return_value=True,
            ) as mock_validate:
                # Configure mocks
                mock_load.return_value = {"categories": ["Assets:Checking"]}

                # Execute run
                validator.run()

                # Check that methods were called with correct parameters
                mock_load.assert_called_once()
                mock_validate.assert_called_once()
                mock_exit.assert_not_called()

    @patch("sys.argv", ["account_validator.py", "journal.hledger", "rules.json"])
    @patch("sys.exit")
    def test_run_validation_failure(
        self, mock_exit: MagicMock, validator: AccountValidator,
    ) -> None:
        """Test run method when validation fails."""
        with patch.object(validator, "load_rules") as mock_load:
            with patch.object(
                validator, "validate_accounts", return_value=False,
            ) as mock_validate:
                # Configure mocks
                mock_load.return_value = {"categories": ["Assets:Checking"]}

                # Execute run
                validator.run()

                # Check that methods were called with correct parameters
                mock_load.assert_called_once()
                mock_validate.assert_called_once()
                mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["account_validator.py", "journal.hledger", "rules.json"])
    @patch("sys.exit")
    def test_run_load_error(
        self, mock_exit: MagicMock, validator: AccountValidator,
    ) -> None:
        """Test run method when rules loading fails."""
        with patch.object(
            validator, "load_rules", side_effect=Exception("Failed to load rules"),
        ):
            # Execute run
            validator.run()

            # Check that exit was called
            mock_exit.assert_called_once_with(1)

    def test_run_invalid_args(self, validator: AccountValidator) -> None:
        """Test run method with invalid arguments."""
        # Patch inside the test to avoid issues with other tests
        with patch("sys.argv", ["account_validator.py"]):
            # Mock sys.exit to capture the exit code instead of raising exception
            with patch("sys.exit") as mock_exit:
                try:
                    # Ensure sys.exit is properly mocked before calling run
                    validator.run()
                except IndexError:
                    # Pass because we expect it to try to access sys.argv[1] which won't exist
                    pass
                mock_exit.assert_called_once_with(1)

    def test_run_journal_not_found(
        self, validator: AccountValidator, mock_sys_exit: MagicMock,
    ) -> None:
        """Test run method when journal file is not found."""
        mock_argv = [
            "account_validator.py",
            "nonexistent_journal.journal",
            "rules.json",
        ]

        # Mock the logger
        mock_logger = MagicMock()
        validator.logger = mock_logger

        with patch("sys.argv", mock_argv):
            with patch(
                "os.path.exists", lambda path: path != "nonexistent_journal.journal",
            ):
                validator.run()

                # Check that sys.exit was called with the correct error code
                mock_sys_exit.assert_any_call(1)
                mock_logger.error.assert_any_call(
                    "Journal file not found: nonexistent_journal.journal",
                )

    def test_run_rules_not_found(
        self, validator: AccountValidator, mock_sys_exit: MagicMock,
    ) -> None:
        """Test run method when rules file is not found."""
        mock_argv = [
            "account_validator.py",
            "journal.journal",
            "nonexistent_rules.json",
        ]

        # Mock the logger
        mock_logger = MagicMock()
        validator.logger = mock_logger

        with patch("sys.argv", mock_argv):
            with patch("os.path.exists", lambda path: path != "nonexistent_rules.json"):
                validator.run()

                # Check that sys.exit was called with the correct error code
                mock_sys_exit.assert_any_call(1)
                mock_logger.error.assert_any_call(
                    "Rules file not found: nonexistent_rules.json",
                )
