"""Test module for transaction_categorizer.py."""

import json
import os
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from shutil import copy2
from typing import Any, Dict, IO, List, Tuple
from unittest.mock import MagicMock, mock_open, patch

import pytest

from dewey.core.bookkeeping.transaction_categorizer import (
    FileSystemInterface,
    JournalCategorizer,
    RealFileSystem,
    main,
)

# Use os.PathLike instead of typing.PathLike
PathLike = os.PathLike


class TestFileSystemInterface:
    """Tests for the FileSystemInterface Protocol implementation."""

    def test_real_file_system_implements_interface(self) -> None:
        """Test that RealFileSystem implements FileSystemInterface."""
        # This test verifies that RealFileSystem has all methods required by FileSystemInterface
        fs = RealFileSystem()
        
        # Test interface methods exist
        assert hasattr(fs, "open")
        assert hasattr(fs, "copy2")
        assert hasattr(fs, "isdir")
        assert hasattr(fs, "listdir")
        assert hasattr(fs, "join")


class MockFileSystem(FileSystemInterface):
    """Mock implementation of FileSystemInterface for testing."""

    def __init__(self, files: Dict[str, bytes] = None):
        """Initialize with optional files dictionary."""
        self.files = files or {}
        self.walk_results: List[Tuple[str, List[str], List[str]]] = []
        self.dirs = set()
        self.copied_files = {}

    def set_walk_results(self, results: List[Tuple[str, List[str], List[str]]]) -> None:
        """Set the results to be returned by the walk method."""
        self.walk_results = results

    def open(self, path: PathLike, mode: str = "r") -> Any:
        """Mock file opening."""
        path_str = str(path)
        if path_str in self.files:
            if "b" in mode:
                return mock_open(read_data=self.files[path_str].encode())(path_str, mode)
            return StringIO(self.files[path_str])
        elif path_str == "classification_rules.json":
            # Mock a default rules file
            default_rules = '{"patterns": [{"regex": "payment", "category": "Income:Payment"}, {"regex": "grocery", "category": "Expenses:Groceries"}], "default_category": "Expenses:Uncategorized"}'
            return StringIO(default_rules)
        else:
            raise FileNotFoundError(f"File not found: {path_str}")
    
    def exists(self, path: PathLike) -> bool:
        """Check if a file exists in the mock file system."""
        path_str = str(path)
        return path_str in self.files or path_str == "classification_rules.json" or path_str in self.dirs

    def copy2(self, src: str, dst: str) -> None:
        """Mock file copy operation."""
        self.copied_files[dst] = self.files.get(src, "")

    def isdir(self, path: str) -> bool:
        """Mock directory check operation."""
        return path in self.dirs

    def listdir(self, path: str) -> list[str]:
        """Mock directory listing operation."""
        return [p.split("/")[-1] for p in self.files.keys() if path in p and path != p]

    def join(self, path1: str, path2: str) -> str:
        """Mock path join operation."""
        return os.path.join(path1, path2)
    
    def walk(self, directory: str) -> list:
        """Mock walk operation."""
        # This will be overridden in specific tests
        return []


@pytest.fixture
def mock_fs() -> MockFileSystem:
    """Fixture providing a mock file system."""
    sample_rules = json.dumps({
        "patterns": [
            {"regex": "payment", "category": "Income:Payment"},
            {"regex": "grocery", "category": "Expenses:Groceries"}
        ],
        "default_category": "Expenses:Uncategorized"
    })
    
    sample_journal = json.dumps({
        "transactions": [
            {"date": "2023-01-01", "description": "Client payment", "amount": 1000},
            {"date": "2023-01-05", "description": "Grocery shopping", "amount": -50},
            {"date": "2023-01-10", "description": "Coffee shop", "amount": -5}
        ]
    })
    
    fs = MockFileSystem({
        "classification_rules.json": sample_rules,
        "journals/2023/jan.json": sample_journal,
        "journals/2023/jan/test.journal": "Sample journal content",
        "journals/2023/feb/test.journal": "Another journal content"
    })
    fs.dirs.add("journals")
    fs.dirs.add("journals/2023")
    fs.dirs.add("journals/2023/jan")
    fs.dirs.add("journals/2023/feb")
    
    return fs


@pytest.fixture
def categorizer(mock_fs: MockFileSystem) -> JournalCategorizer:
    """Fixture providing a JournalCategorizer with mock file system."""
    with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
        categorizer = JournalCategorizer(fs=mock_fs)
        categorizer.config = {"bookkeeping": {}}
        # Add mock logger
        categorizer.logger = MagicMock()
        # Set copy_func to shutil.copy2
        categorizer.copy_func = copy2
        return categorizer


