"""Tests for transaction categorizer module."""

import json
import logging
import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from dewey.core.bookkeeping.transaction_categorizer import (
    load_classification_rules,
    create_backup,
    classify_transaction,
    process_journal_file,
    process_by_year_files,
    main,
)

@pytest.fixture
def sample_rules():
    """Sample classification rules for testing."""
    return {
        "patterns": [
            {
                "regex": "walmart|target",
                "category": "expenses:shopping:retail"
            },
            {
                "regex": "starbucks|dunkin",
                "category": "expenses:food:coffee"
            },
            {
                "regex": "uber|lyft",
                "category": "expenses:transport:rideshare"
            }
        ],
        "default_category": "expenses:uncategorized"
    }

@pytest.fixture
def sample_transaction():
    """Sample transaction for testing."""
    return {
        "date": "2024-01-01",
        "description": "WALMART STORE #1234",
        "amount": 50.00,
        "account": "assets:checking:primary"
    }

@pytest.fixture
def sample_journal():
    """Sample journal data for testing."""
    return {
        "transactions": [
            {
                "date": "2024-01-01",
                "description": "WALMART STORE #1234",
                "amount": 50.00,
                "account": "assets:checking:primary"
            },
            {
                "date": "2024-01-02",
                "description": "STARBUCKS #5678",
                "amount": 5.75,
                "account": "assets:checking:primary"
            },
            {
                "date": "2024-01-03",
                "description": "UNKNOWN VENDOR",
                "amount": 25.00,
                "account": "assets:checking:primary"
            }
        ]
    }

class TestTransactionCategorizer:
    """Test cases for transaction categorizer."""

    def test_load_classification_rules_success(self, sample_rules, tmp_path):
        """Test successful loading of classification rules."""
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps(sample_rules))

        loaded_rules = load_classification_rules(str(rules_file))
        assert loaded_rules == sample_rules

    def test_load_classification_rules_file_not_found(self):
        """Test loading classification rules with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_classification_rules("nonexistent.json")

    def test_load_classification_rules_invalid_json(self, tmp_path):
        """Test loading classification rules with invalid JSON."""
        rules_file = tmp_path / "invalid_rules.json"
        rules_file.write_text("invalid json content")

        with pytest.raises(json.JSONDecodeError):
            load_classification_rules(str(rules_file))

    def test_create_backup_success(self, tmp_path):
        """Test successful creation of backup file."""
        source_file = tmp_path / "journal.json"
        source_file.write_text("test content")

        backup_path = create_backup(source_file)
        assert Path(backup_path).exists()
        assert Path(backup_path).read_text() == "test content"

    def test_create_backup_failure(self):
        """Test backup creation failure."""
        with pytest.raises(Exception):
            create_backup(Path("/nonexistent/path/file.json"))

    def test_classify_transaction_match(self, sample_rules, sample_transaction):
        """Test transaction classification with matching pattern."""
        category = classify_transaction(sample_transaction, sample_rules)
        assert category == "expenses:shopping:retail"

    def test_classify_transaction_no_match(self, sample_rules):
        """Test transaction classification with no matching pattern."""
        transaction = {
            "description": "UNKNOWN VENDOR",
            "amount": 25.00
        }
        category = classify_transaction(transaction, sample_rules)
        assert category == "expenses:uncategorized"

    def test_process_journal_file_success(self, sample_rules, sample_journal, tmp_path):
        """Test successful processing of journal file."""
        journal_file = tmp_path / "journal.json"
        journal_file.write_text(json.dumps(sample_journal))

        result = process_journal_file(journal_file, sample_rules)
        assert result is True

        # Verify the transactions were categorized
        updated_journal = json.loads(journal_file.read_text())
        assert updated_journal["transactions"][0]["category"] == "expenses:shopping:retail"
        assert updated_journal["transactions"][1]["category"] == "expenses:food:coffee"
        assert updated_journal["transactions"][2]["category"] == "expenses:uncategorized"

    def test_process_journal_file_backup_failure(self, sample_rules, tmp_path):
        """Test journal processing when backup fails."""
        journal_file = tmp_path / "journal.json"
        
        with patch("dewey.core.bookkeeping.transaction_categorizer.create_backup") as mock_backup:
            mock_backup.side_effect = Exception("Backup failed")
            
            result = process_journal_file(journal_file, sample_rules)
            assert result is False

    def test_process_by_year_files(self, sample_rules, tmp_path):
        """Test processing of journal files by year."""
        # Create year directories with sample files
        for year in ["2023", "2024"]:
            year_dir = tmp_path / year
            year_dir.mkdir()
            journal_file = year_dir / "transactions.json"
            journal_file.write_text(json.dumps({"transactions": []}))

        with patch("dewey.core.bookkeeping.transaction_categorizer.process_journal_file") as mock_process:
            mock_process.return_value = True
            process_by_year_files(tmp_path, sample_rules)
            assert mock_process.call_count == 2

    def test_main_success(self, sample_rules, tmp_path):
        """Test successful execution of main function."""
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps(sample_rules))

        with patch.dict(os.environ, {
            "JOURNAL_BASE_DIR": str(tmp_path),
            "CLASSIFICATION_RULES": str(rules_file)
        }):
            with patch("dewey.core.bookkeeping.transaction_categorizer.process_by_year_files") as mock_process:
                result = main()
                assert result == 0
                mock_process.assert_called_once()

    def test_main_failure(self):
        """Test main function failure."""
        with patch.dict(os.environ, {
            "CLASSIFICATION_RULES": "nonexistent.json"
        }):
            result = main()
            assert result == 1 