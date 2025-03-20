"""Tests for dewey.core.bookkeeping.transaction_categorizer."""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch, mock_open

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.transaction_categorizer import JournalCategorizer


class TestJournalCategorizer:
    """Tests for the JournalCategorizer class."""

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_init(self, mock_base_init: MagicMock, journal_categorizer: JournalCategorizer) -> None:
        """Test the __init__ method."""
        assert isinstance(journal_categorizer, JournalCategorizer)
        assert isinstance(journal_categorizer, BaseScript)
        mock_base_init.assert_called_once_with(config_section="bookkeeping")

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_load_classification_rules(
        self, mock_base_init: MagicMock, journal_categorizer: JournalCategorizer, tmp_path: Path
    ) -> None:
        """Test loading classification rules from a JSON file."""
        rules_data = {"patterns": [], "default_category": "Test"}
        rules_file = tmp_path / "rules.json"
        with open(rules_file, "w") as f:
            json.dump(rules_data, f)

        with patch("builtins.open", mock_open(read_data=json.dumps(rules_data))) as mock_file:
            rules = journal_categorizer.load_classification_rules(str(rules_file))
            assert rules == rules_data
            mock_file.assert_called_once_with(str(rules_file))

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_load_classification_rules_file_not_found(
        self, mock_base_init: MagicMock, journal_categorizer: JournalCategorizer
    ) -> None:
        """Test loading classification rules when the file is not found."""
        with pytest.raises(FileNotFoundError):
            journal_categorizer.load_classification_rules("nonexistent_file.json")

    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_load_classification_rules_invalid_json(
        self, mock_base_init: MagicMock, journal_categorizer: JournalCategorizer, tmp_path: Path
    ) -> None:
        """Test loading classification rules with invalid JSON."""
        rules_file = tmp_path / "rules.json"
        with open(rules_file, "w") as f:
            f.write("invalid json")

        with patch("builtins.open", mock_open(read_data="invalid json")):
            with pytest.raises(json.JSONDecodeError):
                journal_categorizer.load_classification_rules(str(rules_file))

    @patch("shutil.copy2")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_create_backup(
        self,
        mock_base_init: MagicMock,
        mock_copy2: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
    ) -> None:
        """Test creating a backup of the journal file."""
        file_path = tmp_path / "journal.json"
        file_path.write_text("test data")

        backup_path = journal_categorizer.create_backup(file_path)
        assert backup_path == str(file_path) + ".bak"
        mock_copy2.assert_called_once_with(file_path, str(file_path) + ".bak")

    @patch("shutil.copy2", side_effect=Exception("Backup failed"))
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_create_backup_failure(
        self,
        mock_base_init: MagicMock,
        mock_copy2: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
    ) -> None:
        """Test handling backup creation failure."""
        file_path = tmp_path / "journal.json"
        file_path.write_text("test data")

        with pytest.raises(Exception, match="Backup failed"):
            journal_categorizer.create_backup(file_path)
        mock_copy2.assert_called_once_with(file_path, str(file_path) + ".bak")

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

    @patch("shutil.copy2")
    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file(
        self,
        mock_base_init: MagicMock,
        mock_create_backup: MagicMock,
        mock_copy2: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test processing a journal file and categorizing transactions."""
        mock_create_backup.return_value = str(tmp_path / "journal.json") + ".bak"
        journal_data = {
            "transactions": [
                {"description": "Starbucks coffee", "amount": 5.0},
                {"description": "Amazon purchase", "amount": 25.0},
                {"description": "Generic transaction", "amount": 10.0},
            ]
        }
        journal_file = tmp_path / "journal.json"
        with open(journal_file, "w") as f:
            json.dump(journal_data, f)

        with patch("builtins.open", mock_open(read_data=json.dumps(journal_data))) as mock_file:
            result = journal_categorizer.process_journal_file(
                str(journal_file), sample_rules
            )
            assert result is True

        with open(journal_file) as f:
            journal = json.load(f)
            assert journal["transactions"][0]["category"] == "Coffee"
            assert journal["transactions"][1]["category"] == "Shopping"
            assert journal["transactions"][2]["category"] == "Uncategorized"

    @patch("shutil.copy2")
    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file_no_modifications(
        self,
        mock_base_init: MagicMock,
        mock_create_backup: MagicMock,
        mock_copy2: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test processing a journal file with no modifications needed."""
        mock_create_backup.return_value = str(tmp_path / "journal.json") + ".bak"
        journal_data = {
            "transactions": [
                {"description": "Starbucks coffee", "amount": 5.0, "category": "Coffee"}
            ]
        }
        journal_file = tmp_path / "journal.json"
        with open(journal_file, "w") as f:
            json.dump(journal_data, f)

        with patch("builtins.open", mock_open(read_data=json.dumps(journal_data))) as mock_file:
            result = journal_categorizer.process_journal_file(str(journal_file), sample_rules)
            assert result is True

        with open(journal_file) as f:
            journal = json.load(f)
            assert journal["transactions"][0]["category"] == "Coffee"

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file_backup_failure(
        self,
        mock_base_init: MagicMock,
        mock_create_backup: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test handling backup creation failure during journal file processing."""
        mock_create_backup.side_effect = Exception("Backup failed")
        journal_file = tmp_path / "journal.json"
        journal_file.write_text("{}")

        with patch("builtins.open", mock_open(read_data="{}")):
            result = journal_categorizer.process_journal_file(
                str(journal_file), sample_rules
            )
            assert result is False

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file_load_failure(
        self,
        mock_base_init: MagicMock,
        mock_create_backup: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test handling journal file loading failure."""
        mock_create_backup.return_value = str(tmp_path / "journal.json") + ".bak"
        journal_file = tmp_path / "journal.json"
        journal_file.write_text("invalid json")

        with patch("builtins.open", mock_open(read_data="invalid json")):
            result = journal_categorizer.process_journal_file(
                str(journal_file), sample_rules
            )
            assert result is False

    @patch("shutil.copy2")
    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_journal_file_update_failure(
        self,
        mock_base_init: MagicMock,
        mock_create_backup: MagicMock,
        mock_copy2: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test handling journal file update failure and restore from backup."""
        mock_create_backup.return_value = str(tmp_path / "journal.json") + ".bak"
        journal_data = {"transactions": []}
        journal_file = tmp_path / "journal.json"
        with open(journal_file, "w") as f:
            json.dump(journal_data, f)

        with patch("builtins.open", side_effect=[
            mock_open(read_data=json.dumps(journal_data)).return_value,  # Initial read
            Exception("Update failed"),  # Simulate write failure
        ]):
            result = journal_categorizer.process_journal_file(
                str(journal_file), sample_rules
            )
            assert result is False
            mock_copy2.assert_called()

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.process_journal_file")
    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_process_by_year_files(
        self,
        mock_base_init: MagicMock,
        mock_isdir: MagicMock,
        mock_listdir: MagicMock,
        mock_process_journal_file: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test processing journal files organized by year."""
        year_dir = tmp_path / "2023"
        year_dir.mkdir()
        journal_file = year_dir / "journal.json"
        journal_file.write_text("{}")

        mock_listdir.return_value = ["2023"]
        mock_isdir.return_value = True
        mock_process_journal_file.return_value = True

        journal_categorizer.process_by_year_files(str(tmp_path), sample_rules)
        mock_process_journal_file.assert_called_once_with(
            str(journal_file), sample_rules
        )

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.load_classification_rules")
    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.process_by_year_files")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_run(
        self,
        mock_base_init: MagicMock,
        mock_process_by_year_files: MagicMock,
        mock_load_classification_rules: MagicMock,
        journal_categorizer: JournalCategorizer,
    ) -> None:
        """Test the run method."""
        mock_load_classification_rules.return_value = {"patterns": [], "default_category": "Test"}
        journal_categorizer.get_config_value = MagicMock(return_value="test_value")

        result = journal_categorizer.run()
        assert result == 0
        mock_process_by_year_files.assert_called_once()

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.load_classification_rules")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_run_load_rules_failure(
        self,
        mock_base_init: MagicMock,
        mock_load_classification_rules: MagicMock,
        journal_categorizer: JournalCategorizer,
    ) -> None:
        """Test handling failure to load classification rules."""
        mock_load_classification_rules.side_effect = Exception("Load failed")
        journal_categorizer.get_config_value = MagicMock(return_value="test_value")

        result = journal_categorizer.run()
        assert result == 1

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.process_by_year_files")
    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.load_classification_rules")
    @patch("dewey.core.bookkeeping.transaction_categorizer.BaseScript.__init__", return_value=None)
    def test_run_process_files_failure(
        self,
        mock_base_init: MagicMock,
        mock_load_classification_rules: MagicMock,
        mock_process_by_year_files: MagicMock,
        journal_categorizer: JournalCategorizer,
    ) -> None:
        """Test handling failure during journal file processing."""
        mock_process_by_year_files.side_effect = Exception("Process failed")
        journal_categorizer.get_config_value = MagicMock(return_value="test_value")
        mock_load_classification_rules.return_value = {"patterns": [], "default_category": "Test"}

        result = journal_categorizer.run()
        assert result == 1
