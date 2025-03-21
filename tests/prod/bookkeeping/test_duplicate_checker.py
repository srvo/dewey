"""Test module for duplicate_checker.py."""

import hashlib
import os
from typing import Dict, List, Tuple, Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from dewey.core.bookkeeping.duplicate_checker import (
    DuplicateChecker,
    FileSystemInterface,
    RealFileSystem,
    calculate_file_hash,
    main,
)


class MockFileSystem(FileSystemInterface):
    """Mock implementation of FileSystemInterface for testing."""

    def __init__(self, files: Dict[str, bytes] = None):
        """Initialize with optional files dictionary."""
        self.files = files or {}
        self.walk_results: List[Tuple[str, List[str], List[str]]] = []
        self.dirs = set()

    def set_walk_results(self, results: List[Tuple[str, List[str], List[str]]]) -> None:
        """Set the results to be returned by the walk method."""
        self.walk_results = results

    def walk(self, directory: str) -> object:
        """Mock walk method returning predefined results."""
        return self.walk_results

    def exists(self, path: str) -> bool:
        """Check if path exists in mock filesystem."""
        return path in self.files or path in self.dirs or path == "classification_rules.json"

    def open(self, path: str, mode: str = "r") -> object:
        """Mock open method returning file contents from dictionary."""
        if path not in self.files and "b" in mode:
            m = mock_open()
            handle = m(path, mode)
            handle.read.return_value = b""
            return handle

        if "b" in mode:
            m = mock_open()
            handle = m(path, mode)
            handle.read.return_value = self.files.get(path, b"")
            return handle
        else:
            return mock_open(read_data=self.files.get(path, b"").decode())(path, mode)


@pytest.fixture
def mock_fs() -> MockFileSystem:
    """Fixture providing a mock file system with sample files."""
    # Create different content for each file to get correct hash counts
    duplicate_content = b"This is a duplicate journal entry"
    unique_content1 = b"This is a unique journal entry 1"
    unique_content2 = b"This is a unique journal entry 2"
    
    mock_fs = MockFileSystem({
        "data/bookkeeping/ledger/file1.journal": duplicate_content,
        "data/bookkeeping/ledger/file2.journal": duplicate_content,
        "data/bookkeeping/ledger/unique1.journal": unique_content1,
        "data/bookkeeping/ledger/unique2.journal": unique_content2,
    })
    
    # Set up the walk results to include these files
    mock_fs.set_walk_results([
        ("data/bookkeeping/ledger", [], ["file1.journal", "file2.journal", "unique1.journal", "unique2.journal"])
    ])
    
    return mock_fs


@pytest.fixture
def checker(mock_fs: MockFileSystem) -> DuplicateChecker:
    """Fixture providing a DuplicateChecker with mock file system."""
    # First, patch the BaseScript.__init__ method so we can control it
    with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
        # Create the checker with our mock filesystem and a specific ledger_dir
        with patch("dewey.core.bookkeeping.duplicate_checker.DuplicateChecker.get_config_value", return_value="data/bookkeeping/ledger"):
            checker = DuplicateChecker(file_system=mock_fs, ledger_dir="data/bookkeeping/ledger")
            # Now set required attributes that would normally be set by BaseScript.__init__
            checker.logger = MagicMock()
            checker.config = {"bookkeeping": {"ledger_dir": "data/bookkeeping/ledger"}}
            return checker


class TestFileSystemInterface:
    """Tests for the FileSystemInterface Protocol implementation."""

    def test_real_file_system_implements_interface(self) -> None:
        """Test that RealFileSystem implements FileSystemInterface."""
        fs = RealFileSystem()
        
        # Test interface methods exist
        assert hasattr(fs, "walk")
        assert hasattr(fs, "open")


class TestCalculateFileHash:
    """Tests for the calculate_file_hash function."""

    def test_calculate_file_hash(self) -> None:
        """Test hash calculation."""
        test_content = b"test content"
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        actual_hash = calculate_file_hash(test_content)
        
        assert actual_hash == expected_hash


