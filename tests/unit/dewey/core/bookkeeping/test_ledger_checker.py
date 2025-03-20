"""Tests for dewey.core.bookkeeping.ledger_checker."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import subprocess
from pathlib import Path
from typing import List, Any, Dict, Optional

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.ledger_checker import LedgerFormatChecker, main


@pytest.fixture
def mock_base_script(tmp_path: Path) -> MagicMock:
    """Mocks the BaseScript class."""
    mock = MagicMock(spec=BaseScript)
    mock.logger = MagicMock()
    mock.config = {}
    mock.get_path.return_value = tmp_path
    mock.get_config_value.return_value = 50  # Default max_description_length
    return mock


@pytest.fixture
def ledger_checker(mock_base_script: MagicMock, tmp_path: Path) -> LedgerFormatChecker:
    """Creates a LedgerFormatChecker instance with a temporary journal file."""
    journal_file = tmp_path / "test_journal.ledger"
    journal_file.write_text("")  # Create an empty journal file
    ledger_checker = LedgerFormatChecker(str(journal_file))
    ledger_checker.logger = mock_base_script.logger
    ledger_checker.get_config_value = mock_base_script.get_config_value
    return ledger_checker


@pytest.fixture
def sample_journal_content() -> List[str]:
    """Provides sample journal content for testing."""
    return [
        "2024/01/01 Description\n",
        "  Assets:Checking   $100\n",
        "  Income:Salary  $-100\n",
        "2024/01/02  Invalid Date Format\n",
        "  Assets:Checking   $50\n",
        "  Expenses:Groceries  $-50\n",
        "Assets:Savings   $200\n",  # Invalid account format
        "  Expenses:Rent  $-200\n",
        "2024/01/03 Description with a very long description exceeding the maximum length\n",
        "  Assets:Checking   $75\n",
        "  Expenses:Dining  $-75\n",
        "2024/01/04 Description with different currency\n",
        "  Assets:Checking   100 EUR\n",
        "  Expenses:Gifts  -100 EUR\n",
    ]


def test_init(ledger_checker: LedgerFormatChecker, tmp_path: Path) -> None:
    """Tests the initialization of the LedgerFormatChecker."""
    assert ledger_checker.journal_file == str(tmp_path / "test_journal.ledger")
    assert ledger_checker.warnings == []
    assert ledger_checker.errors == []
    assert ledger_checker.journal_content == []


@patch("builtins.open", new_callable=mock_open, read_data="")
def test_read_journal_success(mock_file: MagicMock, ledger_checker: LedgerFormatChecker, tmp_path: Path, sample_journal_content: List[str]) -> None:
    """Tests reading the journal file successfully."""
    journal_file = tmp_path / "test_journal.ledger"
    mock_file.return_value.readlines.return_value = sample_journal_content
    ledger_checker.journal_file = str(journal_file)
    ledger_checker.read_journal()
    assert ledger_checker.journal_content == sample_journal_content


def test_read_journal_file_not_found(ledger_checker: LedgerFormatChecker, tmp_path: Path) -> None:
    """Tests handling of a missing journal file."""
    ledger_checker.journal_file = str(tmp_path / "nonexistent_journal.ledger")
    ledger_checker.read_journal()
    assert ledger_checker.journal_content == []
    assert "Journal file not found" in ledger_checker.errors


@patch("builtins.open", side_effect=Exception("Failed to read file"))
def test_read_journal_error(mock_open: MagicMock, ledger_checker: LedgerFormatChecker, tmp_path: Path) -> None:
    """Tests handling of an error while reading the journal file."""
    journal_file = tmp_path / "test_journal.ledger"
    ledger_checker.journal_file = str(journal_file)
    ledger_checker.read_journal()
    assert ledger_checker.journal_content == []
    assert "Error reading journal file" in ledger_checker.errors


@patch("subprocess.run")
def test_check_hledger_basic_success(mock_run: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests successful hledger validation."""
    mock_run.return_value.returncode = 0
    assert ledger_checker.check_hledger_basic() is True
    ledger_checker.logger.info.assert_called_with("hledger validation passed")


