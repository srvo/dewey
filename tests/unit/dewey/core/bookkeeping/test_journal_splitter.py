"""Tests for dewey.core.bookkeeping.journal_splitter."""

import pytest
import os
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
from typing import Dict, Any, List

from dewey.core.bookkeeping.journal_splitter import JournalSplitter, main, FileSystemInterface, ConfigInterface


@pytest.fixture
def mock_file_system() -> MagicMock:
    """Fixture to create a mock FileSystemInterface."""
    mock = MagicMock(spec=FileSystemInterface)
    mock.open = mock_open()
    mock.mkdir.return_value = None
    mock.basename.return_value = "test_1234.journal"
    mock.join.side_effect = os.path.join
    mock.listdir.return_value = []
    return mock


@pytest.fixture
def mock_config() -> MagicMock:
    """Fixture to create a mock ConfigInterface."""
    mock = MagicMock(spec=ConfigInterface)
    mock.get_config_value.return_value = "/tmp/journals"
    return mock


@pytest.fixture
def journal_splitter(mock_file_system: MagicMock, mock_config: MagicMock) -> JournalSplitter:
    """Fixture to create a JournalSplitter instance with mocked dependencies."""
    with patch("dewey.core.bookkeeping.journal_splitter.BaseScript.__init__", return_value=None):
        splitter = JournalSplitter(file_system=mock_file_system, config=mock_config)
        splitter.logger = MagicMock()  # Mock the logger directly
        return splitter


def test_journal_splitter_initialization(journal_splitter: JournalSplitter) -> None:
    """Test JournalSplitter initialization."""
    assert journal_splitter.config_section == "bookkeeping"
    assert journal_splitter.logger is not None
    assert journal_splitter.file_system is not None
    assert journal_splitter.config is not None


def test_extract_year(journal_splitter: JournalSplitter) -> None:
    """Test the _extract_year method."""
    assert journal_splitter._extract_year("2023-01-01 Description") == "2023"
    assert journal_splitter._extract_year("2024-12-31 Another Description") == "2024"
    assert journal_splitter._extract_year("invalid-date Description") is None
    assert journal_splitter._extract_year("") is None


def test_process_transaction_line(journal_splitter: JournalSplitter) -> None:
    """Test the _process_transaction_line method."""
    bank_account = "assets:checking:mercury1234"
    assert journal_splitter._process_transaction_line("expenses:unknown 100", bank_account) == "expenses:unclassified 100"
    assert journal_splitter._process_transaction_line("income:unknown -100", bank_account) == "income:unknown -100".replace("income:unknown", bank_account)
    assert journal_splitter._process_transaction_line("No replacement needed", bank_account) == "No replacement needed"


def test_process_transaction_line_no_change(journal_splitter: JournalSplitter) -> None:
    """Test the _process_transaction_line method when no replacement is needed."""
    bank_account = "assets:checking:mercury1234"
    line = "assets:checking:boa3456"
    processed_line = journal_splitter._process_transaction_line(line, bank_account)
    assert processed_line == line


def test_process_transaction_line_empty_line(journal_splitter: JournalSplitter) -> None:
    """Test the _process_transaction_line method with an empty line."""
    bank_account = "assets:checking:mercury1234"
    line = ""
    processed_line = journal_splitter._process_transaction_line(line, bank_account)
    assert processed_line == line


@patch("os.path.basename")
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open)
def test_split_journal_by_year(
    mock_open_file: MagicMock,
    mock_mkdir: MagicMock,
    mock_basename: MagicMock,
    journal_splitter: JournalSplitter,
    mock_config: Dict[str, Any],
    tmp_path: Path,
) -> None:
    """Test splitting a journal file by year."""
    input_file = str(tmp_path / "test_1234.journal")
    output_dir = str(tmp_path / "output")
    mock_basename.return_value = "test_1234.journal"

    journal_content = """2023-01-01 Description 1
    expenses:unknown  100
    income:unknown  -100

2023-02-01 Description 2
    expenses:unknown  200
    income:unknown  -200

2024-01-01 Description 3
    expenses:unknown  300
    income:unknown  -300
"""
    mock_open_file.return_value.read.return_value = journal_content
    mock_open_file.side_effect = [
        mock_open(read_data=journal_content).return_value,
        mock_open().return_value,
        mock_open().return_value,
    ]

    journal_splitter.split_journal_by_year(input_file, output_dir)

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    assert mock_open_file.call_count == 3  # 1 read, 2 writes

    calls = mock_open_file.mock_calls
    assert str(tmp_path / "output/test_1234_2023.journal") in str(calls[1])
    assert str(tmp_path / "output/test_1234_2024.journal") in str(calls[2])

    # Verify writes
    write_calls = mock_open_file.return_value.write.mock_calls
    assert len(write_calls) == 2
    assert "2023-01-01 Description 1" in str(write_calls[0])
    assert "2024-01-01 Description 3" in str(write_calls[1])