class TestDuplicateChecker:
    """Test cases for DuplicateChecker class."""

    @pytest.fixture
    def mock_fs(self) -> MockFileSystem:
        """Fixture to provide a mock file system with test data."""
        # Create different content for files to ensure correct hashing
        duplicate_content = b"This is a duplicate file"
        unique_content1 = b"This is unique file 1"
        unique_content2 = b"This is unique file 2"
        
        fs = MockFileSystem({
            "data/bookkeeping/ledger/file1.journal": duplicate_content,
            "data/bookkeeping/ledger/file2.journal": duplicate_content,
            "data/bookkeeping/ledger/unique1.journal": unique_content1,
            "data/bookkeeping/ledger/unique2.journal": unique_content2,
        })
        
        # Setup walk method to return our test files
        def custom_walk(directory):
            return [("data/bookkeeping/ledger", [], ["file1.journal", "file2.journal", "unique1.journal", "unique2.journal"])]
        
        fs.walk = custom_walk
        return fs

    @pytest.fixture
    def checker(self, mock_fs: MockFileSystem) -> DuplicateChecker:
        """Fixture to provide a DuplicateChecker instance."""
        # First, patch the BaseScript.__init__ method so we can control it
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            # Patch get_config_value to return our desired value
            with patch("dewey.core.base_script.BaseScript.get_config_value", return_value="data/bookkeeping/ledger"):
                # Create the checker with our mock filesystem
                checker = DuplicateChecker(file_system=mock_fs)
                # Now set required attributes that would normally be set by BaseScript.__init__
                checker.logger = MagicMock()
                checker.config = {"bookkeeping": {"ledger_dir": "data/bookkeeping/ledger"}}
                return checker

    def test_init_with_default_values(self) -> None:
        """Test initialization with default values."""
        # First, patch the BaseScript.__init__ method
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            # Then patch the get_config_value method
            with patch("dewey.core.base_script.BaseScript.get_config_value", return_value="data/bookkeeping/ledger"):
                # Create the checker with default values
                checker = DuplicateChecker()
                # Set required attributes that would normally be set by BaseScript.__init__
                checker.logger = MagicMock()
                checker.config = {"bookkeeping": {"ledger_dir": "data/bookkeeping/ledger"}}
                
                # Test default values
                assert checker.ledger_dir == "data/bookkeeping/ledger"
                assert isinstance(checker.file_system, RealFileSystem)

    def test_init_with_custom_values(self) -> None:
        """Test initialization with custom values."""
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            mock_fs = MockFileSystem()
            custom_dir = "custom/ledger/dir"
            
            # Create with custom values
            checker = DuplicateChecker(file_system=mock_fs, ledger_dir=custom_dir)
            # Set required attributes that would normally be set by BaseScript.__init__
            checker.config = {"bookkeeping": {"ledger_dir": "data/bookkeeping/ledger"}}
            
            assert checker.file_system == mock_fs
            assert checker.ledger_dir == custom_dir

    def test_find_ledger_files(self, checker: DuplicateChecker) -> None:
        """Test finding ledger files."""
        hashes = checker.find_ledger_files()
        
        # There should be 3 unique hashes (2 files have the same content)
        assert len(hashes) == 3
        
        # Check that each hash maps to the correct files
        for file_hash, file_paths in hashes.items():
            if len(file_paths) == 2:
                # These are the duplicate files
                assert "file1.journal" in file_paths[0] or "file1.journal" in file_paths[1]
                assert "file2.journal" in file_paths[0] or "file2.journal" in file_paths[1]
            else:
                # This is a unique file
                assert len(file_paths) == 1
                assert "unique1.journal" in file_paths[0] or "unique2.journal" in file_paths[0]

    def test_find_ledger_files_error_handling(self, checker: DuplicateChecker) -> None:
        """Test error handling in find_ledger_files."""
        # Set up the file_system to raise an exception when reading one file
        def mock_open_with_error(path, mode):
            if "file1.journal" in path:
                raise IOError("Simulated file error")
            return mock_open(read_data=b"content")(path, mode)
        
        with patch.object(checker.file_system, 'open', side_effect=mock_open_with_error):
            hashes = checker.find_ledger_files()
            
            # Should still process the other files
            assert len(hashes) > 0
            
            # Should log the error
            checker.logger.error.assert_called_once()

    def test_check_duplicates_with_duplicates(self, checker: DuplicateChecker) -> None:
        """Test check_duplicates when duplicates are found."""
        result = checker.check_duplicates()
        
        assert result is True
        checker.logger.warning.assert_called_once()

    def test_check_duplicates_without_duplicates(self, checker: DuplicateChecker) -> None:
        """Test check_duplicates when no duplicates are found."""
        # Mock find_ledger_files to return no duplicates
        with patch.object(checker, 'find_ledger_files') as mock_find:
            mock_find.return_value = {
                "hash1": ["file1.journal"],
                "hash2": ["file2.journal"],
            }
            
            result = checker.check_duplicates()
            
            assert result is False
            checker.logger.info.assert_called_once_with("No duplicate ledger files found.")

    def test_run_with_duplicates(self, checker: DuplicateChecker) -> None:
        """Test run method when duplicates are found."""
        with patch.object(checker, 'check_duplicates', return_value=True):
            checker.run()
            
            checker.logger.error.assert_called_once_with("Duplicate ledger files found.")

    def test_run_without_duplicates(self, checker: DuplicateChecker) -> None:
        """Test run method when no duplicates are found."""
        with patch.object(checker, 'check_duplicates', return_value=False):
            checker.run()
            
            checker.logger.info.assert_called_once_with("No duplicate ledger files found.")

    @patch("dewey.core.bookkeeping.duplicate_checker.DuplicateChecker")
    def test_main(self, mock_checker_class: MagicMock) -> None:
        """Test the main function."""
        mock_instance = MagicMock()
        mock_checker_class.return_value = mock_instance
        
        main()
        
        mock_checker_class.assert_called_once()
        mock_instance.run.assert_called_once() 