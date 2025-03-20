import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from dewey.core.bookkeeping.journal_writer import JournalWriteError, JournalWriter
from dewey.core.base_script import BaseScript


class TestJournalWriter:
    """Tests for the JournalWriter class."""

    @pytest.fixture
    def journal_writer(self, tmp_path: Path) -> JournalWriter:
        """Fixture for creating a JournalWriter instance."""
        return JournalWriter(output_dir=tmp_path)

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture for mocking BaseScript."""
        with patch("dewey.core.bookkeeping.journal_writer.BaseScript", autospec=True) as MockBaseScript:
            yield MockBaseScript

    def test_init(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test JournalWriter initialization."""
        journal_writer = JournalWriter(output_dir=tmp_path)
        assert journal_writer.output_dir == tmp_path
        assert journal_writer.output_dir.exists()
        assert journal_writer.processed_hashes_file == tmp_path / ".processed_hashes"
        assert isinstance(journal_writer.seen_hashes, set)
        assert isinstance(journal_writer.audit_log, list)
        mock_base_script.assert_called_once_with(config_section="bookkeeping")

    def test_run(self, journal_writer: JournalWriter) -> None:
        """Test the run method (currently a placeholder)."""
        journal_writer.logger = MagicMock()
        journal_writer.run()
        journal_writer.logger.info.assert_called_once_with("JournalWriter run method called.")

    def test_load_processed_hashes_success(self, journal_writer: JournalWriter, tmp_path: Path) -> None:
        """Test loading processed hashes from file successfully."""
        processed_hashes = {"hash1", "hash2", "hash3"}
        (journal_writer.processed_hashes_file).write_text("\n".join(processed_hashes))
        loaded_hashes = journal_writer._load_processed_hashes()
        assert loaded_hashes == processed_hashes

    def test_load_processed_hashes_file_not_exists(self, journal_writer: JournalWriter) -> None:
        """Test loading processed hashes when the file does not exist."""
        loaded_hashes = journal_writer._load_processed_hashes()
        assert loaded_hashes == set()

    def test_load_processed_hashes_failure(self, journal_writer: JournalWriter) -> None:
        """Test loading processed hashes when an exception occurs."""
        journal_writer.processed_hashes_file = MagicMock(side_effect=Exception("Test Exception"))
        journal_writer.logger = MagicMock()
        loaded_hashes = journal_writer._load_processed_hashes()
        assert loaded_hashes == set()
        journal_writer.logger.exception.assert_called_once()

    def test_save_processed_hashes_success(self, journal_writer: JournalWriter, tmp_path: Path) -> None:
        """Test saving processed hashes successfully."""
        seen_hashes = {"hash1", "hash2", "hash3"}
        journal_writer._save_processed_hashes(seen_hashes)
        saved_hashes = set((journal_writer.processed_hashes_file).read_text().splitlines())
        assert saved_hashes == seen_hashes

    def test_save_processed_hashes_failure(self, journal_writer: JournalWriter) -> None:
        """Test saving processed hashes when an exception occurs."""
        journal_writer.processed_hashes_file = MagicMock(side_effect=Exception("Test Exception"))
        journal_writer.logger = MagicMock()
        seen_hashes = {"hash1", "hash2", "hash3"}
        journal_writer._save_processed_hashes(seen_hashes)
        journal_writer.logger.exception.assert_called_once()

    def test_write_file_with_backup_new_file(self, journal_writer: JournalWriter, tmp_path: Path) -> None:
        """Test writing to a new file with backup."""
        filename = tmp_path / "test.journal"
        entries = ["entry1", "entry2"]
        journal_writer._write_file_with_backup(filename, entries)
        assert filename.exists()
        assert filename.read_text() == "entry1\nentry2\n\n"

    def test_write_file_with_backup_existing_file(self, journal_writer: JournalWriter, tmp_path: Path) -> None:
        """Test writing to an existing file with backup."""
        filename = tmp_path / "test.journal"
        filename.write_text("initial content\n")
        entries = ["entry1", "entry2"]
        journal_writer._write_file_with_backup(filename, entries)
        assert filename.exists()
        assert "initial content" in filename.read_text()
        assert "entry1" in filename.read_text()
        assert "entry2" in filename.read_text()
        assert len(list(tmp_path.glob("test_*"))) == 1

    def test_write_file_with_backup_failure(self, journal_writer: JournalWriter) -> None:
        """Test writing to a file with backup when an exception occurs."""
        journal_writer.logger = MagicMock()
        filename = MagicMock(side_effect=Exception("Test Exception"))
        entries = ["entry1", "entry2"]
        journal_writer._write_file_with_backup(filename, entries)
        journal_writer.logger.exception.assert_called_once()

    def test_group_entries_by_account_and_year(self, journal_writer: JournalWriter) -> None:
        """Test grouping entries by account ID and year."""
        entries = {"2023": ["entry1", "entry2"], "2024": ["entry3"]}
        journal_writer.get_config_value = MagicMock(return_value="1234")
        grouped_entries = journal_writer._group_entries_by_account_and_year(entries)
        assert grouped_entries == {("1234", "2023"): ["entry1", "entry2"], ("1234", "2024"): ["entry3"]}
        journal_writer.get_config_value.assert_called_with("default_account_id", "8542")

    def test_write_entries(self, journal_writer: JournalWriter, tmp_path: Path) -> None:
        """Test writing journal entries to appropriate files."""
        entries = {"2023": ["entry1", "entry2"], "2024": ["entry3"]}
        journal_writer._group_entries_by_account_and_year = MagicMock(
            return_value={("1234", "2023"): ["entry1", "entry2"], ("1234", "2024"): ["entry3"]},
        )
        journal_writer._write_file_with_backup = MagicMock()
        journal_writer._save_processed_hashes = MagicMock()
        journal_writer.logger = MagicMock()

        journal_writer.write_entries(entries)

        journal_writer._group_entries_by_account_and_year.assert_called_once_with(entries)
        journal_writer._write_file_with_backup.assert_any_call(tmp_path / "1234_2023.journal", ["entry1", "entry2"])
        journal_writer._write_file_with_backup.assert_any_call(tmp_path / "1234_2024.journal", ["entry3"])
        journal_writer._save_processed_hashes.assert_called_once_with(journal_writer.seen_hashes)
        journal_writer.logger.info.assert_called_once_with("Writing 3 journal entries")

    def test_log_classification_decision(self, journal_writer: JournalWriter) -> None:
        """Test logging a classification decision."""
        tx_hash = "tx123"
        pattern = "pattern1"
        category = "category1"
        journal_writer.log_classification_decision(tx_hash, pattern, category)
        assert len(journal_writer.audit_log) == 1
        log_entry = journal_writer.audit_log[0]
        assert log_entry["tx_hash"] == tx_hash
        assert log_entry["pattern"] == pattern
        assert log_entry["category"] == category
        assert "timestamp" in log_entry

    def test_get_classification_report(self, journal_writer: JournalWriter) -> None:
        """Test generating a classification report."""
        journal_writer.audit_log = [
            {"tx_hash": "tx1", "pattern": "pattern1", "category": "category1"},
            {"tx_hash": "tx2", "pattern": "pattern1", "category": "category2"},
            {"tx_hash": "tx3", "pattern": "pattern2", "category": "category1"},
        ]
        report = journal_writer.get_classification_report()
        assert report["total_transactions"] == 3
        assert report["unique_rules_applied"] == 2
        assert report["category_distribution"] == {"category1": 2, "category2": 1}
