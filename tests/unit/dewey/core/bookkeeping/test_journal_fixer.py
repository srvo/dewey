"""Tests for dewey.core.bookkeeping.journal_fixer."""

import os
import re
import shutil
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, mock_open, patch

import pytest
from dewey.core.bookkeeping.journal_fixer import JournalFixer, main


def test_journal_fixer_initialization(journal_fixer: MagicMock) -> None:
    """Test that JournalFixer initializes correctly."""
    assert isinstance(journal_fixer, JournalFixer)
    assert isinstance(journal_fixer.logger, MagicMock)


class TestParseTransactions:
    """Tests for the parse_transactions method."""

    def test_parse_transactions_empty_content(self, journal_fixer: MagicMock) -> None:
        """Test parsing transactions from empty content."""
        content = ""
        transactions = journal_fixer.parse_transactions(content)
        assert transactions == []

    def test_parse_transactions_single_transaction(self, journal_fixer: MagicMock) -> None:
        """Test parsing a single transaction."""
        content = """
        2024-01-01 Description
            Account1  100
            Account2  -100
        """
        transactions = journal_fixer.parse_transactions(content)
        assert len(transactions) == 1
        assert transactions[0]["date"] == "2024-01-01"
        assert transactions[0]["description"] == "Description"
        assert len(transactions[0]["postings"]) == 2
        assert transactions[0]["postings"][0]["account"] == "Account1"
        assert transactions[0]["postings"][0]["amount"] == "100"
        assert transactions[0]["postings"][1]["account"] == "Account2"
        assert transactions[0]["postings"][1]["amount"] == "-100"

    def test_parse_transactions_multiple_transactions(self, journal_fixer: MagicMock) -> None:
        """Test parsing multiple transactions."""
        content = """
        2024-01-01 Description1
            Account1  100
            Account2  -100

        2024-01-02 Description2
            Account3  200
            Account4  -200
        """
        transactions = journal_fixer.parse_transactions(content)
        assert len(transactions) == 2
        assert transactions[0]["date"] == "2024-01-01"
        assert transactions[0]["description"] == "Description1"
        assert transactions[1]["date"] == "2024-01-02"
        assert transactions[1]["description"] == "Description2"

    def test_parse_transactions_no_amount(self, journal_fixer: MagicMock) -> None:
        """Test parsing transactions with no amount."""
        content = """
        2024-01-01 Description
            Account1
        """
        transactions = journal_fixer.parse_transactions(content)
        assert len(transactions) == 1
        assert transactions[0]["postings"][0]["account"] == "Account1"
        assert transactions[0]["postings"][0]["amount"] is None

    def test_parse_transactions_invalid_date_format(
        self, journal_fixer: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test parsing transactions with an invalid date format."""
        content = """
        2024/01/01 Description
            Account1  100
        """
        transactions = journal_fixer.parse_transactions(content)
        assert transactions == []
        assert "Invalid transaction date format" in caplog.text

    def test_parse_transactions_empty_transaction_lines(
        self, journal_fixer: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test parsing transactions with empty transaction lines."""
        content = """

        2024-01-01 Description
            Account1  100
        """
        transactions = journal_fixer.parse_transactions(content)
        assert len(transactions) == 1
        assert "Empty transaction lines encountered" not in caplog.text


class TestProcessTransactions:
    """Tests for the process_transactions method."""

    def test_process_transactions_empty_transactions(self, journal_fixer: MagicMock) -> None:
        """Test processing an empty list of transactions."""
        transactions: List[Dict[str, Any]] = []
        fixed_content = journal_fixer.process_transactions(transactions)
        assert fixed_content == ""

    def test_process_transactions_single_transaction(self, journal_fixer: MagicMock) -> None:
        """Test processing a single transaction."""
        transactions: List[Dict[str, Any]] = [
            {
                "date": "2024-01-01",
                "description": "Description",
                "postings": [
                    {"account": "Account1", "amount": "100"},
                    {"account": "Account2", "amount": "-100"},
                ],
            }
        ]
        fixed_content = journal_fixer.process_transactions(transactions)
        expected_content = "2024-01-01 Description\n    Account1  100\n    Account2  -100\n"
        assert fixed_content == expected_content

    def test_process_transactions_multiple_transactions(self, journal_fixer: MagicMock) -> None:
        """Test processing multiple transactions."""
        transactions: List[Dict[str, Any]] = [
            {
                "date": "2024-01-01",
                "description": "Description1",
                "postings": [
                    {"account": "Account1", "amount": "100"},
                    {"account": "Account2", "amount": "-100"},
                ],
            },
            {
                "date": "2024-01-02",
                "description": "Description2",
                "postings": [
                    {"account": "Account3", "amount": "200"},
                    {"account": "Account4", "amount": "-200"},
                ],
            },
        ]
        fixed_content = journal_fixer.process_transactions(transactions)
        expected_content = (
            "2024-01-01 Description1\n    Account1  100\n    Account2  -100\n\n"
            "2024-01-02 Description2\n    Account3  200\n    Account4  -200\n"
        )
        assert fixed_content == expected_content


class TestParseTransaction:
    """Tests for the parse_transaction method."""

    def test_parse_transaction_valid_lines(self, journal_fixer: MagicMock) -> None:
        """Test parsing a valid transaction."""
        lines = ["2024-01-01 Description", "    Account1  100", "    Account2  -100"]
        transaction = journal_fixer.parse_transaction(lines)
        assert transaction is not None
        assert transaction["date"] == "2024-01-01"
        assert transaction["description"] == "Description"
        assert len(transaction["postings"]) == 2
        assert transaction["postings"][0]["account"] == "Account1"
        assert transaction["postings"][0]["amount"] == "100"
        assert transaction["postings"][1]["account"] == "Account2"
        assert transaction["postings"][1]["amount"] == "-100"

    def test_parse_transaction_invalid_date(self, journal_fixer: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """Test parsing a transaction with an invalid date."""
        lines = ["2024/01/01 Description", "    Account1  100"]
        transaction = journal_fixer.parse_transaction(lines)
        assert transaction is None
        assert "Invalid transaction date format" in caplog.text

    def test_parse_transaction_no_description(self, journal_fixer: MagicMock) -> None:
        """Test parsing a transaction with no description."""
        lines = ["2024-01-01", "    Account1  100"]
        transaction = journal_fixer.parse_transaction(lines)
        assert transaction is not None
        assert transaction["description"] == ""

    def test_parse_transaction_empty_lines(self, journal_fixer: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """Test parsing a transaction with empty lines."""
        lines = ["", "    Account1  100"]
        transaction = journal_fixer.parse_transaction(lines)
        assert transaction is None
        assert "Empty transaction lines encountered" in caplog.text

    def test_parse_transaction_no_postings(self, journal_fixer: MagicMock) -> None:
        """Test parsing a transaction with no postings."""
        lines = ["2024-01-01 Description"]
        transaction = journal_fixer.parse_transaction(lines)
        assert transaction is not None
        assert len(transaction["postings"]) == 0


class TestProcessJournalFile:
    """Tests for the process_journal_file method."""

    def test_process_journal_file_file_not_found(self, journal_fixer: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """Test processing a journal file that does not exist."""
        file_path = "nonexistent_file.journal"
        journal_fixer.process_journal_file(file_path)
        assert f"File not found: {file_path}" in caplog.text

    @patch("os.path.exists")
    @patch("shutil.copy2")
    @patch("builtins.open", new_callable=mock_open, read_data="2024-01-01 Description\n    Account1  100")
    @patch.object(JournalFixer, "parse_transactions")
    @patch.object(JournalFixer, "process_transactions")
    def test_process_journal_file_success(
        self,
        mock_process_transactions: MagicMock,
        mock_parse_transactions: MagicMock,
        mock_open_file: MagicMock,
        mock_copy2: MagicMock,
        mock_exists: MagicMock,
        journal_fixer: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test processing a journal file successfully."""
        mock_exists.return_value = True
        mock_parse_transactions.return_value = [
            {"date": "2024-01-01", "description": "Description", "postings": [{"account": "Account1", "amount": "100"}]}
        ]
        mock_process_transactions.return_value = "2024-01-01 Description\n    Account1  100"

        file_path = "test.journal"
        journal_fixer.process_journal_file(file_path)

        mock_copy2.assert_called_once_with(file_path, file_path + ".bak")
        mock_parse_transactions.assert_called_once()
        mock_process_transactions.assert_called_once()
        mock_open_file.assert_called()
        assert f"Processing file: {file_path}" in caplog.text
        assert f"Restoring from backup: {file_path}.bak" not in caplog.text

    @patch("os.path.exists")
    @patch("shutil.copy2", side_effect=Exception("Copy failed"))
    def test_process_journal_file_copy_error(
        self, mock_copy2: MagicMock, mock_exists: MagicMock, journal_fixer: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test processing a journal file when the copy fails."""
        mock_exists.return_value = True
        file_path = "test.journal"
        with pytest.raises(Exception, match="Copy failed"):
            journal_fixer.process_journal_file(file_path)
        assert f"Failed to process {file_path}" in caplog.text

    @patch("os.path.exists")
    @patch("shutil.copy2")
    @patch("builtins.open", side_effect=Exception("Open failed"))
    def test_process_journal_file_open_error(
        self, mock_open_file: MagicMock, mock_copy2: MagicMock, mock_exists: MagicMock, journal_fixer: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test processing a journal file when the open fails."""
        mock_exists.return_value = True
        file_path = "test.journal"
        with pytest.raises(Exception, match="Open failed"):
            journal_fixer.process_journal_file(file_path)
        assert f"Failed to process {file_path}" in caplog.text

    @patch("os.path.exists")
    @patch("shutil.copy2")
    @patch("builtins.open", new_callable=mock_open, read_data="2024-01-01 Description\n    Account1  100")
    @patch.object(JournalFixer, "parse_transactions", side_effect=Exception("Parse failed"))
    def test_process_journal_file_parse_error(
        self,
        mock_parse_transactions: MagicMock,
        mock_open_file: MagicMock,
        mock_copy2: MagicMock,
        mock_exists: MagicMock,
        journal_fixer: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test processing a journal file when the parsing fails."""
        mock_exists.return_value = True
        file_path = "test.journal"
        with pytest.raises(Exception, match="Parse failed"):
            journal_fixer.process_journal_file(file_path)
        assert f"Failed to process {file_path}" in caplog.text

    @patch("os.path.exists")
    @patch("shutil.copy2")
    @patch("builtins.open", new_callable=mock_open, read_data="2024-01-01 Description\n    Account1  100")
    @patch.object(JournalFixer, "parse_transactions")
    @patch.object(JournalFixer, "process_transactions", side_effect=Exception("Process failed"))
    def test_process_journal_file_process_error(
        self,
        mock_process_transactions: MagicMock,
        mock_parse_transactions: MagicMock,
        mock_open_file: MagicMock,
        mock_copy2: MagicMock,
        mock_exists: MagicMock,
        journal_fixer: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test processing a journal file when the processing fails."""
        mock_exists.return_value = True
        mock_parse_transactions.return_value = [
            {"date": "2024-01-01", "description": "Description", "postings": [{"account": "Account1", "amount": "100"}]}
        ]
        file_path = "test.journal"
        with pytest.raises(Exception, match="Process failed"):
            journal_fixer.process_journal_file(file_path)
        assert f"Failed to process {file_path}" in caplog.text

    @patch("os.path.exists")
    @patch("shutil.copy2")
    @patch("builtins.open", new_callable=mock_open, read_data="2024-01-01 Description\n    Account1  100")
    @patch.object(JournalFixer, "parse_transactions")
    @patch.object(JournalFixer, "process_transactions")
    @patch("shutil.move", side_effect=Exception("Move failed"))
    def test_process_journal_file_restore_error(
        self,
        mock_move: MagicMock,
        mock_process_transactions: MagicMock,
        mock_parse_transactions: MagicMock,
        mock_open_file: MagicMock,
        mock_copy2: MagicMock,
        mock_exists: MagicMock,
        journal_fixer: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test processing a journal file when the restore fails."""
        mock_exists.return_value = True
        mock_parse_transactions.return_value = [
            {"date": "2024-01-01", "description": "Description", "postings": [{"account": "Account1", "amount": "100"}]}
        ]
        mock_process_transactions.return_value = "2024-01-01 Description\n    Account1  100"
        file_path = "test.journal"
        with pytest.raises(Exception, match="Move failed"):
            journal_fixer.process_journal_file(file_path)
        assert f"Failed to process {file_path}" in caplog.text
        assert f"Restoring from backup: {file_path}.bak" in caplog.text


class TestRun:
    """Tests for the run method."""

    @patch("os.listdir")
    @patch.object(JournalFixer, "process_journal_file")
    def test_run_processes_journal_files(
        self, mock_process_journal_file: MagicMock, mock_listdir: MagicMock, journal_fixer: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that run processes all journal files in the directory."""
        mock_listdir.return_value = ["test.journal", "test2.txt"]
        journal_fixer.run()
        mock_process_journal_file.assert_called_once_with("test.journal")
        assert "Starting journal entries correction" in caplog.text
        assert "Completed journal entries correction" in caplog.text


class TestMain:
    """Tests for the main function."""

    @patch.object(JournalFixer, "execute")
    def test_main_calls_execute(self, mock_execute: MagicMock) -> None:
        """Test that main calls the execute method."""
        main()
        mock_execute.assert_called_once()
