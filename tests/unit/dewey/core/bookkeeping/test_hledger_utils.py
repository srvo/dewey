import logging
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.bookkeeping.hledger_utils import HledgerUpdater


@pytest.fixture
def hledger_updater(tmp_path: Path) -> HledgerUpdater:
    """Fixture to create an instance of HledgerUpdater with a temporary config file."""
    # Create a temporary config file
    config_data = {
        'bookkeeping': {
            'start_year': 2022,
        },
        'logging': {
            'level': 'DEBUG',
            'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            'date_format': '%Y-%m-%d %H:%M:%S',
        }
    }
    config_file = tmp_path / 'config.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Patch the CONFIG_PATH to point to the temporary config file
    with patch('dewey.core.bookkeeping.hledger_utils.CONFIG_PATH', config_file):
        updater = HledgerUpdater()
    return updater


@pytest.fixture
def mock_subprocess_run() -> MagicMock:
    """Fixture to mock subprocess.run."""
    with patch('dewey.core.bookkeeping.hledger_utils.subprocess.run') as mock:
        yield mock


def test_hledger_updater_initialization(hledger_updater: HledgerUpdater) -> None:
    """Test that HledgerUpdater is initialized correctly."""
    assert hledger_updater.config_section == 'bookkeeping'
    assert isinstance(hledger_updater.logger, logging.Logger)


def test_get_balance_success(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock) -> None:
    """Test get_balance method with a successful hledger command execution."""
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stdout = "Some header lines\n$1,234.56"
    balance = hledger_updater.get_balance("assets:checking:mercury8542", "2023-12-31")
    assert balance == "$1,234.56"
    mock_subprocess_run.assert_called_once()


def test_get_balance_no_balance_found(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock) -> None:
    """Test get_balance method when no balance is found in the output."""
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stdout = "Some header lines\n"
    balance = hledger_updater.get_balance("assets:checking:mercury8542", "2023-12-31")
    assert balance is None
    mock_subprocess_run.assert_called_once()


def test_get_balance_hledger_error(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock) -> None:
    """Test get_balance method when hledger command returns an error."""
    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stderr = "Error message from hledger"
    balance = hledger_updater.get_balance("assets:checking:mercury8542", "2023-12-31")
    assert balance is None
    mock_subprocess_run.assert_called_once()


def test_get_balance_exception(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock) -> None:
    """Test get_balance method when an exception occurs during hledger execution."""
    mock_subprocess_run.side_effect = Exception("Some exception")
    balance = hledger_updater.get_balance("assets:checking:mercury8542", "2023-12-31")
    assert balance is None
    mock_subprocess_run.assert_called_once()


def test_update_opening_balances_success(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock, tmp_path: Path) -> None:
    """Test update_opening_balances method with successful balance retrieval and journal update."""
    # Mock successful balance retrieval
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stdout = "$1,234.56"

    # Create a dummy journal file
    journal_content = """
    ; Opening balances
    2023-01-01 Opening Balances
        assets:checking:mercury8542  = $0.00
        assets:checking:mercury9281  = $0.00
    """
    journal_file = tmp_path / "2023.journal"
    with open(journal_file, "w") as f:
        f.write(journal_content)

    # Patch Path.exists() to return True for the journal file
    with patch("pathlib.Path.exists", return_value=True):
        hledger_updater.update_opening_balances(2023)

    # Assert that subprocess.run was called twice (once for each account)
    assert mock_subprocess_run.call_count == 2

    # Assert that the journal file was updated with the new balances
    with open(journal_file, "r") as f:
        updated_content = f.read()
        assert "assets:checking:mercury8542  = $1,234.56" in updated_content
        assert "assets:checking:mercury9281  = $1,234.56" in updated_content


def test_update_opening_balances_no_balances(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock, tmp_path: Path) -> None:
    """Test update_opening_balances method when balance retrieval fails."""
    # Mock failed balance retrieval
    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stderr = "Error message from hledger"

    # Create a dummy journal file
    journal_file = tmp_path / "2023.journal"
    with open(journal_file, "w") as f:
        f.write("Dummy journal content")

    # Patch Path.exists() to return True for the journal file
    with patch("pathlib.Path.exists", return_value=True):
        hledger_updater.update_opening_balances(2023)

    # Assert that subprocess.run was called twice (once for each account)
    assert mock_subprocess_run.call_count == 2

    # Assert that the journal file was not modified
    with open(journal_file, "r") as f:
        content = f.read()
        assert content == "Dummy journal content"


def test_update_opening_balances_journal_not_exists(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock, tmp_path: Path) -> None:
    """Test update_opening_balances method when the journal file does not exist."""
    # Mock Path.exists() to return False
    with patch("pathlib.Path.exists", return_value=False):
        hledger_updater.update_opening_balances(2023)

    # Assert that subprocess.run was not called
    mock_subprocess_run.assert_not_called()


def test_update_opening_balances_exception(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock, tmp_path: Path) -> None:
    """Test update_opening_balances method when an exception occurs."""
    # Mock successful balance retrieval
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stdout = "$1,234.56"

    # Create a dummy journal file
    journal_file = tmp_path / "2023.journal"
    with open(journal_file, "w") as f:
        f.write("Dummy journal content")

    # Mock an exception during file operations
    with patch("pathlib.Path.exists", return_value=True), \
            patch("builtins.open", side_effect=Exception("Some exception")):
        hledger_updater.update_opening_balances(2023)

    # Assert that subprocess.run was called twice (once for each account)
    assert mock_subprocess_run.call_count == 2


def test_run(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock, tmp_path: Path) -> None:
    """Test the run method to ensure it iterates through the years and calls update_opening_balances."""
    # Mock the update_opening_balances method
    with patch.object(HledgerUpdater, 'update_opening_balances') as mock_update:
        hledger_updater.run()

        # Assert that update_opening_balances is called for each year in the range
        start_year = int(hledger_updater.get_config_value("start_year", 2022))
        current_year = datetime.now().year
        expected_calls = current_year - start_year + 2  # +1 for current year, +1 for end_year
        assert mock_update.call_count == expected_calls

        # Assert that update_opening_balances is called with the correct years
        for year in range(start_year, current_year + 2):
            mock_update.assert_any_call(year)


def test_main(hledger_updater: HledgerUpdater, mock_subprocess_run: MagicMock, tmp_path: Path) -> None:
    """Test the main function to ensure it creates and runs the HledgerUpdater."""
    # Mock the HledgerUpdater.run method
    with patch.object(HledgerUpdater, 'run') as mock_run:
        # Call the main function
from dewey.core.bookkeeping.hledger_utils import main
        main()

        # Assert that HledgerUpdater.run was called
        mock_run.assert_called_once()
