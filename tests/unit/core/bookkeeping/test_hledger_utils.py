"""Tests for hledger utilities."""

import os
import pytest
from unittest.mock import patch, MagicMock
from dewey.core.bookkeeping.hledger_utils import (
    get_balance,
    update_opening_balances,
    main,
)


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for testing hledger commands."""
    with patch("dewey.core.bookkeeping.hledger_utils.subprocess") as mock:
        yield mock


@pytest.fixture
def mock_path():
    """Mock Path for testing file operations."""
    with patch("dewey.core.bookkeeping.hledger_utils.Path") as mock:
        yield mock


class TestHledgerUtils:
    """Test cases for hledger utilities."""

    def test_get_balance_success(self, mock_subprocess):
        """Test successful balance retrieval."""
        # Mock successful command execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "         $1,234.56  assets:checking:mercury8542\n"
        mock_subprocess.run.return_value = mock_process

        result = get_balance("assets:checking:mercury8542", "2024-01-01")
        assert result == "$1,234.56"
        mock_subprocess.run.assert_called_once()

    def test_get_balance_command_failure(self, mock_subprocess):
        """Test balance retrieval when command fails."""
        # Mock failed command execution
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Error: Invalid account"
        mock_subprocess.run.return_value = mock_process

        result = get_balance("invalid:account", "2024-01-01")
        assert result is None
        mock_subprocess.run.assert_called_once()

    def test_get_balance_no_match(self, mock_subprocess):
        """Test balance retrieval with no matching balance in output."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "No matching transactions"
        mock_subprocess.run.return_value = mock_process

        result = get_balance("assets:checking:mercury8542", "2024-01-01")
        assert result is None
        mock_subprocess.run.assert_called_once()

    def test_get_balance_exception(self, mock_subprocess):
        """Test balance retrieval when an exception occurs."""
        mock_subprocess.run.side_effect = Exception("Command failed")

        result = get_balance("assets:checking:mercury8542", "2024-01-01")
        assert result is None
        mock_subprocess.run.assert_called_once()

    def test_update_opening_balances_success(
        self, mock_subprocess, mock_path, tmp_path
    ):
        """Test successful update of opening balances."""
        # Create a temporary journal file
        journal_content = """2024-01-01 Opening balances
    assets:checking:mercury8542  = $1,000.00
    assets:checking:mercury9281  = $2,000.00
    equity:opening balances
"""
        journal_file = tmp_path / "2024.journal"
        journal_file.write_text(journal_content)

        # Mock Path.exists() to return True
        mock_path.return_value.exists.return_value = True

        # Mock get_balance to return new values
        with patch(
            "dewey.core.bookkeeping.hledger_utils.get_balance"
        ) as mock_get_balance:
            mock_get_balance.side_effect = ["$1,500.00", "$2,500.00"]

            # Mock open to use our temporary file
            with patch("builtins.open") as mock_open:
                mock_open.side_effect = [
                    open(journal_file),  # For reading
                    open(journal_file, "w"),  # For writing
                ]

                update_opening_balances(2024)

                # Verify the file was updated with new balances
                updated_content = journal_file.read_text()
                assert "= $1,500.00" in updated_content
                assert "= $2,500.00" in updated_content

    def test_update_opening_balances_file_not_exists(self, mock_path):
        """Test update_opening_balances when journal file doesn't exist."""
        mock_path.return_value.exists.return_value = False

        # Should return without error
        update_opening_balances(2024)
        mock_path.return_value.exists.assert_called_once()

    def test_update_opening_balances_missing_balance(self, mock_path):
        """Test update_opening_balances when balance retrieval fails."""
        mock_path.return_value.exists.return_value = True

        with patch(
            "dewey.core.bookkeeping.hledger_utils.get_balance"
        ) as mock_get_balance:
            mock_get_balance.return_value = None

            # Should return without error
            update_opening_balances(2024)

    def test_main_function(self):
        """Test main function execution."""
        with patch(
            "dewey.core.bookkeeping.hledger_utils.update_opening_balances"
        ) as mock_update:
            with patch(
                "dewey.core.bookkeeping.hledger_utils.datetime"
            ) as mock_datetime:
                mock_datetime.now.return_value.year = 2024

                main()

                # Should process years from 2022 to 2025 (current year + 1)
                expected_calls = [2022, 2023, 2024, 2025]
                actual_calls = [call[0][0] for call in mock_update.call_args_list]
                assert actual_calls == expected_calls