class TestJournalCategorizer:
    """Tests for the JournalCategorizer class."""

    def test_init(self) -> None:
        """Test initialization of JournalCategorizer."""
        # Test with default values
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            categorizer = JournalCategorizer()
            categorizer.config = {"bookkeeping": {}}
            categorizer.logger = MagicMock()
            assert isinstance(categorizer.fs, RealFileSystem)
        
        # Test with mock file system
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            mock_fs = MockFileSystem()
            categorizer = JournalCategorizer(fs=mock_fs)
            categorizer.config = {"bookkeeping": {}}
            categorizer.logger = MagicMock()
            assert categorizer.fs == mock_fs

    def test_load_classification_rules(self, categorizer: JournalCategorizer) -> None:
        """Test loading classification rules."""
        rules = categorizer.load_classification_rules("classification_rules.json")
        
        assert rules is not None
        assert "patterns" in rules
        assert len(rules["patterns"]) == 2
        assert rules["patterns"][0]["regex"] == "payment"
        assert rules["default_category"] == "Expenses:Uncategorized"

    def test_load_classification_rules_file_not_found(self, categorizer: JournalCategorizer) -> None:
        """Test error handling when rules file is not found."""
        # Mock opening a file that doesn't exist
        with patch.object(categorizer.fs, 'open', side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                categorizer.load_classification_rules("nonexistent_file.json")

    @patch("json.load")
    def test_load_classification_rules_invalid_json(self, mock_json_load: MagicMock, categorizer: JournalCategorizer) -> None:
        """Test error handling when rules file contains invalid JSON."""
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with pytest.raises(json.JSONDecodeError):
            categorizer.load_classification_rules("classification_rules.json")

    def test_create_backup(self, categorizer: JournalCategorizer) -> None:
        """Test creating a backup of a journal file."""
        file_path = Path("journals/2023/jan.json")
        
        # Mock the file system to pretend the file exists
        with patch.object(categorizer, 'copy_func') as mock_copy:
            backup_path = categorizer.create_backup(file_path)
            
            assert backup_path == str(file_path) + ".bak"
            mock_copy.assert_called_once_with(str(file_path), backup_path)

    @patch("shutil.copy2")
    def test_create_backup_exception(self, mock_copy2: MagicMock, categorizer: JournalCategorizer) -> None:
        """Test error handling when backup creation fails."""
        mock_copy2.side_effect = Exception("Backup failed")
        categorizer.copy_func = mock_copy2
        
        with pytest.raises(Exception, match="Backup failed"):
            categorizer.create_backup(Path("journals/2023/jan.json"))

    def test_classify_transaction(self, categorizer: JournalCategorizer) -> None:
        """Test transaction classification based on rules."""
        rules = categorizer.load_classification_rules("classification_rules.json")
        
        # Test matching first pattern
        transaction = {"description": "Client payment", "amount": 1000}
        category = categorizer.classify_transaction(transaction, rules)
        assert category == "Income:Payment"
        
        # Test matching second pattern
        transaction = {"description": "Grocery shopping", "amount": -50}
        category = categorizer.classify_transaction(transaction, rules)
        assert category == "Expenses:Groceries"
        
        # Test default category
        transaction = {"description": "Coffee shop", "amount": -5}
        category = categorizer.classify_transaction(transaction, rules)
        assert category == "Expenses:Uncategorized"

    @patch("json.load")
    @patch("json.dump")
    def test_process_journal_file(self, mock_json_dump: MagicMock, mock_json_load: MagicMock, categorizer: JournalCategorizer) -> None:
        """Test processing of a journal file."""
        # Setup mock data
        journal_data = {
            "transactions": [
                {"date": "2023-01-01", "description": "Client payment", "amount": 1000},
                {"date": "2023-01-05", "description": "Grocery shopping", "amount": -50},
                {"date": "2023-01-10", "description": "Coffee shop", "amount": -5}
            ]
        }
        mock_json_load.return_value = journal_data
        
        # Setup classification rules
        rules = {
            "patterns": [
                {"regex": "payment", "category": "Income:Payment"},
                {"regex": "grocery", "category": "Expenses:Groceries"},
                {"regex": "coffee", "category": "Expenses:Food:Coffee"}
            ],
            "default_category": "Expenses:Uncategorized"
        }
    
        # Mock the file read/write operations
        with patch.object(categorizer, 'create_backup', return_value="journals/2023/jan.json.bak"):
            result = categorizer.process_journal_file("journals/2023/jan.json", rules)
            
            assert result is True
            mock_json_dump.assert_called_once()
            
            # Check that categories were added
            call_args = mock_json_dump.call_args[0]
            modified_journal = call_args[0]
            
            assert modified_journal["transactions"][0]["category"] == "Income:Payment"
            assert modified_journal["transactions"][1]["category"] == "Expenses:Groceries"
            assert modified_journal["transactions"][2]["category"] == "Expenses:Food:Coffee"

    def test_process_journal_file_backup_fails(self, categorizer: JournalCategorizer) -> None:
        """Test error handling when journal file backup fails."""
        with patch.object(categorizer, 'create_backup', side_effect=Exception("Backup failed")):
            rules = categorizer.load_classification_rules("classification_rules.json")
            result = categorizer.process_journal_file("journals/2023/jan.json", rules)
        
        assert result is False

    def test_process_journal_file_load_fails(self, categorizer: JournalCategorizer) -> None:
        """Test error handling when journal file loading fails."""
        # Setup classification rules
        rules = {
            "patterns": [
                {"regex": "payment", "category": "Income:Payment"}
            ],
            "default_category": "Expenses:Uncategorized"
        }
        
        # Mock json.load to raise an exception
        with patch.object(categorizer, 'create_backup', return_value="journals/2023/jan.json.bak"):
            with patch("builtins.open", MagicMock()):
                with patch("json.load", side_effect=Exception("Load failed")):
                    result = categorizer.process_journal_file("journals/2023/jan.json", rules)
                    assert result is False

    def test_process_by_year_files(self, categorizer: JournalCategorizer, mock_fs: MockFileSystem) -> None:
        """Test processing journal files grouped by year."""
        # Create mock files for different years: 2022/file.journal and 2023/file.journal
        mock_fs.files = {
            "data/bookkeeping/ledger/2022/file.json": b'{"transactions": [{"description": "payment", "amount": 100}]}',
            "data/bookkeeping/ledger/2023/file.json": b'{"transactions": [{"description": "grocery", "amount": -50}]}',
        }
        
        # Add dirs to mock_fs
        mock_fs.dirs.add("data/bookkeeping/ledger/2022")
        mock_fs.dirs.add("data/bookkeeping/ledger/2023")
        
        # Mock listdir method
        def mock_listdir(path):
            if path == "data/bookkeeping/ledger":
                return ["2022", "2023"]
            elif path == "data/bookkeeping/ledger/2022":
                return ["file.json"]
            elif path == "data/bookkeeping/ledger/2023":
                return ["file.json"]
            return []
        
        # Mock isdir method
        def mock_isdir(path):
            return path in mock_fs.dirs
        
        # Mock join method
        def mock_join(path1, path2):
            return os.path.join(path1, path2)
        
        # Set up the mock methods
        mock_fs.listdir = mock_listdir
        mock_fs.isdir = mock_isdir
        mock_fs.join = mock_join
        
        # Create classification rules
        rules = {
            "patterns": [
                {"regex": "payment", "category": "Income:Payment"},
                {"regex": "grocery", "category": "Expenses:Groceries"}
            ],
            "default_category": "Expenses:Uncategorized"
        }
        
        # Patch the process_journal_file method to verify it's called
        with patch.object(categorizer, 'process_journal_file') as mock_process:
            # Make the mock return True to indicate success
            mock_process.return_value = True
            
            # Call the function being tested
            categorizer.process_by_year_files("data/bookkeeping/ledger", rules)
            
            # Should be called once for each year's file
            assert mock_process.call_count == 2
            mock_process.assert_any_call("data/bookkeeping/ledger/2022/file.json", rules)
            mock_process.assert_any_call("data/bookkeeping/ledger/2023/file.json", rules)

    @patch("sys.exit")
    def test_run_success(self, mock_exit: MagicMock, categorizer: JournalCategorizer) -> None:
        """Test successful execution of run method."""
        with patch.object(categorizer, 'load_classification_rules') as mock_load:
            with patch.object(categorizer, 'process_by_year_files') as mock_process:
                # Configure mocks
                mock_load.return_value = {"patterns": []}
                
                # Execute run
                result = categorizer.run()
                
                # Check that methods were called with correct parameters
                mock_load.assert_called_once()
                mock_process.assert_called_once()
                assert result == 0

    @patch("sys.exit")
    def test_run_failure(self, mock_exit: MagicMock, categorizer: JournalCategorizer) -> None:
        """Test error handling during run method execution."""
        with patch.object(categorizer, 'load_classification_rules', side_effect=Exception("Failed to load rules")):
            result = categorizer.run()
            assert result == 1

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer")
    def test_main(self, mock_categorizer_class: MagicMock) -> None:
        """Test the main function."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = 0
        mock_categorizer_class.return_value = mock_instance
        
        result = main()
        
        mock_categorizer_class.assert_called_once()
        mock_instance.run.assert_called_once()
        assert result == 0 