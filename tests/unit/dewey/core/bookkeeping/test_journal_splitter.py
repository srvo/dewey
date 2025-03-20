"""Tests for dewey.core.bookkeeping.journal_splitter."""

import pytest
import os
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
from typing import Dict, Any

from dewey.core.bookkeeping.journal_splitter import JournalSplitter, main


@pytest.fixture
def journal_splitter(mock_base_script: MagicMock) -> JournalSplitter:
    """Fixture to create a JournalSplitter instance with mocked BaseScript."""
    with patch("dewey.core.bookkeeping.journal_splitter.BaseScript.__init__", return_value=None):
        splitter = JournalSplitter()
        splitter.config = mock_base_script.config
        splitter.logger = mock_base_script.logger
        return splitter


def test_journal_splitter_initialization(journal_splitter: JournalSplitter) -> None:
    """Test JournalSplitter initialization."""
    assert journal_splitter.config_section == "bookkeeping"
    assert journal_splitter.logger is not None


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


@patch("os.path.basename")
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open)
def test_split_journal_by_year_empty_file(
    mock_open_file: MagicMock,
    mock_mkdir: MagicMock,
    mock_basename: MagicMock,
    journal_splitter: JournalSplitter,
    tmp_path: Path,
) -> None:
    """Test splitting an empty journal file."""
    input_file = str(tmp_path / "empty.journal")
    output_dir = str(tmp_path / "output")
    mock_basename.return_value = "empty.journal"
    mock_open_file.return_value.read.return_value = ""

    journal_splitter.split_journal_by_year(input_file, output_dir)

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_open_file.assert_called_once_with(input_file)
    mock_open_file.return_value.close.assert_called_once()
    mock_open_file.return_value.write.assert_not_called()


@patch("os.path.basename")
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open)
def test_split_journal_by_year_invalid_date(
    mock_open_file: MagicMock,
    mock_mkdir: MagicMock,
    mock_basename: MagicMock,
    journal_splitter: JournalSplitter,
    tmp_path: Path,
) -> None:
    """Test splitting a journal file with an invalid date format."""
    input_file = str(tmp_path / "invalid_date.journal")
    output_dir = str(tmp_path / "output")
    mock_basename.return_value = "invalid_date.journal"
    invalid_date_content = "invalid-date-format Description\n  expenses:unknown 100\n  income:unknown -100"
    mock_open_file.return_value.read.return_value = invalid_date_content

    journal_splitter.split_journal_by_year(input_file, output_dir)

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_open_file.assert_called_once_with(input_file)
    mock_open_file.return_value.close.assert_called_once()
    mock_open_file.return_value.write.assert_not_called()


@patch("os.path.basename")
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open)
def test_split_journal_by_year_replace_accounts(
    mock_open_file: MagicMock,
    mock_mkdir: MagicMock,
    mock_basename: MagicMock,
    journal_splitter: JournalSplitter,
    tmp_path: Path,
) -> None:
    """Test that the account replacement works correctly."""
    input_file = str(tmp_path / "test_5678.journal")
    output_dir = str(tmp_path / "output")
    mock_basename.return_value = "test_5678.journal"
    journal_content = """2023-01-01 Description 1
    expenses:unknown  100
    income:unknown  -100
"""
    mock_open_file.return_value.read.return_value = journal_content
    mock_open_file.side_effect = [
        mock_open(read_data=journal_content).return_value,
        mock_open().return_value,
    ]

    journal_splitter.split_journal_by_year(input_file, output_dir)

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    assert mock_open_file.call_count == 2

    write_calls = mock_open_file.return_value.write.mock_calls
    assert len(write_calls) == 1
    assert "expenses:unclassified" in str(write_calls[0])
    assert "assets:checking:mercury5678" in str(write_calls[0])


@patch("os.listdir")
@patch("os.path.join")
@patch("os.path.isdir")
@patch("dewey.core.bookkeeping.journal_splitter.JournalSplitter.split_journal_by_year")
@patch.object(JournalSplitter, "get_config_value", return_value="/tmp/journals")
def test_run(
    mock_get_config_value: MagicMock,
    mock_split_journal_by_year: MagicMock,
    mock_isdir: MagicMock,
    mock_join: MagicMock,
    mock_listdir: MagicMock,
    journal_splitter: JournalSplitter,
) -> None:
    """Test the run method."""
    mock_listdir.return_value = ["test_1234.journal", "test_5678.journal"]
    mock_join.side_effect = lambda a, b: os.path.join(a, b)
    mock_isdir.return_value = True

    journal_splitter.run()

    assert mock_get_config_value.call_count == 1
    assert mock_split_journal_by_year.call_count == 2
    mock_split_journal_by_year.assert_called_with(os.path.join("/tmp/journals", "test_5678.journal"), os.path.join("/tmp/journals", "by_year"))


@patch("os.listdir")
@patch.object(JournalSplitter, "get_config_value", return_value="/tmp/journals")
def test_run_no_journal_files(
    mock_get_config_value: MagicMock,
    mock_listdir: MagicMock,
    journal_splitter: JournalSplitter,
) -> None:
    """Test the run method when there are no journal files."""
    mock_listdir.return_value = []

    journal_splitter.run()

    mock_get_config_value.assert_called_once()
    assert journal_splitter.logger.info.call_count == 0


@patch("os.listdir")
@patch.object(JournalSplitter, "get_config_value", return_value="/tmp/journals")
def test_run_with_dot_file(
    mock_get_config_value: MagicMock,
    mock_listdir: MagicMock,
    journal_splitter: JournalSplitter,
) -> None:
    """Test the run method when there is a dot file in the journal directory."""
    mock_listdir.return_value = [".DS_Store", "test_1234.journal"]

    journal_splitter.run()

    mock_get_config_value.assert_called_once()
    assert journal_splitter.logger.info.call_count == 1


@patch("dewey.core.bookkeeping.journal_splitter.JournalSplitter.execute")
@patch("dewey.core.bookkeeping.journal_splitter.JournalSplitter.__init__", return_value=None)
def test_main(mock_init: MagicMock, mock_execute: MagicMock) -> None:
    """Test the main function."""
    main()
    mock_execute.assert_called_once()