@patch("subprocess.run")
def test_check_hledger_basic_failure(mock_run: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests failed hledger validation."""
    mock_run.return_value.returncode = 1
    assert ledger_checker.check_hledger_basic() is False
    assert "hledger validation failed" in ledger_checker.warnings


@patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd"))
def test_check_hledger_basic_called_process_error(self, mock_run: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests handling of a CalledProcessError during hledger validation."""
    assert ledger_checker.check_hledger_basic() is False
    assert "hledger command failed" in ledger_checker.errors


@patch("subprocess.run", side_effect=FileNotFoundError)
def test_check_hledger_basic_file_not_found_error(self, mock_run: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests handling of a FileNotFoundError during hledger validation."""
    assert ledger_checker.check_hledger_basic() is False
    assert "hledger not found" in ledger_checker.errors


def test_check_date_format(ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the date format check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_date_format()
    assert len(ledger_checker.warnings) == 1
    assert "Invalid date format on line 4" in ledger_checker.warnings


def test_check_accounts(ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the account format check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_accounts()
    assert len(ledger_checker.warnings) == 1
    assert "Invalid account format on line 7" in ledger_checker.warnings


def test_check_amount_format(ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the amount format check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_amount_format()
    assert len(ledger_checker.warnings) == 0  # No invalid amount formats in the sample


def test_check_description_length(ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the description length check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_description_length()
    assert len(ledger_checker.warnings) == 1
    assert "Description too long on line 9" in ledger_checker.warnings


def test_check_currency_consistency(ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the currency consistency check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_currency_consistency()
    assert len(ledger_checker.warnings) == 1
    assert "Currency inconsistency on line 12" in ledger_checker.warnings


def test_run_all_checks_success(ledger_checker: LedgerFormatChecker) -> None:
    """Tests running all checks successfully."""
    ledger_checker.check_hledger_basic = MagicMock(return_value=True)
    ledger_checker.check_date_format = MagicMock()
    ledger_checker.check_accounts = MagicMock()
    ledger_checker.check_amount_format = MagicMock()
    ledger_checker.check_description_length = MagicMock()
    ledger_checker.check_currency_consistency = MagicMock()
    assert ledger_checker.run_all_checks() is True


def test_run_all_checks_with_errors(ledger_checker: LedgerFormatChecker) -> None:
    """Tests running all checks with errors."""
    ledger_checker.check_hledger_basic = MagicMock(return_value=False)
    ledger_checker.check_date_format = MagicMock()
    ledger_checker.check_accounts = MagicMock()
    ledger_checker.check_amount_format = MagicMock()
    ledger_checker.check_description_length = MagicMock()
    ledger_checker.check_currency_consistency = MagicMock()
    assert ledger_checker.run_all_checks() is False


def test_run(ledger_checker: LedgerFormatChecker) -> None:
    """Tests the run method."""
    ledger_checker.run_all_checks = MagicMock(return_value=True)
    ledger_checker.run()
    ledger_checker.logger.info.assert_called_with("All ledger checks passed successfully")


def test_run_with_warnings(ledger_checker: LedgerFormatChecker) -> None:
    """Tests the run method with warnings."""
    ledger_checker.run_all_checks = MagicMock(return_value=False)
    ledger_checker.warnings = ["Warning 1"]
    ledger_checker.errors = []
    ledger_checker.run()
    ledger_checker.logger.warning.assert_called_with("Validation warnings occurred")


def test_run_with_errors(ledger_checker: LedgerFormatChecker) -> None:
    """Tests the run method with errors."""
    ledger_checker.run_all_checks = MagicMock(return_value=False)
    ledger_checker.warnings = []
    ledger_checker.errors = ["Error 1"]
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        ledger_checker.run()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
    ledger_checker.logger.error.assert_called_with("Validation errors detected")


@patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(journal_file="test.ledger"))
@patch("dewey.core.bookkeeping.ledger_checker.LedgerFormatChecker.run")
def test_main(mock_run: MagicMock, mock_args: MagicMock) -> None:
    """Tests the main function."""
    main()
    mock_run.assert_called()
