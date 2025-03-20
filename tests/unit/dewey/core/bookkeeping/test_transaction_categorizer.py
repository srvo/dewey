"""Tests for dewey.core.bookkeeping.transaction_categorizer."""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch, mock_open

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.transaction_categorizer import JournalCategorizer, FileSystemInterface, RealFileSystem


class TestRealFileSystem:
    """Tests for the RealFileSystem class."""

    def test_open(self, tmp_path: Path) -> None:
        """Test the open method."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("test data")
        with RealFileSystem().open(str(file_path)) as f:
            assert f.read() == "test data"

    def test_copy2(self, tmp_path: Path) -> None:
        """Test the copy2 method."""
        src_file = tmp_path / "src.txt"
        dst_file = tmp_path / "dst.txt"
        src_file.write_text("test data")
        RealFileSystem().copy2(str(src_file), str(dst_file))
        assert dst_file.read_text() == "test data"

    def test_isdir(self, tmp_path: Path) -> None:
        """Test the isdir method."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        assert RealFileSystem().isdir(str(dir_path)) is True
        assert RealFileSystem().isdir(str(tmp_path / "nonexistent_dir")) is False

    def test_listdir(self, tmp_path: Path) -> None:
        """Test the listdir method."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("test")
        file2.write_text("test")
        contents = RealFileSystem().listdir(str(tmp_path))
        assert "file1.txt" in contents
        assert "file2.txt" in contents

    def test_join(self) -> None:
        """Test the join method."""
        assert RealFileSystem().join("path1", "path2") == "path1/path2"


class TestJournalCategorizer:
    """Tests for the JournalCategorizer class."""

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_init(self, mock_base_init: MagicMock, journal_categorizer: JournalCategorizer, mock_fs: MagicMock) -> None:
        """Test the __init__ method."""
        assert isinstance(journal_categorizer, JournalCategorizer)
        assert isinstance(journal_categorizer, BaseScript)
        mock_base_init.assert_called_once_with(config_section="bookkeeping")
        assert journal_categorizer.fs == mock_fs

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_load_classification_rules(
        self, mock_base_init: MagicMock, journal_categorizer: JournalCategorizer, mock_fs: MagicMock
    ) -> None:
        """Test loading classification rules from a JSON file."""
        rules_data = {"patterns": [], "default_category": "Test"}
        mock_fs.open.return_value = mock_open(read_data=json.dumps(rules_data)).return_value

        rules = journal_categorizer.load_classification_rules("rules.json")
        assert rules == rules_data
        mock_fs.open.assert_called_once_with("rules.json")

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_load_classification_rules_file_not_found(
        self, mock_base_init: MagicMock, journal_categorizer: JournalCategorizer, mock_fs: MagicMock
    ) -> None:
        """Test loading classification rules when the file is not found."""
        mock_fs.open.side_effect = FileNotFoundError
        with pytest.raises(FileNotFoundError):
            journal_categorizer.load_classification_rules("nonexistent_file.json")
        mock_fs.open.assert_called_once_with("nonexistent_file.json")

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_load_classification_rules_invalid_json(
        self, mock_base_init: MagicMock, journal_categorizer: JournalCategorizer, mock_fs: MagicMock
    ) -> None:
        """Test loading classification rules with invalid JSON."""
        mock_fs.open.side_effect = json.JSONDecodeError("", "", 0)
        with pytest.raises(json.JSONDecodeError):
            journal_categorizer.load_classification_rules("invalid_file.json")
        mock_fs.open.assert_called_once_with("invalid_file.json")

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_create_backup(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
        mock_fs: MagicMock
    ) -> None:
        """Test creating a backup of the journal file."""
        file_path = tmp_path / "journal.json"
        file_path.write_text("test data")
        backup_path_str = str(file_path) + ".bak"

        backup_path = journal_categorizer.create_backup(file_path)

        assert backup_path == backup_path_str
        journal_categorizer.copy_func.assert_called_once_with(str(file_path), backup_path_str)

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_create_backup_failure(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
    ) -> None:
        """Test handling backup creation failure."""
        file_path = tmp_path / "journal.json"
        file_path.write_text("test data")
        journal_categorizer.copy_func = MagicMock(side_effect=Exception("Backup failed"))

        with pytest.raises(Exception, match="Backup failed"):
            journal_categorizer.create_backup(file_path)
        journal_categorizer.copy_func.assert_called_once()

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_classify_transaction(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_transaction: Dict[str, Any],
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test classifying a transaction based on rules."""
        category = journal_categorizer.classify_transaction(
            sample_transaction, sample_rules
        )
        assert category == "Coffee"

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_classify_transaction_default_category(
        self, mock_base_init: MagicMock, journal_categorizer: JournalCategorizer, sample_rules: Dict[str, Any]
    ) -> None:
        """Test classifying a transaction with the default category."""
        transaction = {"description": "Generic transaction", "amount": 10.0}
        category = journal_categorizer.classify_transaction(transaction, sample_rules)
        assert category == "Uncategorized"

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_rules: Dict[str, Any],
        mock_fs: MagicMock
    ) -> None:
        """Test processing a journal file and categorizing transactions."""
        journal_data = {
            "transactions": [
                {"description": "Starbucks coffee", "amount": 5.0},
                {"description": "Amazon purchase", "amount": 25.0},
                {"description": "Generic transaction", "amount": 10.0},
            ]
        }
        mock_fs.open.return_value = mock_open(read_data=json.dumps(journal_data)).return_value
        mock_fs.copy2.return_value = None
        journal_categorizer.copy_func = mock_fs.copy2

        result = journal_categorizer.process_journal_file(
            "journal.json", sample_rules
        )
        assert result is True

        mock_fs.open.assert_called()
        journal_categorizer.copy_func.assert_called_once()
        calls = mock_fs.open.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "journal.json"
        assert calls[1][0][0] == "journal.json"
        assert calls[1][1] == {'mode': 'w'}

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file_no_modifications(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_rules: Dict[str, Any],
        mock_fs: MagicMock
    ) -> None:
        """Test processing a journal file with no modifications needed."""
        journal_data = {
            "transactions": [
                {"description": "Starbucks coffee", "amount": 5.0, "category": "Coffee"}
            ]
        }
        mock_fs.open.return_value = mock_open(read_data=json.dumps(journal_data)).return_value
        result = journal_categorizer.process_journal_file("journal.json", sample_rules)
        assert result is True
        mock_fs.open.assert_called_once()

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file_backup_failure(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_rules: Dict[str, Any],
        mock_fs: MagicMock
    ) -> None:
        """Test handling backup creation failure during journal file processing."""
        mock_fs.copy2.side_effect = Exception("Backup failed")
        journal_categorizer.copy_func = mock_fs.copy2

        mock_fs.open.return_value = mock_open(read_data="{}").return_value
        result = journal_categorizer.process_journal_file(
            "journal.json", sample_rules
        )
        assert result is False
        journal_categorizer.copy_func.assert_called_once()

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file_load_failure(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_rules: Dict[str, Any],
        mock_fs: MagicMock
    ) -> None:
        """Test handling journal file loading failure."""
        mock_fs.open.side_effect = Exception("Load failed")

        result = journal_categorizer.process_journal_file(
            "journal.json", sample_rules
        )
        assert result is False
        mock_fs.open.assert_called_once()

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file_update_failure(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_rules: Dict[str, Any],
        mock_fs: MagicMock
    ) -> None:
        """Test handling journal file update failure and restore from backup."""
        journal_data = {"transactions": []}
        mock_fs.open.side_effect = [
            mock_open(read_data=json.dumps(journal_data)).return_value,
            Exception("Update failed"),
        ]
        mock_fs.copy2.return_value = None
        journal_categorizer.copy_func = mock_fs.copy2

        result = journal_categorizer.process_journal_file(
            "journal.json", sample_rules
        )
        assert result is False
        assert journal_categorizer.copy_func.call_count == 1
        assert mock_fs.open.call_count == 2

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_by_year_files(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_rules: Dict[str, Any],
        mock_fs: MagicMock
    ) -> None:
        """Test processing journal files organized by year."""
        mock_fs.listdir.return_value = ["2023"]
        mock_fs.isdir.return_value = True
        mock_fs.join.side_effect = lambda x, y: f"{x}/{y}"
        mock_fs.open.return_value = mock_open(read_data="{}").return_value

        journal_categorizer.process_journal_file = MagicMock(return_value=True)

        journal_categorizer.process_by_year_files("/base_dir", sample_rules)

        mock_fs.listdir.assert_called_once_with("/base_dir")
        mock_fs.isdir.assert_called_once_with("/base_dir/2023")
        journal_categorizer.process_journal_file.assert_called_once_with(
            "/base_dir/2023/None", sample_rules
        )

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_run(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        mock_fs: MagicMock
    ) -> None:
        """Test the run method."""
        journal_categorizer.load_classification_rules = MagicMock(return_value={"patterns": [], "default_category": "Test"})
        journal_categorizer.get_config_value = MagicMock(return_value="test_value")
        journal_categorizer.process_by_year_files = MagicMock()

        result = journal_categorizer.run()
        assert result == 0
        journal_categorizer.process_by_year_files.assert_called_once()

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_run_load_rules_failure(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        mock_fs: MagicMock
    ) -> None:
        """Test handling failure to load classification rules."""
        journal_categorizer.load_classification_rules = MagicMock(side_effect=Exception("Load failed"))
        journal_categorizer.get_config_value = MagicMock(return_value="test_value")

        result = journal_categorizer.run()
        assert result == 1

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_run_process_files_failure(
        self,
        mock_base_init: MagicMock,
        journal_categorizer: JournalCategorizer,
        mock_fs: MagicMock
    ) -> None:
        """Test handling failure during journal file processing."""
        journal_categorizer.process_by_year_files = MagicMock(side_effect=Exception("Process failed"))
        journal_categorizer.get_config_value = MagicMock(return_value="test_value")
        journal_categorizer.load_classification_rules = MagicMock(return_value={"patterns": [], "default_category": "Test"})

        result = journal_categorizer.run()
        assert result == 1
