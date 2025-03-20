"""Tests for dewey.core.bookkeeping.ledger_checker."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import subprocess
from pathlib import Path
from typing import List, Any, Dict, Optional

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.ledger_checker import LedgerFormatChecker, main, FileSystemInterface, SubprocessInterface


@pytest.fixture
def mock_fs() -> MagicMock:
    """Mocks the FileSystemInterface."""
    return MagicMock(spec=FileSystemInterface)


@pytest.fixture
def mock_subprocess_runner() -> MagicMock:
    """Mocks the SubprocessInterface."""
    return MagicMock(spec=SubprocessInterface)


@pytest.fixture
def ledger_checker(mock_base_script: MagicMock, mock_fs: MagicMock, mock_subprocess_runner: MagicMock, tmp_path: Path) -> LedgerFormatChecker:
    """Creates a LedgerFormatChecker instance with mocked dependencies."""
    journal_file = tmp_path / "test_journal.ledger"
    ledger_checker = LedgerFormatChecker(str(journal_file), fs=mock_fs, subprocess_runner=mock_subprocess_runner)
    ledger_checker.logger = mock_base_script.logger
    ledger_checker.get_config_value = mock_base_script.get_config_value
    return ledger_checker


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_init(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker, tmp_path: Path) -> None:
    """Tests the initialization of the LedgerFormatChecker."""
    assert ledger_checker.journal_file == str(tmp_path / "test_journal.ledger")
    assert ledger_checker.warnings == []
    assert ledger_checker.errors == []
    assert ledger_checker.journal_content == []
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_read_journal_success(mock_base_init: MagicMock, mock_fs: MagicMock, ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests reading the journal file successfully."""
    mock_file = mock_open(read_data="".join(sample_journal_content))
    mock_fs.open.return_value = mock_file.return_value
    ledger_checker.read_journal()
    assert ledger_checker.journal_content == sample_journal_content
    mock_fs.open.assert_called_once_with(ledger_checker.journal_file, "r")
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_read_journal_file_not_found(mock_base_init: MagicMock, mock_fs: MagicMock, ledger_checker: LedgerFormatChecker, tmp_path: Path) -> None:
    """Tests handling of a missing journal file."""
    mock_fs.open.side_effect = FileNotFoundError("File not found")
    ledger_checker.journal_file = str(tmp_path / "nonexistent_journal.ledger")
    ledger_checker.read_journal()
    assert ledger_checker.journal_content == []
    assert "Journal file not found" in ledger_checker.errors
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_read_journal_error(mock_base_init: MagicMock, mock_fs: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests handling of an error while reading the journal file."""
    mock_fs.open.side_effect = Exception("Failed to read file")
    ledger_checker.read_journal()
    assert ledger_checker.journal_content == []
    assert "Error reading journal file" in ledger_checker.errors
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_check_hledger_basic_success(mock_base_init: MagicMock, mock_subprocess_runner: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests successful hledger validation."""
    mock_subprocess_runner.run.return_value.returncode = 0
    assert ledger_checker.check_hledger_basic() is True
    ledger_checker.logger.info.assert_called_with("hledger validation passed")
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_check_hledger_basic_failure(mock_base_init: MagicMock, mock_subprocess_runner: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests failed hledger validation."""
    mock_subprocess_runner.run.return_value.returncode = 1
    mock_subprocess_runner.run.return_value.stderr = "hledger validation failed"
    assert ledger_checker.check_hledger_basic() is False
    assert "hledger validation failed" in ledger_checker.warnings
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_check_hledger_basic_called_process_error(mock_base_init: MagicMock, mock_subprocess_runner: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests handling of a CalledProcessError during hledger validation."""
    mock_subprocess_runner.run.side_effect = subprocess.CalledProcessError(1, "cmd")
    assert ledger_checker.check_hledger_basic() is False
    assert "hledger command failed" in ledger_checker.errors
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_check_hledger_basic_file_not_found_error(mock_base_init: MagicMock, mock_subprocess_runner: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests handling of a FileNotFoundError during hledger validation."""
    mock_subprocess_runner.run.side_effect = FileNotFoundError
    assert ledger_checker.check_hledger_basic() is False
    assert "hledger not found" in ledger_checker.errors
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_check_date_format(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the date format check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_date_format()
    assert len(ledger_checker.warnings) == 1
    assert "Invalid date format on line 4" in ledger_checker.warnings
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_check_accounts(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the account format check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_accounts()
    assert len(ledger_checker.warnings) == 1
    assert "Invalid account format on line 7" in ledger_checker.warnings
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_check_amount_format(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the amount format check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_amount_format()
    assert len(ledger_checker.warnings) == 0  # No invalid amount formats in the sample
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_check_description_length(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the description length check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_description_length()
    assert len(ledger_checker.warnings) == 1
    assert "Description too long on line 9" in ledger_checker.warnings
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_check_currency_consistency(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker, sample_journal_content: List[str]) -> None:
    """Tests the currency consistency check."""
    ledger_checker.journal_content = sample_journal_content
    ledger_checker.check_currency_consistency()
    assert len(ledger_checker.warnings) == 1
    assert "Currency inconsistency on line 12" in ledger_checker.warnings
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_run_all_checks_success(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests running all checks successfully."""
    ledger_checker.check_hledger_basic = MagicMock(return_value=True)
    ledger_checker.check_date_format = MagicMock()
    ledger_checker.check_accounts = MagicMock()
    ledger_checker.check_amount_format = MagicMock()
    ledger_checker.check_description_length = MagicMock()
    ledger_checker.check_currency_consistency = MagicMock()
    assert ledger_checker.run_all_checks() is True
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_run_all_checks_with_errors(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests running all checks with errors."""
    ledger_checker.check_hledger_basic = MagicMock(return_value=False)
    ledger_checker.check_date_format = MagicMock()
    ledger_checker.check_accounts = MagicMock()
    ledger_checker.check_amount_format = MagicMock()
    ledger_checker.check_description_length = MagicMock()
    ledger_checker.check_currency_consistency = MagicMock()
    assert ledger_checker.run_all_checks() is False
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_run_success(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests the run method."""
    ledger_checker.run_all_checks = MagicMock(return_value=True)
    assert ledger_checker.run() is True
    ledger_checker.logger.info.assert_called_with("All ledger checks passed successfully")
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_run_with_warnings(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests the run method with warnings."""
    ledger_checker.run_all_checks = MagicMock(return_value=False)
    ledger_checker.warnings = ["Warning 1"]
    ledger_checker.errors = []
    assert ledger_checker.run() is False
    ledger_checker.logger.warning.assert_called_with("Validation warnings occurred")
    mock_base_init.assert_called_once()


@patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
def test_run_with_errors(mock_base_init: MagicMock, ledger_checker: LedgerFormatChecker) -> None:
    """Tests the run method with errors."""
    ledger_checker.run_all_checks = MagicMock(return_value=False)
    ledger_checker.warnings = []
    ledger_checker.errors = ["Error 1"]
    assert ledger_checker.run() is False
    ledger_checker.logger.error.assert_called_with("Validation errors detected")
    mock_base_init.assert_called_once()


@patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(journal_file="test.ledger"))
@patch("dewey.core.bookkeeping.ledger_checker.LedgerFormatChecker.run")
def test_main_success(mock_run: MagicMock, mock_args: MagicMock) -> None:
    """Tests the main function."""
    mock_run.return_value = True
    main()
    mock_run.assert_called()


@patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(journal_file="test.ledger"))
@patch("dewey.core.bookkeeping.ledger_checker.LedgerFormatChecker.run")
def test_main_failure(mock_run: MagicMock, mock_args: MagicMock) -> None:
    """Tests the main function."""
    mock_run.return_value = False
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
    mock_run.assert_called()
