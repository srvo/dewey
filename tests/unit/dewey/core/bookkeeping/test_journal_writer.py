"""Tests for dewey.core.bookkeeping.journal_writer."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from typing import Dict, List, Any, Tuple, Callable

import pytest
from dewey.core.bookkeeping.journal_writer import JournalWriter, JournalWriteError, IOServiceInterface
from dewey.core.base_script import BaseScript
from datetime import datetime


class TestJournalWriter:
    """Tests for the JournalWriter class."""

    @pytest.fixture
    def journal_writer(self, tmp_path: Path, mock_base_script: MagicMock, mock_io_service: MagicMock) -> JournalWriter:
        """Fixture for creating a JournalWriter instance."""
        with patch("dewey.core.bookkeeping.journal_writer.BaseScript", return_value=mock_base_script):
            journal_writer = JournalWriter(io_service=mock_io_service)
            journal_writer.output_dir = tmp_path
            journal_writer.processed_hashes_file = tmp_path / ".processed_hashes"
            return journal_writer

    def test_init(self, tmp_path: Path, mock_base_script: MagicMock, mock_io_service: MagicMock) -> None:
        """Test JournalWriter initialization."""
        mock_base_script.get_config_value.return_value = str(tmp_path / "journals")
        with patch("dewey.core.bookkeeping.journal_writer.BaseScript", return_value=mock_base_script):
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                journal_writer = JournalWriter(io_service=mock_io_service)
                assert journal_writer.output_dir == tmp_path / "journals"
                mock_mkdir.assert_called_with(parents=True, exist_ok=True)
                assert journal_writer.processed_hashes_file == journal_writer.output_dir / ".processed_hashes"
                assert isinstance(journal_writer.seen_hashes, set)
                assert isinstance(journal_writer.audit_log, list)
                mock_base_script.assert_called_once_with(config_section="bookkeeping")

    def test_run(self, journal_writer: JournalWriter, mock_base_script: MagicMock) -> None:
        """Test the run method."""
        journal_writer.logger = MagicMock()
        journal_writer.db_conn = MagicMock()
        journal_writer.db_conn.execute.return_value = "DB Result"
        journal_writer.run()
        journal_writer.logger.info.assert_called()
        journal_writer.db_conn.execute.assert_called_once_with("SELECT 1")

    def test_run_no_db(self, journal_writer: JournalWriter, mock_base_script: MagicMock) -> None:
        """Test the run method when no db connection exists."""
        journal_writer.logger = MagicMock()
        journal_writer.db_conn = None
        journal_writer.run()
        journal_writer.logger.info.assert_called()

    @patch("builtins.open", new_callable=mock_open, read_data="hash1\nhash2\nhash3")
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_processed_hashes_success(self, mock_exists: MagicMock, mock_open_file: MagicMock, journal_writer: JournalWriter, mock_io_service: MagicMock) -> None:
        """Test loading processed hashes from file successfully."""
        mock_io_service.read_text.return_value = "hash1\nhash2\nhash3"
        loaded_hashes = journal_writer._load_processed_hashes()
        assert loaded_hashes == {"hash1", "hash2", "hash3"}
        mock_exists.assert_called_once()
        mock_io_service.read_text.assert_called_once_with(journal_writer.processed_hashes_file)

    @patch("pathlib.Path.exists", return_value=False)
    def test_load_processed_hashes_file_not_exists(self, mock_exists: MagicMock, journal_writer: JournalWriter) -> None:
        """Test loading processed hashes when the file does not exist."""
        loaded_hashes = journal_writer._load_processed_hashes()
        assert loaded_hashes == set()
        mock_exists.assert_called_once()

    @patch("builtins.open", side_effect=Exception("Test Exception"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_processed_hashes_failure(self, mock_exists: MagicMock, mock_open_file: MagicMock, journal_writer: JournalWriter) -> None:
        """Test loading processed hashes when an exception occurs."""
        journal_writer.logger = MagicMock()
        mock_io_service = MagicMock()
        mock_io_service.read_text.side_effect = Exception("Test Exception")
        journal_writer.io_service = mock_io_service
        loaded_hashes = journal_writer._load_processed_hashes()
        assert loaded_hashes == set()
        journal_writer.logger.exception.assert_called_once()
        mock_exists.assert_called_once()
        mock_io_service.read_text.assert_called_once_with(journal_writer.processed_hashes_file)

    def test_save_processed_hashes_success(self, journal_writer: JournalWriter, mock_io_service: MagicMock) -> None:
        """Test saving processed hashes successfully."""
        seen_hashes = {"hash1", "hash2", "hash3"}
        journal_writer._save_processed_hashes(seen_hashes)
        mock_io_service.write_text.assert_called_once_with(journal_writer.processed_hashes_file, "hash1\nhash2\nhash3")

    def test_save_processed_hashes_failure(self, journal_writer: JournalWriter, mock_io_service: MagicMock) -> None:
        """Test saving processed hashes when an exception occurs."""
        journal_writer.logger = MagicMock()
        mock_io_service.write_text.side_effect = Exception("Test Exception")
        journal_writer.io_service = mock_io_service
        seen_hashes = {"hash1", "hash2", "hash3"}
        journal_writer._save_processed_hashes(seen_hashes)
        journal_writer.logger.exception.assert_called_once()
        mock_io_service.write_text.assert_called_once_with(journal_writer.processed_hashes_file, "hash1\nhash2\nhash3")

    def test_write_file_with_backup_new_file(self, journal_writer: JournalWriter, tmp_path: Path, mock_io_service: MagicMock) -> None:
        """Test writing to a new file with backup."""
        filename = tmp_path / "test.journal"
        entries = ["entry1", "entry2"]

        journal_writer._write_file_with_backup(filename, entries, now_func=lambda: datetime(2024, 1, 1, 0, 0, 0))

        mock_io_service.copy_file.assert_not_called()
        mock_io_service.write_text.assert_called_once_with(filename, "entry1\nentry2\n\n")

    @patch("pathlib.Path.exists", return_value=True)
    def test_write_file_with_backup_existing_file(self, mock_exists: MagicMock, journal_writer: JournalWriter, tmp_path: Path, mock_io_service: MagicMock) -> None:
        """Test writing to an existing file with backup."""
        filename = tmp_path / "test.journal"
        entries = ["entry1", "entry2"]

        journal_writer._write_file_with_backup(filename, entries, now_func=lambda: datetime(2024, 1, 1, 0, 0, 0))

        mock_exists.assert_called_once_with()
        mock_io_service.copy_file.assert_called_once_with(filename, tmp_path / "test_20240101000000.journal")
        mock_io_service.write_text.assert_called_once_with(filename, "entry1\nentry2\n\n")

    def test_write_file_with_backup_failure(self, journal_writer: JournalWriter, tmp_path: Path, mock_io_service: MagicMock) -> None:
        """Test writing to a file with backup when an exception occurs."""
        journal_writer.logger = MagicMock()
        filename = tmp_path / "test.journal"
        entries = ["entry1", "entry2"]
        mock_io_service.copy_file.side_effect = Exception("Test Exception")
        journal_writer.io_service = mock_io_service

        journal_writer._write_file_with_backup(filename, entries, now_func=lambda: datetime(2024, 1, 1, 0, 0, 0))

        journal_writer.logger.exception.assert_called_once()
        mock_io_service.write_text.assert_not_called()

    def test_group_entries_by_account_and_year(self, journal_writer: JournalWriter) -> None:
        """Test grouping entries by account ID and year."""
        entries = {"2023": ["entry1", "entry2"], "2024": ["entry3"]}
        journal_writer.config_source.get_config_value.return_value = "1234"
        grouped_entries = journal_writer._group_entries_by_account_and_year(entries)
        assert grouped_entries == {("1234", "2023"): ["entry1", "entry2"], ("1234", "2024"): ["entry3"]}
        journal_writer.config_source.get_config_value.assert_called_with("default_account_id", "8542")

    def test_group_entries_by_account_and_year_with_provided_func(self, journal_writer: JournalWriter) -> None:
        """Test grouping entries by account ID and year with a provided function."""
        entries = {"2023": ["entry1", "entry2"], "2024": ["entry3"]}
        mock_get_account_id: MagicMock = MagicMock(return_value="5678")
        grouped_entries = journal_writer._group_entries_by_account_and_year(entries, get_account_id=mock_get_account_id)
        assert grouped_entries == {("5678", "2023"): ["entry1", "entry2"], ("5678", "2024"): ["entry3"]}
        mock_get_account_id.assert_called()

    @patch("dewey.core.bookkeeping.journal_writer.JournalWriter._group_entries_by_account_and_year")
    @patch("dewey.core.bookkeeping.journal_writer.JournalWriter._write_file_with_backup")
    @patch("dewey.core.bookkeeping.journal_writer.JournalWriter._save_processed_hashes")
    def test_write_entries(self, mock_save_hashes: MagicMock, mock_write_file: MagicMock, mock_group_entries: MagicMock, journal_writer: JournalWriter, tmp_path: Path) -> None:
        """Test writing journal entries to appropriate files."""
        entries = {"2023": ["entry1", "entry2"], "2024": ["entry3"]}
        mock_group_entries.return_value = {("1234", "2023"): ["entry1", "entry2"], ("1234", "2024"): ["entry3"]}
        journal_writer.logger = MagicMock()

        journal_writer.write_entries(entries)

        mock_group_entries.assert_called_once_with(entries)
        mock_write_file.assert_any_call(tmp_path / "1234_2023.journal", ["entry1", "entry2"])
        mock_write_file.assert_any_call(tmp_path / "1234_2024.journal", ["entry3"])
        mock_save_hashes.assert_called_once_with(journal_writer.seen_hashes)
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