def test_split_journal_by_year_with_mocks(
    journal_splitter: JournalSplitter, mock_file_system: MagicMock
) -> None:
    """Test splitting a journal file by year using mock_file_system."""
    input_file = "input.journal"
    output_dir = "output_dir"
    journal_content = """2023-01-01 Description 1
    expenses:unknown  100
    income:unknown  -100

2024-01-01 Description 3
    expenses:unknown  300
    income:unknown  -300
"""
    mock_file_system.open.return_value.__iter__.return_value = journal_content.splitlines()
    mock_file_system.basename.return_value = "input.journal"

    journal_splitter.split_journal_by_year(input_file, output_dir)

    mock_file_system.mkdir.assert_called_once_with(output_dir, parents=True, exist_ok=True)
    assert mock_file_system.open.call_count == 3  # 1 read, 2 write
    mock_file_system.open.assert_called_with(os.path.join(output_dir, "input_2024.journal"), "w")


def test_split_journal_by_year_empty_file(
    journal_splitter: JournalSplitter, mock_file_system: MagicMock, tmp_path: Path
) -> None:
    """Test splitting an empty journal file."""
    input_file = str(tmp_path / "empty.journal")
    output_dir = str(tmp_path / "output")
    mock_file_system.basename.return_value = "empty.journal"
    mock_file_system.open.return_value.__iter__.return_value = []

    journal_splitter.split_journal_by_year(input_file, output_dir)

    mock_file_system.mkdir.assert_called_once_with(output_dir, parents=True, exist_ok=True)
    mock_file_system.open.assert_called_once_with(input_file)
    mock_file_system.open.return_value.close.assert_called_once()
    mock_file_system.open.return_value.write.assert_not_called()


def test_split_journal_by_year_invalid_date(
    journal_splitter: JournalSplitter, mock_file_system: MagicMock, tmp_path: Path
) -> None:
    """Test splitting a journal file with an invalid date format."""
    input_file = str(tmp_path / "invalid_date.journal")
    output_dir = str(tmp_path / "output")
    mock_file_system.basename.return_value = "invalid_date.journal"
    invalid_date_content = "invalid-date-format Description\n  expenses:unknown 100\n  income:unknown -100"
    mock_file_system.open.return_value.__iter__.return_value = invalid_date_content.splitlines()

    journal_splitter.split_journal_by_year(input_file, output_dir)

    mock_file_system.mkdir.assert_called_once_with(output_dir, parents=True, exist_ok=True)
    mock_file_system.open.assert_called_once_with(input_file)
    mock_file_system.open.return_value.close.assert_called_once()
    mock_file_system.open.return_value.write.assert_not_called()


def test_split_journal_by_year_replace_accounts(
    journal_splitter: JournalSplitter, mock_file_system: MagicMock, tmp_path: Path
) -> None:
    """Test that the account replacement works correctly."""
    input_file = str(tmp_path / "test_5678.journal")
    output_dir = str(tmp_path / "output")
    mock_file_system.basename.return_value = "test_5678.journal"
    journal_content = """2023-01-01 Description 1
    expenses:unknown  100
    income:unknown  -100
"""
    mock_file_system.open.return_value.__iter__.return_value = journal_content.splitlines()

    journal_splitter.split_journal_by_year(input_file, output_dir)

    mock_file_system.mkdir.assert_called_once_with(output_dir, parents=True, exist_ok=True)
    assert mock_file_system.open.call_count == 2

    write_calls = mock_file_system.open.return_value.write.mock_calls
    assert len(write_calls) == 1
    assert "expenses:unclassified" in str(write_calls[0])
    assert "assets:checking:mercury5678" in str(write_calls[0])


def test_run(
    journal_splitter: JournalSplitter, mock_file_system: MagicMock, mock_config: MagicMock
) -> None:
    """Test the run method."""
    mock_file_system.listdir.return_value = ["test_1234.journal", "test_5678.journal"]
    mock_file_system.join.side_effect = os.path.join

    journal_splitter.run()

    mock_config.get_config_value.assert_called_once_with("bookkeeping.journal_dir")
    assert journal_splitter.logger.info.call_count == 4
    assert mock_file_system.join.call_count == 3
    mock_file_system.join.assert_called_with("/tmp/journals", "by_year")
    assert mock_file_system.listdir.call_count == 1
    assert mock_file_system.listdir.called_with("/tmp/journals")
    assert mock_file_system.open.call_count == 0


def test_run_no_journal_files(
    journal_splitter: JournalSplitter, mock_file_system: MagicMock, mock_config: MagicMock
) -> None:
    """Test the run method when there are no journal files."""
    mock_file_system.listdir.return_value = []

    journal_splitter.run()

    mock_config.get_config_value.assert_called_once_with("bookkeeping.journal_dir")
    assert journal_splitter.logger.info.call_count == 0


def test_run_with_dot_file(
    journal_splitter: JournalSplitter, mock_file_system: MagicMock, mock_config: MagicMock
) -> None:
    """Test the run method when there is a dot file in the journal directory."""
    mock_file_system.listdir.return_value = [".DS_Store", "test_1234.journal"]

    journal_splitter.run()

    mock_config.get_config_value.assert_called_once_with("bookkeeping.journal_dir")
    assert journal_splitter.logger.info.call_count == 2


@patch("dewey.core.bookkeeping.journal_splitter.JournalSplitter.execute")
@patch("dewey.core.bookkeeping.journal_splitter.JournalSplitter.__init__", return_value=None)
def test_main(mock_init: MagicMock, mock_execute: MagicMock) -> None:
    """Test the main function."""
    main()
    mock_execute.assert_called_once()
