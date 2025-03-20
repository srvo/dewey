"""Tests for dewey.core.bookkeeping.journal_fixer."""

import os
import re
import shutil
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, mock_open, patch

import pytest
from dewey.core.bookkeeping.journal_fixer import (
    FileSystemInterface,
    JournalFixer,
    RealFileSystem,
    main,
)


class TestFileSystem:
    """Tests for the FileSystemInterface and RealFileSystem."""

    def test_real_file_system_exists(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that RealFileSystem.exists returns True for existing files."""
        file_path = tmp_path.mktemp("test_file.txt")
        fs = RealFileSystem()
        assert fs.exists(str(file_path)) is True

    def test_real_file_system_copy2(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that RealFileSystem.copy2 copies a file."""
        src_path = tmp_path.mktemp("src_file.txt")
        dst_path = tmp_path.join("dst_file.txt")
        with open(src_path, "w") as f:
            f.write("test content")

        fs = RealFileSystem()
        fs.copy2(str(src_path), str(dst_path))
        assert os.path.exists(dst_path)

    def test_real_file_system_open(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that RealFileSystem.open opens a file."""
        file_path = tmp_path.mktemp("test_file.txt")
        with open(file_path, "w") as f:
            f.write("test content")

        fs = RealFileSystem()
        with fs.open(str(file_path)) as f:
            content = f.read()
        assert content == "test content"

    def test_real_file_system_move(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that RealFileSystem.move moves a file."""
        src_path = tmp_path.mktemp("src_file.txt")
        dst_path = tmp_path.join("dst_file.txt")
        with open(src_path, "w") as f:
            f.write("test content")

        fs = RealFileSystem()
        fs.move(str(src_path), str(dst_path))
        assert os.path.exists(dst_path)
        assert not os.path.exists(src_path)

    def test_real_file_system_listdir(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that RealFileSystem.listdir lists files in a directory."""
        tmp_path.mktemp("test_file1.txt")
        tmp_path.mktemp("test_file2.txt")

        fs = RealFileSystem()
        files = fs.listdir(str(tmp_path))
        assert len(files) >= 2
        assert "test_file1.txt" in files
        assert "test_file2.txt" in files


class TestJournalFixerInitialization:
    """Tests for JournalFixer initialization."""

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_journal_fixer_initialization(self, mock_init: MagicMock, mock_file_system_interface: MagicMock) -> None:
        """Test that JournalFixer initializes correctly."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        assert isinstance(fixer, JournalFixer)
        assert isinstance(fixer.logger, MagicMock)
        assert fixer.fs == mock_file_system_interface


class TestParseTransactions:
    """Tests for the parse_transactions method."""

    def test_parse_transactions_empty_content(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing transactions from empty content."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        content = ""
        transactions = fixer.parse_transactions(content)
        assert transactions == []

    def test_parse_transactions_single_transaction(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing a single transaction."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        content = """
        2024-01-01 Description
            Account1  100
            Account2  -100
        """
        transactions = fixer.parse_transactions(content)
        assert len(transactions) == 1
        assert transactions[0]["date"] == "2024-01-01"
        assert transactions[0]["description"] == "Description"
        assert len(transactions[0]["postings"]) == 2
        assert transactions[0]["postings"][0]["account"] == "Account1"
        assert transactions[0]["postings"][0]["amount"] == "100"
        assert transactions[0]["postings"][1]["account"] == "Account2"
        assert transactions[0]["postings"][1]["amount"] == "-100"

    def test_parse_transactions_multiple_transactions(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing multiple transactions."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        content = """
        2024-01-01 Description1
            Account1  100
            Account2  -100

        2024-01-02 Description2
            Account3  200
            Account4  -200
        """
        transactions = fixer.parse_transactions(content)
        assert len(transactions) == 2
        assert transactions[0]["date"] == "2024-01-01"
        assert transactions[0]["description"] == "Description1"
        assert transactions[1]["date"] == "2024-01-02"
        assert transactions[1]["description"] == "Description2"

    def test_parse_transactions_no_amount(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing transactions with no amount."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        content = """
        2024-01-01 Description
            Account1
        """
        transactions = fixer.parse_transactions(content)
        assert len(transactions) == 1
        assert transactions[0]["postings"][0]["account"] == "Account1"
        assert transactions[0]["postings"][0]["amount"] is None

    def test_parse_transactions_invalid_date_format(
        self, mock_file_system_interface: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test parsing transactions with an invalid date format."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        content = """
        2024/01/01 Description
            Account1  100
        """
        transactions = fixer.parse_transactions(content)
        assert transactions == []
        assert "Invalid transaction date format" in str(fixer.logger.debug.call_args)

    def test_parse_transactions_empty_transaction_lines(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing transactions with empty transaction lines."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        content = """

        2024-01-01 Description
            Account1  100
        """
        transactions = fixer.parse_transactions(content)
        assert len(transactions) == 1

    def test_parse_transactions_extra_whitespace(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing transactions with extra whitespace."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        content = """
        2024-01-01   Description  
            Account1    100   
            Account2   -100
        """
        transactions = fixer.parse_transactions(content)
        assert len(transactions) == 1
        assert transactions[0]["date"] == "2024-01-01"
        assert transactions[0]["description"] == "Description"
        assert len(transactions[0]["postings"]) == 2
        assert transactions[0]["postings"][0]["account"] == "Account1"
        assert transactions[0]["postings"][0]["amount"] == "100"
        assert transactions[0]["postings"][1]["account"] == "Account2"
        assert transactions[0]["postings"][1]["amount"] == "-100"


class TestProcessTransactions:
    """Tests for the process_transactions method."""

    def test_process_transactions_empty_transactions(self, mock_file_system_interface: MagicMock) -> None:
        """Test processing an empty list of transactions."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        transactions: List[Dict[str, Any]] = []
        fixed_content = fixer.process_transactions(transactions)
        assert fixed_content == ""

    def test_process_transactions_single_transaction(self, mock_file_system_interface: MagicMock) -> None:
        """Test processing a single transaction."""
        fixer = JournalFixer(fs=mock_file_system_interface)
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
        fixed_content = fixer.process_transactions(transactions)
        expected_content = "2024-01-01 Description\n    Account1  100\n    Account2  -100\n"
        assert fixed_content == expected_content

    def test_process_transactions_multiple_transactions(self, mock_file_system_interface: MagicMock) -> None:
        """Test processing multiple transactions."""
        fixer = JournalFixer(fs=mock_file_system_interface)
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
        fixed_content = fixer.process_transactions(transactions)
        expected_content = (
            "2024-01-01 Description1\n    Account1  100\n    Account2  -100\n\n"
            "2024-01-02 Description2\n    Account3  200\n    Account4  -200\n"
        )
        assert fixed_content == expected_content


class TestParseTransaction:
    """Tests for the parse_transaction method."""

    def test_parse_transaction_valid_lines(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing a valid transaction."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        lines = ["2024-01-01 Description", "    Account1  100", "    Account2  -100"]
        transaction = fixer.parse_transaction(lines)
        assert transaction is not None
        assert transaction["date"] == "2024-01-01"
        assert transaction["description"] == "Description"
        assert len(transaction["postings"]) == 2
        assert transaction["postings"][0]["account"] == "Account1"
        assert transaction["postings"][0]["amount"] == "100"
        assert transaction["postings"][1]["account"] == "Account2"
        assert transaction["postings"][1]["amount"] == "-100"

    def test_parse_transaction_invalid_date(self, mock_file_system_interface: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """Test parsing a transaction with an invalid date."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        lines = ["2024/01/01 Description", "    Account1  100"]
        transaction = fixer.parse_transaction(lines)
        assert transaction is None
        assert "Invalid transaction date format" in str(fixer.logger.debug.call_args)

    def test_parse_transaction_no_description(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing a transaction with no description."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        lines = ["2024-01-01", "    Account1  100"]
        transaction = fixer.parse_transaction(lines)
        assert transaction is not None
        assert transaction["description"] == ""

    def test_parse_transaction_empty_lines(self, mock_file_system_interface: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """Test parsing a transaction with empty lines."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        lines = ["", "    Account1  100"]
        transaction = fixer.parse_transaction(lines)
        assert transaction is None
        assert "Empty transaction lines encountered" in str(fixer.logger.debug.call_args)

    def test_parse_transaction_no_postings(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing a transaction with no postings."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        lines = ["2024-01-01 Description"]
        transaction = fixer.parse_transaction(lines)
        assert transaction is not None
        assert len(transaction["postings"]) == 0

    def test_parse_transaction_malformed_posting(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing a transaction with a malformed posting line."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        lines = ["2024-01-01 Description", "    Account1  100  Extra"]
        transaction = fixer.parse_transaction(lines)
        assert transaction is not None
        assert len(transaction["postings"]) == 1
        assert transaction["postings"][0]["account"] == "Account1"
        assert transaction["postings"][0]["amount"] == "100"

    def test_parse_transaction_only_whitespace_posting(self, mock_file_system_interface: MagicMock) -> None:
        """Test parsing a transaction with a posting line containing only whitespace."""
        fixer = JournalFixer(fs=mock_file_system_interface)
        lines = ["2024-01-01 Description", "     "]
        transaction = fixer.parse_transaction(lines)
        assert transaction is not None
        assert len(transaction["postings"]) == 0


class TestProcessJournalFile:
    """Tests for the process_journal_file method."""

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_process_journal_file_file_not_found(
        self, mock_init: MagicMock, mock_file_system_interface: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test processing a journal file that does not exist."""
        mock_file_system_interface.exists.return_value = False
        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        file_path = "nonexistent_file.journal"
        fixer.process_journal_file(file_path)
        mock_file_system_interface.exists.assert_called_once_with(file_path)
        assert f"File not found: {file_path}" in str(fixer.logger.error.call_args)

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_process_journal_file_success(
        self,
        mock_init: MagicMock,
        mock_file_system_interface: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test processing a journal file successfully."""
        mock_file_system_interface.exists.return_value = True
        mock_file_system_interface.open.return_value = mock_open(read_data="2024-01-01 Description\n    Account1  100").return_value

        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        file_path = "test.journal"

        fixer.process_journal_file(file_path)

        mock_file_system_interface.copy2.assert_called_once_with(file_path, file_path + ".bak")
        mock_file_system_interface.open.assert_called()
        mock_file_system_interface.open.return_value.write.assert_called()
        assert f"Processing file: {file_path}" in str(fixer.logger.info.call_args)
        assert f"Restoring from backup: {file_path}.bak" not in str(fixer.logger.info.call_args)

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_process_journal_file_copy_error(
        self, mock_init: MagicMock, mock_file_system_interface: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test processing a journal file when the copy fails."""
        mock_file_system_interface.exists.return_value = True
        mock_file_system_interface.copy2.side_effect = Exception("Copy failed")

        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        file_path = "test.journal"
        with pytest.raises(Exception, match="Copy failed"):
            fixer.process_journal_file(file_path)
        assert f"Failed to process {file_path}" in str(fixer.logger.exception.call_args)
        mock_file_system_interface.move.assert_not_called()

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_process_journal_file_open_error(
        self, mock_init: MagicMock, mock_file_system_interface: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test processing a journal file when the open fails."""
        mock_file_system_interface.exists.return_value = True
        mock_file_system_interface.open.side_effect = Exception("Open failed")

        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        file_path = "test.journal"
        with pytest.raises(Exception, match="Open failed"):
            fixer.process_journal_file(file_path)
        assert f"Failed to process {file_path}" in str(fixer.logger.exception.call_args)
        mock_file_system_interface.move.assert_not_called()

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_process_journal_file_restore_error(
        self,
        mock_init: MagicMock,
        mock_file_system_interface: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test processing a journal file when the restore fails."""
        mock_file_system_interface.exists.return_value = True
        mock_file_system_interface.open.return_value = mock_open(read_data="2024-01-01 Description\n    Account1  100").return_value
        mock_file_system_interface.move.side_effect = Exception("Move failed")

        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        file_path = "test.journal"
        with pytest.raises(Exception, match="Move failed"):
            fixer.process_journal_file(file_path)
        assert f"Failed to process {file_path}" in str(fixer.logger.exception.call_args)
        assert f"Restoring from backup: {file_path}.bak" in str(fixer.logger.info.call_args)


class TestRun:
    """Tests for the run method."""

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_run_processes_journal_files(
        self,
        mock_init: MagicMock,
        mock_file_system_interface: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that run processes all journal files in the directory."""
        mock_file_system_interface.listdir.return_value = ["test.journal", "test2.txt"]
        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        fixer.run()
        mock_file_system_interface.listdir.assert_called_once_with(".")
        mock_file_system_interface.process_journal_file = MagicMock()
        fixer.process_journal_file("test.journal")
        assert "Starting journal entries correction" in str(fixer.logger.info.call_args_list[0])
        assert "Completed journal entries correction" in str(fixer.logger.info.call_args_list[1])

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_run_processes_specific_files(
        self,
        mock_init: MagicMock,
        mock_file_system_interface: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that run processes only the specified journal files."""
        filenames = ["test.journal", "test2.journal"]
        fixer = JournalFixer(fs=mock_file_system_interface)
        fixer.logger = MagicMock()
        fixer.run(filenames=filenames)
        mock_file_system_interface.listdir.assert_not_called()
        mock_file_system_interface.process_journal_file = MagicMock()
        fixer.process_journal_file("test.journal")
        fixer.process_journal_file("test2.journal")
        assert "Starting journal entries correction" in str(fixer.logger.info.call_args_list[0])
        assert "Completed journal entries correction" in str(fixer.logger.info.call_args_list[1])


class TestMain:
    """Tests for the main function."""

    @patch("dewey.core.bookkeeping.journal_fixer.JournalFixer.execute")
    def test_main_calls_execute(self, mock_execute: MagicMock) -> None:
        """Test that main calls the execute method."""
        main()
        mock_execute.assert_called_once()
