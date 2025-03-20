"""Tests for hledger utilities."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dewey.core.bookkeeping.hledger_utils import (
    run_hledger_command,
    check_journal_file,
    parse_journal_entries,
    format_amount,
    validate_account_name
)

class TestHledgerUtils:
    """Test suite for hledger utilities."""

    def test_run_hledger_command_success(self, mock_subprocess_run):
        """Test successful hledger command execution."""
        result = run_hledger_command(["check"])
        assert result.returncode == 0
        mock_subprocess_run.assert_called_once()

    def test_run_hledger_command_failure(self, mock_subprocess_run):
        """Test failed hledger command execution."""
        mock_subprocess_run.return_value.returncode = 1
        with pytest.raises(Exception):
            run_hledger_command(["invalid"])

    def test_check_journal_file_valid(self, sample_journal_dir):
        """Test journal file validation with valid file."""
        journal_file = sample_journal_dir / "2024.journal"
        assert check_journal_file(journal_file) is True

    def test_check_journal_file_invalid(self, tmp_path):
        """Test journal file validation with invalid file."""
        invalid_file = tmp_path / "invalid.journal"
        invalid_file.write_text("Invalid content")
        assert check_journal_file(invalid_file) is False

    def test_parse_journal_entries(self, mock_hledger_output):
        """Test parsing journal entries."""
        entries = parse_journal_entries(mock_hledger_output)
        assert len(entries) == 2
        assert entries[0]["date"] == "2024-01-01"
        assert entries[0]["description"] == "Opening Balance"
        assert len(entries[0]["postings"]) == 2

    def test_format_amount_positive(self):
        """Test amount formatting for positive numbers."""
        assert format_amount(100.50) == "$100.50"
        assert format_amount(1000) == "$1000.00"

    def test_format_amount_negative(self):
        """Test amount formatting for negative numbers."""
        assert format_amount(-50.25) == "$-50.25"
        assert format_amount(-1000) == "$-1000.00"

    def test_validate_account_name_valid(self):
        """Test account name validation with valid names."""
        valid_names = [
            "Assets:Checking",
            "Expenses:Office:Supplies",
            "Income:Salary",
            "Liabilities:CreditCard"
        ]
        for name in valid_names:
            assert validate_account_name(name) is True

    def test_validate_account_name_invalid(self):
        """Test account name validation with invalid names."""
        invalid_names = [
            "assets:checking",  # lowercase
            "Expenses:",  # ends with colon
            "Income/Salary",  # invalid character
            ""  # empty string
        ]
        for name in invalid_names:
            assert validate_account_name(name) is False

    @pytest.mark.integration
    def test_full_journal_processing(self, sample_journal_dir, mock_subprocess_run):
        """Integration test for journal processing."""
        journal_file = sample_journal_dir / "2024.journal"
        
        # Check file
        assert check_journal_file(journal_file) is True
        
        # Run hledger commands
        result = run_hledger_command(["check", str(journal_file)])
        assert result.returncode == 0
        
        # Parse output
        entries = parse_journal_entries(mock_hledger_output())
        assert len(entries) > 0
        
        # Validate all account names
        for entry in entries:
            for posting in entry["postings"]:
                assert validate_account_name(posting["account"]) is True 