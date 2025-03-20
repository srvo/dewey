"""Tests for dewey.core.bookkeeping.duplicate_checker."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import hashlib
import os
from typing import Dict, List, Any, Optional

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.duplicate_checker import DuplicateChecker


@pytest.fixture
def mock_base_script() -> MagicMock:
    """Mock BaseScript instance."""
    mock_script = MagicMock(spec=BaseScript)
    mock_script.get_config_value.return_value = "test_value"
    mock_script.logger = MagicMock()
    return mock_script


@pytest.fixture
def mock_duplicate_checker(mock_base_script: MagicMock) -> DuplicateChecker:
    """Create a DuplicateChecker instance with mocked BaseScript."""
    with patch("dewey.core.bookkeeping.duplicate_checker.BaseScript.__init__", return_value=None):
        checker = DuplicateChecker()
        checker.logger = mock_base_script.logger
        checker.get_config_value = mock_base_script.get_config_value
    return checker


@pytest.fixture
def mock_os_walk() -> MagicMock:
    """Mock os.walk."""
    mock_walk = MagicMock()
    return mock_walk


@pytest.fixture
def mock_hashlib() -> MagicMock:
    """Mock hashlib.sha256."""
    mock_hash = MagicMock()
    mock_hash.hexdigest.return_value = "dummy_hash"
    return mock_hash


def test_duplicate_checker_initialization(mock_base_script: MagicMock) -> None:
    """Test that DuplicateChecker initializes correctly."""
    with patch("dewey.core.bookkeeping.duplicate_checker.BaseScript.__init__", return_value=None):
        checker = DuplicateChecker()
        assert checker.config_section == "bookkeeping"


@patch("dewey.core.bookkeeping.duplicate_checker.os.walk")
def test_find_ledger_files_success(mock_os_walk: MagicMock, mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that find_ledger_files finds ledger files and calculates hashes."""
    mock_os_walk.return_value = [
        ("/path/to/ledger", ["subdir"], ["file1.journal", "file2.journal"]),
        ("/path/to/ledger/subdir", [], ["file3.journal"]),
    ]

    with patch("builtins.open", mock_open(read_data="test data")) as mock_file:
        with patch("hashlib.sha256", return_value=MagicMock(hexdigest=lambda: "dummy_hash")):
            hashes = mock_duplicate_checker.find_ledger_files()

            assert "dummy_hash" in hashes
            assert len(hashes["dummy_hash"]) == 3
            assert "/path/to/ledger/file1.journal" in hashes["dummy_hash"]
            assert "/path/to/ledger/file2.journal" in hashes["dummy_hash"]
            assert "/path/to/ledger/subdir/file3.journal" in hashes["dummy_hash"]
            assert mock_file.call_count == 3


@patch("dewey.core.bookkeeping.duplicate_checker.os.walk")
def test_find_ledger_files_error_reading_file(mock_os_walk: MagicMock, mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that find_ledger_files handles errors when reading files."""
    mock_os_walk.return_value = [("/path/to/ledger", [], ["file1.journal"])]

    with patch("builtins.open", side_effect=Exception("Failed to read file")):
        hashes = mock_duplicate_checker.find_ledger_files()

        assert hashes == {}
        mock_duplicate_checker.logger.error.assert_called_once()


@patch("dewey.core.bookkeeping.duplicate_checker.DuplicateChecker.find_ledger_files")
def test_check_duplicates_duplicates_found(mock_find_ledger_files: MagicMock, mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that check_duplicates returns True if duplicate files are found."""
    mock_find_ledger_files.return_value = {"hash1": ["file1", "file2"], "hash2": ["file3"]}

    result = mock_duplicate_checker.check_duplicates()

    assert result is True
    mock_duplicate_checker.logger.warning.assert_called_once()


@patch("dewey.core.bookkeeping.duplicate_checker.DuplicateChecker.find_ledger_files")
def test_check_duplicates_no_duplicates_found(mock_find_ledger_files: MagicMock, mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that check_duplicates returns False if no duplicate files are found."""
    mock_find_ledger_files.return_value = {"hash1": ["file1"], "hash2": ["file3"]}

    result = mock_duplicate_checker.check_duplicates()

    assert result is False
    mock_duplicate_checker.logger.info.assert_called_once()


@patch("dewey.core.bookkeeping.duplicate_checker.DuplicateChecker.check_duplicates")
def test_run_duplicates_found(mock_check_duplicates: MagicMock, mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that run logs an error if duplicate files are found."""
    mock_check_duplicates.return_value = True

    mock_duplicate_checker.run()

    mock_duplicate_checker.logger.error.assert_called_once_with("Duplicate ledger files found.")


@patch("dewey.core.bookkeeping.duplicate_checker.DuplicateChecker.check_duplicates")
def test_run_no_duplicates_found(mock_check_duplicates: MagicMock, mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that run logs an info message if no duplicate files are found."""
    mock_check_duplicates.return_value = False

    mock_duplicate_checker.run()

    mock_duplicate_checker.logger.info.assert_called_once_with("No duplicate ledger files found.")


@patch("dewey.core.bookkeeping.duplicate_checker.DuplicateChecker.run")
def test_main(mock_run: MagicMock) -> None:
    """Test that main creates a DuplicateChecker instance and calls run."""
    with patch("dewey.core.bookkeeping.duplicate_checker.DuplicateChecker") as MockDuplicateChecker:
        from dewey.core.bookkeeping import duplicate_checker
        duplicate_checker.main()
        MockDuplicateChecker.assert_called_once()
        mock_run.assert_called_once()
