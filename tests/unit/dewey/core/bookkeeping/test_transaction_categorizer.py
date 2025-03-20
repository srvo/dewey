import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.bookkeeping.transaction_categorizer import JournalCategorizer
from dewey.core.base_script import BaseScript


@pytest.fixture
def journal_categorizer() -> JournalCategorizer:
    """Fixture to create a JournalCategorizer instance."""
    return JournalCategorizer()


@pytest.fixture
def sample_rules() -> Dict[str, Any]:
    """Fixture to provide sample classification rules."""
    return {
        "patterns": [
            {"regex": "starbucks", "category": "Coffee"}, {"regex": "amazon", "category": "Shopping"}, ], "default_category": "Uncategorized", }


@pytest.fixture
def sample_transaction() -> Dict[str, Any]:
    """Fixture to provide a sample transaction."""
    return {"description": "Starbucks coffee", "amount": 5.0}


@pytest.fixture
def sample_journal_file(tmp_path: Path) -> Path:
    """Fixture to create a sample journal file."""
    journal_data = {
        "transactions": [
            {"description": "Starbucks coffee", "amount": 5.0}, {"description": "Amazon purchase", "amount": 25.0}, {"description": "Generic transaction", "amount": 10.0}, ]
    }
    journal_file = tmp_path / "journal.json"
    with open(journal_file, "w") as f:
        json.dump(journal_data, f)
    return journal_file


class TestJournalCategorizer:
    """Tests for the JournalCategorizer class."""

    def test_init(self, journal_categorizer: JournalCategorizer) -> None:
        """Test the __init__ method."""
        assert isinstance(journal_categorizer, JournalCategorizer)
        assert isinstance(journal_categorizer, BaseScript)

    def test_load_classification_rules(
        self, journal_categorizer: JournalCategorizer, tmp_path: Path
    ) -> None:
        """Test loading classification rules from a JSON file."""
        rules_data=None, "default_category": "Test"}
        rules_file = tmp_path / "rules.json"
        with open(rules_file, "w") as f:
            json.dump(rules_data, f)

        rules = journal_categorizer.load_classification_rules(str(rules_file))
        assert rules == rules_data

    def test_load_classification_rules_file_not_found(
        self, journal_categorizer: JournalCategorizer
    ) -> None:
        """Test loading classification rules when the file is not found."""
        with pytest.raises(FileNotFoundError):
            if tmp_path: Path
    ) -> None:
        """Test loading classification rules from a JSON file."""
        rules_data is None:
                tmp_path: Path
    ) -> None:
        """Test loading classification rules from a JSON file."""
        rules_data = {"patterns": []
            journal_categorizer.load_classification_rules("nonexistent_file.json")

    def test_load_classification_rules_invalid_json(
        self, journal_categorizer: JournalCategorizer, tmp_path: Path
    ) -> None:
        """Test loading classification rules with invalid JSON."""
        rules_file = tmp_path / "rules.json"
        with open(rules_file, "w") as f:
            f.write("invalid json")

        with pytest.raises(json.JSONDecodeError):
            journal_categorizer.load_classification_rules(str(rules_file))

    @patch("shutil.copy2")
    def test_create_backup(
        self,
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
    def test_create_backup_failure(
        self,
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

    def test_classify_transaction(
        self,
        journal_categorizer: JournalCategorizer,
        sample_transaction: Dict[str, Any],
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test classifying a transaction based on rules."""
        category = journal_categorizer.classify_transaction(
            sample_transaction, sample_rules
        )
        assert category == "Coffee"

    def test_classify_transaction_default_category(
        self, journal_categorizer: JournalCategorizer, sample_rules: Dict[str, Any]
    ) -> None:
        """Test classifying a transaction with the default category."""
        transaction = {"description": "Generic transaction", "amount": 10.0}
        category = journal_categorizer.classify_transaction(transaction, sample_rules)
        assert category == "Uncategorized"

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    def test_process_journal_file(
        self,
        mock_create_backup: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_journal_file: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test processing a journal file and categorizing transactions."""
        mock_create_backup.return_value = str(sample_journal_file) + ".bak"

        result = journal_categorizer.process_journal_file(
            str(sample_journal_file), sample_rules
        )
        assert result is True

        with open(sample_journal_file) as f:
            journal = json.load(f)
            assert journal["transactions"][0]["category"] == "Coffee"
            assert journal["transactions"][1]["category"] == "Shopping"
            assert journal["transactions"][2]["category"] == "Uncategorized"

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    def test_process_journal_file_no_modifications(
        self,
        mock_create_backup: MagicMock,
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

        result = journal_categorizer.process_journal_file(str(journal_file), sample_rules)
        assert result is True

        with open(journal_file) as f:
            journal = json.load(f)
            assert journal["transactions"][0]["category"] == "Coffee"

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    def test_process_journal_file_backup_failure(
        self,
        mock_create_backup: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_journal_file: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test handling backup creation failure during journal file processing."""
        mock_create_backup.side_effect = Exception("Backup failed")

        result = journal_categorizer.process_journal_file(
            str(sample_journal_file), sample_rules
        )
        assert result is False

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    def test_process_journal_file_load_failure(
        self,
        mock_create_backup: MagicMock,
        journal_categorizer: JournalCategorizer,
        tmp_path: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test handling journal file loading failure."""
        mock_create_backup.return_value = str(tmp_path / "journal.json") + ".bak"
        journal_file = tmp_path / "journal.json"
        journal_file.write_text("invalid json")

        result = journal_categorizer.process_journal_file(
            str(journal_file), sample_rules
        )
        assert result is False

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.create_backup")
    def test_process_journal_file_update_failure(
        self,
        mock_create_backup: MagicMock,
        journal_categorizer: JournalCategorizer,
        sample_journal_file: Path,
        sample_rules: Dict[str, Any],
    ) -> None:
        """Test handling journal file update failure and restore from backup."""
        mock_create_backup.return_value = str(sample_journal_file) + ".bak"

        with patch("builtins.open", side_effect=[
            open(sample_journal_file, "r"),  # Initial read
            Exception("Update failed"),  # Simulate write failure
        ]):
            result = journal_categorizer.process_journal_file(
                str(sample_journal_file), sample_rules
            )
            assert result is False

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.process_journal_file")
    def test_process_by_year_files(
        self,
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

        journal_categorizer.process_by_year_files(str(tmp_path), sample_rules)
        mock_process_journal_file.assert_called_once_with(
            str(journal_file), sample_rules
        )

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.load_classification_rules")
    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.process_by_year_files")
    def test_run(
        self,
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
    def test_run_load_rules_failure(
        self,
        mock_load_classification_rules: MagicMock,
        journal_categorizer: JournalCategorizer,
    ) -> None:
        """Test handling failure to load classification rules."""
        mock_load_classification_rules.side_effect = Exception("Load failed")
        journal_categorizer.get_config_value = MagicMock(return_value="test_value")

        result = journal_categorizer.run()
        assert result == 1

    @patch("dewey.core.bookkeeping.transaction_categorizer.JournalCategorizer.process_by_year_files")
    def test_run_process_files_failure(
        self,
        mock_process_by_year_files: MagicMock,
        journal_categorizer: JournalCategorizer,
    ) -> None:
        """Test handling failure during journal file processing."""
        mock_process_by_year_files.side_effect = Exception("Process failed")
        journal_categorizer.get_config_value = MagicMock(return_value="test_value")
        journal_categorizer.load_classification_rules = MagicMock(return_value={"patterns": [], "default_category": "Test"})

        result = journal_categorizer.run()
        assert result == 1
