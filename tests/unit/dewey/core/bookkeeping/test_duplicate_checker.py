"""Tests for dewey.core.bookkeeping.duplicate_checker."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import hashlib
import os
from typing import Dict, List, Any, Optional

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.duplicate_checker import DuplicateChecker, FileSystemInterface, RealFileSystem, calculate_file_hash


@pytest.fixture
def mock_base_script() -> MagicMock:
    """Mock BaseScript instance."""
    mock_script = MagicMock(spec=BaseScript)
    mock_script.get_config_value.return_value = "test_ledger_dir"
    mock_script.logger = MagicMock()
    return mock_script


@pytest.fixture
def mock_file_system() -> MagicMock:
    """Mock FileSystemInterface."""
    mock_fs = MagicMock(spec=FileSystemInterface)
    return mock_fs


@pytest.fixture
def mock_duplicate_checker(mock_base_script: MagicMock, mock_file_system: MagicMock) -> DuplicateChecker:
    """Create a DuplicateChecker instance with mocked BaseScript and FileSystemInterface."""
    with patch("dewey.core.bookkeeping.duplicate_checker.BaseScript.__init__", return_value=None):
        checker = DuplicateChecker(file_system=mock_file_system)
        checker.logger = mock_base_script.logger
        checker.get_config_value = mock_base_script.get_config_value
    return checker


def test_real_file_system_walk() -> None:
    """Test that RealFileSystem.walk calls os.walk."""
    with patch("os.walk") as mock_os_walk:
        fs = RealFileSystem()
        fs.walk("/test/directory")
        mock_os_walk.assert_called_once_with("/test/directory")


def test_real_file_system_open() -> None:
    """Test that RealFileSystem.open calls open."""
    with patch("builtins.open") as mock_open:
        fs = RealFileSystem()
        fs.open("/test/file.txt", "rb")
        mock_open.assert_called_once_with("/test/file.txt", "rb")


def test_calculate_file_hash() -> None:
    """Test that calculate_file_hash calculates the correct SHA256 hash."""
    file_content = b"test content"
    expected_hash = hashlib.sha256(file_content).hexdigest()
    assert calculate_file_hash(file_content) == expected_hash


def test_duplicate_checker_initialization(mock_base_script: MagicMock, mock_file_system: MagicMock) -> None:
    """Test that DuplicateChecker initializes correctly."""
    with patch("dewey.core.bookkeeping.duplicate_checker.BaseScript.__init__", return_value=None):
        checker = DuplicateChecker(file_system=mock_file_system)
        assert checker.config_section == "bookkeeping"
        assert checker.file_system == mock_file_system
        assert checker.ledger_dir == "test_ledger_dir"


def test_duplicate_checker_initialization_with_ledger_dir(mock_base_script: MagicMock, mock_file_system: MagicMock) -> None:
    """Test that DuplicateChecker initializes correctly with a provided ledger_dir."""
    with patch("dewey.core.bookkeeping.duplicate_checker.BaseScript.__init__", return_value=None):
        checker = DuplicateChecker(file_system=mock_file_system, ledger_dir="custom_ledger_dir")
        assert checker.ledger_dir == "custom_ledger_dir"


def test_duplicate_checker_initialization_real_filesystem() -> None:
    """Test that DuplicateChecker initializes with RealFileSystem by default."""
    with patch("dewey.core.bookkeeping.duplicate_checker.BaseScript.__init__", return_value=None):
        checker = DuplicateChecker()
        assert isinstance(checker.file_system, RealFileSystem)


def test_duplicate_checker_initialization_real_filesystem_ledger_dir() -> None:
    """Test that DuplicateChecker initializes with RealFileSystem by default and ledger_dir from config."""
    with patch("dewey.core.bookkeeping.duplicate_checker.BaseScript.__init__", return_value=None):
        checker = DuplicateChecker()
        assert isinstance(checker.file_system, RealFileSystem)
        checker.get_config_value = MagicMock(return_value="config_ledger_dir")
        assert checker.ledger_dir == checker.get_config_value("ledger_dir", "data/bookkeeping/ledger")


def test_find_ledger_files_success(mock_duplicate_checker: DuplicateChecker, mock_file_system: MagicMock) -> None:
    """Test that find_ledger_files finds ledger files and calculates hashes."""
    mock_file_system.walk.return_value = [
        ("/path/to/ledger", ["subdir"], ["file1.journal", "file2.journal"]),
        ("/path/to/ledger/subdir", [], ["file3.journal"]),
    ]

    mock_file1 = MagicMock()
    mock_file1.read.return_value = b"test data 1"
    mock_file2 = MagicMock()
    mock_file2.read.return_value = b"test data 2"
    mock_file3 = MagicMock()
    mock_file3.read.return_value = b"test data 3"

    mock_file_system.open.side_effect = [mock_file1, mock_file2, mock_file3]

    with patch("dewey.core.bookkeeping.duplicate_checker.calculate_file_hash", side_effect=["hash1", "hash2", "hash3"]):
        hashes = mock_duplicate_checker.find_ledger_files()

        assert "hash1" in hashes
        assert "hash2" in hashes
        assert "hash3" in hashes
        assert len(hashes) == 3
        assert hashes["hash1"] == ["/path/to/ledger/file1.journal"]
        assert hashes["hash2"] == ["/path/to/ledger/file2.journal"]
        assert hashes["hash3"] == ["/path/to/ledger/subdir/file3.journal"]
        assert mock_file_system.open.call_count == 3


def test_find_ledger_files_error_reading_file(mock_duplicate_checker: DuplicateChecker, mock_file_system: MagicMock) -> None:
    """Test that find_ledger_files handles errors when reading files."""
    mock_file_system.walk.return_value = [("/path/to/ledger", [], ["file1.journal"])]
    mock_file_system.open.side_effect = Exception("Failed to read file")

    hashes = mock_duplicate_checker.find_ledger_files()

    assert hashes == {}
    mock_duplicate_checker.logger.error.assert_called_once()


def test_check_duplicates_duplicates_found(mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that check_duplicates returns True if duplicate files are found."""
    mock_duplicate_checker.find_ledger_files.return_value = {"hash1": ["file1", "file2"], "hash2": ["file3"]}

    result = mock_duplicate_checker.check_duplicates()

    assert result is True
    mock_duplicate_checker.logger.warning.assert_called_once()


def test_check_duplicates_no_duplicates_found(mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that check_duplicates returns False if no duplicate files are found."""
    mock_duplicate_checker.find_ledger_files.return_value = {"hash1": ["file1"], "hash2": ["file3"]}

    result = mock_duplicate_checker.check_duplicates()

    assert result is False
    mock_duplicate_checker.logger.info.assert_called_once()


def test_run_duplicates_found(mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that run logs an error if duplicate files are found."""
    mock_duplicate_checker.check_duplicates.return_value = True

    mock_duplicate_checker.run()

    mock_duplicate_checker.logger.error.assert_called_once_with("Duplicate ledger files found.")


def test_run_no_duplicates_found(mock_duplicate_checker: DuplicateChecker) -> None:
    """Test that run logs an info message if no duplicate files are found."""
    mock_duplicate_checker.check_duplicates.return_value = False

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
