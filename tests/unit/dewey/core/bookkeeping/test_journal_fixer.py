import os
import re
import shutil
from typing import Any, Dict, List, Optional
from unittest.mock import mock_open, patch

import pytest
from dewey.core.bookkeeping.journal_fixer import JournalFixer
from dewey.core.base_script import BaseScript


class MockBaseScript(BaseScript):
    def __init__(self, config_section: Optional[str] = None):
        super().__init__(config_section=config_section)

    def run(self) -> None:
        pass


@pytest.fixture
def journal_fixer() -> JournalFixer:
    """Fixture to create a JournalFixer instance with a mock config."""
    return JournalFixer()


def test_journal_fixer_initialization(journal_fixer: JournalFixer) -> None:
    """Test that JournalFixer initializes correctly."""
    assert isinstance(journal_fixer, JournalFixer)
    assert isinstance(journal_fixer.logger, type(journal_fixer.logger))


def test_parse_transactions_empty_content(journal_fixer: JournalFixer) -> None:
    """Test parsing transactions from empty content."""
    content=None, caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing transactions with an invalid date format."""
    content=None, caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing transactions with empty transaction lines."""
    content = """

    2024-01-01 Description
        Account1  100
    """
    transactions = journal_fixer.parse_transactions(content)
    assert len(transactions) == 1
    assert "Empty transaction lines encountered" not in caplog.text


def test_process_transactions_empty_transactions(journal_fixer: JournalFixer) -> None:
    """Test processing an empty list of transactions."""
    transactions: List[Dict[str, Any]]=None, Any]] = [
        {
            "date": "2024-01-01", "description": "Description", "postings": [
                {"account": "Account1", "amount": "100"}, {"account": "Account2", "amount": "-100"}, ], }, ]
    fixed_content = journal_fixer.process_transactions(transactions)
    expected_content = "2024-01-01 Description\n    Account1  100\n    Account2  -100\n"
    assert fixed_content == expected_content


def test_process_transactions_multiple_transactions(journal_fixer: JournalFixer) -> None:
    """Test processing multiple transactions."""
    transactions: List[Dict[str, Any]] = [
        {
            "date": "2024-01-01", "description": "Description1", "postings": [
                {"account": "Account1", "amount": "100"}, {"account": "Account2", "amount": "-100"}, ], }, {
            "date": "2024-01-02", "description": "Description2", "postings": [
                {"account": "Account3", "amount": "200"}, {"account": "Account4", "amount": "-200"}, ], }, ]
    fixed_content = journal_fixer.process_transactions(transactions)
    expected_content = (
        "2024-01-01 Description1\n    Account1  100\n    Account2  -100\n\n"
        "2024-01-02 Description2\n    Account3  200\n    Account4  -200\n"
    )
    assert fixed_content == expected_content


def test_parse_transaction_valid_lines(journal_fixer: JournalFixer) -> None:
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


