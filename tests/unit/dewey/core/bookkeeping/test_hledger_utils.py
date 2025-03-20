"""Tests for dewey.core.bookkeeping.hledger_utils."""

import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml

from dewey.core.bookkeeping.hledger_utils import HledgerUpdater, main


class TestHledgerUpdater:
    """Tests for the HledgerUpdater class."""

    @pytest.fixture
    def hledger_updater(self, mock_config: Dict[str, Any]) -> HledgerUpdater:
        """Fixture to create an instance of HledgerUpdater with a mock config."""
        with patch(
            "dewey.core.bookkeeping.hledger_utils.BaseScript.__init__", return_value=None
        ):
            with patch(
                "dewey.core.bookkeeping.hledger_utils.BaseScript.config",
                new_callable=pytest.helpers.MockConfig,
                config=mock_config,
            ):
                updater = HledgerUpdater()
                updater.logger = MagicMock()  # Mock the logger
        return updater

    def test_hledger_updater_initialization(
        self, hledger_updater: HledgerUpdater
    ) -> None:
        """Test that HledgerUpdater is initialized correctly."""
        assert hledger_updater.config_section == "bookkeeping"
        assert isinstance(hledger_updater.logger, MagicMock)

    @patch("subprocess.run")
    def test_get_balance_success(
        self,
        mock_subprocess_run: MagicMock,
        hledger_updater: HledgerUpdater,
    ) -> None:
        """Test get_balance method with a successful hledger command execution."""
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "Some header lines\n$1,234.56"
        balance = hledger_updater.get_balance(
            "assets:checking:mercury8542", "2023-12-31"
        )
        assert balance == "$1,234.56"
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run")
    def test_get_balance_no_balance_found(
        self,
        mock_subprocess_run: MagicMock,
        hledger_updater: HledgerUpdater,
    ) -> None:
        """Test get_balance method when no balance is found in the output."""
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "Some header lines\n"
        balance = hledger_updater.get_balance(
            "assets:checking:mercury8542", "2023-12-31"
        )
        assert balance is None
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run")
    def test_get_balance_hledger_error(
        self,
        mock_subprocess_run: MagicMock,
        hledger_updater: HledgerUpdater,
    ) -> None:
        """Test get_balance method when hledger command returns an error."""
        mock_subprocess_run.return_value.returncode = 1
        mock_subprocess_run.return_value.stderr = "Error message from hledger"
        balance = hledger_updater.get_balance(
            "assets:checking:mercury8542", "2023-12-31"
        )
        assert balance is None
        mock_subprocess_run.assert_called_once()
        hledger_updater.logger.error.assert_called()

    @patch("subprocess.run")
    def test_get_balance_exception(
        self,
        mock_subprocess_run: MagicMock,
        hledger_updater: HledgerUpdater,
    ) -> None:
        """Test get_balance method when an exception occurs during hledger execution."""
        mock_subprocess_run.side_effect = Exception("Some exception")
        balance = hledger_updater.get_balance(
            "assets:checking:mercury8542", "2023-12-31"
        )
        assert balance is None
        mock_subprocess_run.assert_called_once()
        hledger_updater.logger.error.assert_called()

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_update_opening_balances_success(
        self,
        mock_path_exists: MagicMock,
        mock_subprocess_run: MagicMock,
        hledger_updater: HledgerUpdater,
    ) -> None:
        """Test update_opening_balances method with successful balance retrieval and journal update."""
        # Mock successful balance retrieval
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "$1,234.56"

        # Mock file operations
        mock_path_exists.return_value = True
        mock_file = mock_open(
            read_data="""
        ; Opening balances
        2023-01-01 Opening Balances
            assets:checking:mercury8542  = $0.00
            assets:checking:mercury9281  = $0.00
        """
        )
        with patch("builtins.open", mock_file):
            hledger_updater.update_opening_balances(2023)

        # Assert that subprocess.run was called twice (once for each account)
        assert mock_subprocess_run.call_count == 2

        # Assert that the file was opened in write mode and written to
        mock_file.assert_called_with("2023.journal", "w")
        handle = mock_file()
        assert (
            "assets:checking:mercury8542  = $1,234.56" in handle.write.call_args[0][0]
        )
        assert (
            "assets:checking:mercury9281  = $1,234.56" in handle.write.call_args[0][0]
        )
        hledger_updater.logger.info.assert_called()

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_update_opening_balances_no_balances(
        self,
        mock_path_exists: MagicMock,
        mock_subprocess_run: MagicMock,
        hledger_updater: HledgerUpdater,
    ) -> None:
        """Test update_opening_balances method when balance retrieval fails."""
        # Mock failed balance retrieval
        mock_subprocess_run.return_value.returncode = 1
        mock_subprocess_run.return_value.stderr = "Error message from hledger"

        # Mock file operations
        mock_path_exists.return_value = True
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            hledger_updater.update_opening_balances(2023)

        # Assert that subprocess.run was called twice (once for each account)
        assert mock_subprocess_run.call_count == 2

        # Assert that the file was not opened in write mode
        mock_file.assert_not_called()
        hledger_updater.logger.warning.assert_called()

    @patch("pathlib.Path.exists")
    def test_update_opening_balances_journal_not_exists(
        self,
        mock_path_exists: MagicMock,
        hledger_updater: HledgerUpdater,
    ) -> None:
        """Test update_opening_balances method when the journal file does not exist."""
        # Mock Path.exists() to return False
        mock_path_exists.return_value = False
        hledger_updater.update_opening_balances(2023)

        # Assert that subprocess.run was not called
        hledger_updater.logger.warning.assert_called()

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_update_opening_balances_exception(
        self,
        mock_path_exists: MagicMock,
        mock_subprocess_run: MagicMock,
        hledger_updater: HledgerUpdater,
    ) -> None:
        """Test update_opening_balances method when an exception occurs."""
        # Mock successful balance retrieval
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "$1,234.56"

        # Mock file operations
        mock_path_exists.return_value = True
        mock_file = mock_open()

        # Mock an exception during file operations
        with patch("builtins.open", side_effect=Exception("Some exception")):
            hledger_updater.update_opening_balances(2023)

        # Assert that subprocess.run was called twice (once for each account)
        assert mock_subprocess_run.call_count == 2
        hledger_updater.logger.exception.assert_called()

    @patch("dewey.core.bookkeeping.hledger_utils.HledgerUpdater.update_opening_balances")
    def test_run(
        self,
        mock_update_opening_balances: MagicMock,
        hledger_updater: HledgerUpdater,
    ) -> None:
        """Test the run method to ensure it iterates through the years and calls update_opening_balances."""
        # Mock the update_opening_balances method
        hledger_updater.get_config_value = MagicMock(return_value=2022)
        hledger_updater.run()

        # Assert that update_opening_balances is called for each year in the range
        start_year = int(hledger_updater.get_config_value("start_year", 2022))
        current_year = datetime.now().year
        expected_calls = current_year - start_year + 2  # +1 for current year, +1 for end_year
        assert mock_update_opening_balances.call_count == expected_calls

        # Assert that update_opening_balances is called with the correct years
        for year in range(start_year, current_year + 2):
            mock_update_opening_balances.assert_any_call(year)

    @patch("dewey.core.bookkeeping.hledger_utils.HledgerUpdater.run")
    def test_main(self, mock_run: MagicMock) -> None:
        """Test the main function to ensure it creates and runs the HledgerUpdater."""
        # Call the main function
        main()

        # Assert that HledgerUpdater.run was called
        mock_run.assert_called_once()