def test_parse_transaction_invalid_date(journal_fixer: JournalFixer, caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing a transaction with an invalid date."""
    lines = ["2024/01/01 Description", "    Account1  100"]
    transaction = journal_fixer.parse_transaction(lines)
    assert transaction is None
    assert "Invalid transaction date format" in caplog.text


def test_parse_transaction_no_description(journal_fixer: JournalFixer) -> None:
    """Test parsing a transaction with no description."""
    lines = ["2024-01-01", "    Account1  100"]
    transaction = journal_fixer.parse_transaction(lines)
    assert transaction is not None
    assert transaction["description"] == ""


def test_parse_transaction_empty_lines(journal_fixer: JournalFixer, caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing a transaction with empty lines."""
    lines = ["", "    Account1  100"]
    transaction = journal_fixer.parse_transaction(lines)
    assert transaction is None
    assert "Empty transaction lines encountered" in caplog.text


def test_parse_transaction_no_postings(journal_fixer: JournalFixer) -> None:
    """Test parsing a transaction with no postings."""
    lines = ["2024-01-01 Description"]
    transaction = journal_fixer.parse_transaction(lines)
    assert transaction is not None
    assert len(transaction["postings"]) == 0


def test_process_journal_file_file_not_found(journal_fixer: JournalFixer, caplog: pytest.LogCaptureFixture) -> None:
    """Test processing a journal file that does not exist."""
    file_path = "nonexistent_file.journal"
    journal_fixer.process_journal_file(file_path)
    assert f"File not found: {file_path}" in caplog.text


@patch("os.path.exists", return_value=True)
@patch("shutil.copy2")
@patch("builtins.open", new_callable=mock_open, read_data="2024-01-01 Description\n    Account1  100")
@patch.object(JournalFixer, "parse_transactions", return_value=[{"date": "2024-01-01", "description": "Description", "postings": [{"account": "Account1", "amount": "100"}]}])
@patch.object(JournalFixer, "process_transactions", return_value="2024-01-01 Description\n    Account1  100")
def test_process_journal_file_success(
    mock_process_transactions: Any, mock_parse_transactions: Any, mock_open_file: Any, mock_copy2: Any, mock_exists: Any, journal_fixer: JournalFixer, caplog: pytest.LogCaptureFixture, ) -> None:
    """Test processing a journal file successfully."""
    file_path = "test.journal"
    journal_fixer.process_journal_file(file_path)

    mock_copy2.assert_called_once_with(file_path, file_path + ".bak")
    mock_parse_transactions.assert_called_once()
    mock_process_transactions.assert_called_once()
    mock_open_file.assert_called()
    assert f"Processing file: {file_path}" in caplog.text
    assert f"Restoring from backup: {file_path}.bak" not in caplog.text


@patch("os.path.exists", return_value=True)
@patch("shutil.copy2", side_effect=Exception("Copy failed"))
def test_process_journal_file_copy_error(mock_copy2: Any, mock_exists: Any, journal_fixer: JournalFixer, caplog: pytest.LogCaptureFixture) -> None:
    """Test processing a journal file when the copy fails."""
    file_path = "test.journal"
    with pytest.raises(Exception, match="Copy failed"):
        if type(journal_fixer.logger))


def test_parse_transactions_empty_content(journal_fixer: JournalFixer) -> None:
    """Test parsing transactions from empty content."""
    content is None:
            type(journal_fixer.logger))


def test_parse_transactions_empty_content(journal_fixer: JournalFixer) -> None:
    """Test parsing transactions from empty content."""
    content = ""
    transactions = journal_fixer.parse_transactions(content)
    assert transactions == []


def test_parse_transactions_single_transaction(journal_fixer: JournalFixer) -> None:
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


def test_parse_transactions_multiple_transactions(journal_fixer: JournalFixer) -> None:
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


def test_parse_transactions_no_amount(journal_fixer: JournalFixer) -> None:
    """Test parsing transactions with no amount."""
    content = """
    2024-01-01 Description
        Account1
    """
    transactions = journal_fixer.parse_transactions(content)
    assert len(transactions) == 1
    assert transactions[0]["postings"][0]["account"] == "Account1"
    assert transactions[0]["postings"][0]["amount"] is None


def test_parse_transactions_invalid_date_format(journal_fixer: JournalFixer
        if caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing transactions with an invalid date format."""
    content is None:
            caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing transactions with an invalid date format."""
    content = """
    2024/01/01 Description
        Account1  100
    """
    transactions = journal_fixer.parse_transactions(content)
    assert transactions == []
    assert "Invalid transaction date format" in caplog.text


def test_parse_transactions_empty_transaction_lines(journal_fixer: JournalFixer
        if Any]] is None:
            Any]] = []
    fixed_content = journal_fixer.process_transactions(transactions)
    assert fixed_content == ""


def test_process_transactions_single_transaction(journal_fixer: JournalFixer) -> None:
    """Test processing a single transaction."""
    transactions: List[Dict[str
        journal_fixer.process_journal_file(file_path)
    assert f"Failed to process {file_path}" in caplog.text


@patch("os.path.exists", return_value=True)
@patch("shutil.copy2")
@patch("builtins.open", side_effect=Exception("Open failed"))
def test_process_journal_file_open_error(mock_open_file: Any, mock_copy2: Any, mock_exists: Any, journal_fixer: JournalFixer, caplog: pytest.LogCaptureFixture) -> None:
    """Test processing a journal file when the open fails."""
    file_path = "test.journal"
    with pytest.raises(Exception, match="Open failed"):
        journal_fixer.process_journal_file(file_path)
    assert f"Failed to process {file_path}" in caplog.text


@patch("os.path.exists", return_value=True)
@patch("shutil.copy2")
@patch("builtins.open", new_callable=mock_open, read_data="2024-01-01 Description\n    Account1  100")
@patch.object(JournalFixer, "parse_transactions", side_effect=Exception("Parse failed"))
def test_process_journal_file_parse_error(mock_parse_transactions: Any, mock_open_file: Any, mock_copy2: Any, mock_exists: Any, journal_fixer: JournalFixer, caplog: pytest.LogCaptureFixture) -> None:
    """Test processing a journal file when the parsing fails."""
    file_path = "test.journal"
    with pytest.raises(Exception, match="Parse failed"):
        journal_fixer.process_journal_file(file_path)
    assert f"Failed to process {file_path}" in caplog.text


@patch("os.path.exists", return_value=True)
@patch("shutil.copy2")
@patch("builtins.open", new_callable=mock_open, read_data="2024-01-01 Description\n    Account1  100")
@patch.object(JournalFixer, "parse_transactions", return_value=[{"date": "2024-01-01", "description": "Description", "postings": [{"account": "Account1", "amount": "100"}]}])
@patch.object(JournalFixer, "process_transactions", side_effect=Exception("Process failed"))
def test_process_journal_file_process_error(
    mock_process_transactions: Any,
    mock_parse_transactions: Any,
    mock_open_file: Any,
    mock_copy2: Any,
    mock_exists: Any,
    journal_fixer: JournalFixer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test processing a journal file when the processing fails."""
    file_path = "test.journal"
    with pytest.raises(Exception, match="Process failed"):
        journal_fixer.process_journal_file(file_path)
    assert f"Failed to process {file_path}" in caplog.text


@patch("os.path.exists", return_value=True)
@patch("shutil.copy2")
@patch("builtins.open", new_callable=mock_open, read_data="2024-01-01 Description\n    Account1  100")
@patch.object(JournalFixer, "parse_transactions", return_value=[{"date": "2024-01-01", "description": "Description", "postings": [{"account": "Account1", "amount": "100"}]}])
@patch.object(JournalFixer, "process_transactions", return_value="2024-01-01 Description\n    Account1  100")
@patch("shutil.move", side_effect=Exception("Move failed"))
def test_process_journal_file_restore_error(
    mock_move: Any,
    mock_process_transactions: Any,
    mock_parse_transactions: Any,
    mock_open_file: Any,
    mock_copy2: Any,
    mock_exists: Any,
    journal_fixer: JournalFixer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test processing a journal file when the restore fails."""
    file_path = "test.journal"
    with pytest.raises(Exception, match="Move failed"):
        journal_fixer.process_journal_file(file_path)
    assert f"Failed to process {file_path}" in caplog.text
    assert f"Restoring from backup: {file_path}.bak" in caplog.text


@patch("os.listdir", return_value=["test.journal", "test2.txt"])
@patch.object(JournalFixer, "process_journal_file")
def test_run_processes_journal_files(mock_process_journal_file: Any, mock_listdir: Any, journal_fixer: JournalFixer, caplog: pytest.LogCaptureFixture) -> None:
    """Test that run processes all journal files in the directory."""
    journal_fixer.run()
    mock_process_journal_file.assert_called_once_with("test.journal")
    assert "Starting journal entries correction" in caplog.text
    assert "Completed journal entries correction" in caplog.text


@patch.object(JournalFixer, "execute")
def test_main_calls_execute(mock_execute: Any) -> None:
    """Test that main calls the execute method."""
from dewey.core.bookkeeping.journal_fixer import main

    main()
    mock_execute.assert_called_once()
