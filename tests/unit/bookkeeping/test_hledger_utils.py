"""Test module for hledger_utils.py."""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from dewey.core.bookkeeping.hledger_utils import (
    FileSystemInterface,
    HledgerUpdater,
    PathFileSystem,
    SubprocessRunnerInterface,
    main,
)


class MockSubprocessRunner(SubprocessRunnerInterface):
    """Mock implementation of SubprocessRunnerInterface for testing."""

    def __init__(self, results=None):
        """Initialize with predefined results."""
        self.results = results or {}
        self.call_args = []

    def __call__(
        self,
        args: list[str],
        capture_output: bool = True,
        text: bool = True,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """Mock execution of a subprocess command."""
        self.call_args.append((args, capture_output, text, check))

        # Convert args to command string for lookup
        cmd = " ".join(args) if isinstance(args, list) else args

        if cmd in self.results:
            result = self.results[cmd]
            return result

        # Default result for unknown commands
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0"
        mock_result.stderr = ""
        return mock_result


class MockFileSystem(FileSystemInterface):
    """Mock implementation of FileSystemInterface for testing."""

    def __init__(self, existing_files=None, file_contents=None):
        """Initialize with existing files and file contents."""
        self.existing_files = existing_files or set()
        self.file_contents = file_contents or {}
        self.written_content = {}

    def exists(self, path: Path | str) -> bool:
        """Check if a path exists."""
        return str(path) in self.existing_files

    def open(self, path: Path | str, mode: str = "r") -> MagicMock:
        """Mock open a file."""
        path_str = str(path)

        if "w" in mode and path_str not in self.written_content:
            # Track writes to files
            m = mock_open()
            handle = m(path_str, mode)
            handle.write.side_effect = lambda data: self.written_content.update(
                {path_str: data}
            )
            return handle

        if "r" in mode and path_str not in self.file_contents:
            raise FileNotFoundError(f"File not found: {path_str}")

        # For reading existing files
        content = self.file_contents.get(path_str, "")
        return mock_open(read_data=content)(path_str, mode)


@pytest.fixture
def mock_subprocess():
    """Fixture providing a mock subprocess runner."""
    mercury8542_result = MagicMock()
    mercury8542_result.returncode = 0
    mercury8542_result.stdout = "             $10,000.00  assets:checking:mercury8542\n--------------------\n             $10,000.00"

    mercury9281_result = MagicMock()
    mercury9281_result.returncode = 0
    mercury9281_result.stdout = "              $5,000.00  assets:checking:mercury9281\n--------------------\n              $5,000.00"

    error_result = MagicMock()
    error_result.returncode = 1
    error_result.stderr = "Error: Unknown account"

    return MockSubprocessRunner(
        {
            "hledger -f all.journal bal assets:checking:mercury8542 -e 2022-12-31 --depth 1": mercury8542_result,
            "hledger -f all.journal bal assets:checking:mercury9281 -e 2022-12-31 --depth 1": mercury9281_result,
            "hledger -f all.journal bal assets:checking:error -e 2022-12-31 --depth 1": error_result,
        }
    )


@pytest.fixture
def mock_fs():
    """Fixture providing a mock file system."""
    return MockFileSystem(
        existing_files={"2023.journal", "2024.journal"},
        file_contents={
            "2023.journal": """
2023-01-01 Opening Balances
    assets:checking:mercury8542    = $9,500.00
    assets:checking:mercury9281    = $4,500.00
    equity:opening balances
"""
        },
    )


@pytest.fixture
def updater(mock_subprocess, mock_fs):
    """Fixture providing a HledgerUpdater with mock dependencies."""
    return HledgerUpdater(subprocess_runner=mock_subprocess, fs=mock_fs)


class TestPathFileSystem:
    """Tests for the PathFileSystem class."""

    def test_exists(self):
        """Test exists method."""
        fs = PathFileSystem()
        with patch("pathlib.Path.exists", return_value=True):
            assert fs.exists("test_path") is True

    def test_open(self):
        """Test open method."""
        fs = PathFileSystem()
        with patch("builtins.open", mock_open(read_data="test content")):
            f = fs.open("test_path")
            assert f.read() == "test content"


class TestHledgerUpdater:
    """Tests for the HledgerUpdater class."""

    def test_init(self):
        """Test initialization of HledgerUpdater."""
        # Test with default values
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            updater = HledgerUpdater()
            assert updater._subprocess_runner is not None
            assert updater._fs is not None
            assert isinstance(updater._fs, PathFileSystem)

        # Test with mock dependencies
        mock_subprocess = MockSubprocessRunner()
        mock_fs = MockFileSystem()

        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            updater = HledgerUpdater(subprocess_runner=mock_subprocess, fs=mock_fs)
            assert updater._subprocess_runner == mock_subprocess
            assert updater._fs == mock_fs

    def test_get_balance_success(self, updater):
        """Test successful retrieval of balance."""
        balance = updater.get_balance("assets:checking:mercury8542", "2022-12-31")

        assert balance == "$10,000.00"
        assert len(updater._subprocess_runner.call_args) == 1

        # Verify the command that was run
        args = updater._subprocess_runner.call_args[0][0]
        assert args[0] == "hledger"
        assert "-f" in args
        assert "bal" in args
        assert "assets:checking:mercury8542" in args
        assert "-e" in args
        assert "2022-12-31" in args

    def test_get_balance_error(self, updater):
        """Test error handling in get_balance."""
        # Reset call_args before this test to isolate it from previous tests
        updater._subprocess_runner.call_args = []

        balance = updater.get_balance("assets:checking:error", "2022-12-31")

        assert balance is None
        assert (
            len(updater._subprocess_runner.call_args) == 1
        )  # Only count calls in this test

    def test_get_balance_exception(self, updater):
        """Test exception handling in get_balance."""

        # Make subprocess_runner raise an exception
        def raise_exception(*args, **kwargs):
            raise Exception("Subprocess error")

        updater._subprocess_runner = raise_exception

        balance = updater.get_balance("assets:checking:mercury8542", "2022-12-31")

        assert balance is None

    def test_read_journal_file(self, updater):
        """Test reading journal file."""
        content = updater._read_journal_file("2023.journal")

        assert "Opening Balances" in content
        assert "assets:checking:mercury8542" in content
        assert "= $9,500.00" in content

    def test_write_journal_file(self, updater):
        """Test writing journal file."""
        new_content = "New journal content"
        updater._write_journal_file("2023.journal", new_content)

        assert "2023.journal" in updater._fs.written_content
        assert updater._fs.written_content["2023.journal"] == new_content

    def test_update_opening_balances_success(self, updater):
        """Test successful update of opening balances."""
        updater.update_opening_balances(2023)

        # Check that the journal file was updated
        assert "2023.journal" in updater._fs.written_content
        updated_content = updater._fs.written_content["2023.journal"]

        # Verify the updated balances
        assert "assets:checking:mercury8542    = $10,000.00" in updated_content
        assert "assets:checking:mercury9281    = $5,000.00" in updated_content

    def test_update_opening_balances_missing_journal(self, updater):
        """Test handling of missing journal file."""
        # Try to update a year without a journal file
        updater.update_opening_balances(2025)

        # Verify no files were written
        assert "2025.journal" not in updater._fs.written_content

    def test_update_opening_balances_missing_balance(self, updater):
        """Test handling of missing balance information."""
        # Make get_balance return None
        with patch.object(updater, "get_balance", return_value=None):
            updater.update_opening_balances(2023)

        # Verify no files were written
        assert "2023.journal" not in updater._fs.written_content

    def test_update_opening_balances_exception(self, updater):
        """Test exception handling in update_opening_balances."""
        # Make _read_journal_file raise an exception
        with patch.object(
            updater, "_read_journal_file", side_effect=Exception("Read error")
        ):
            updater.update_opening_balances(2023)

        # Verify no files were written
        assert "2023.journal" not in updater._fs.written_content

    def test_run(self, updater):
        """Test the run method."""
        # Mock datetime to control current year
        with patch("dewey.core.bookkeeping.hledger_utils.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1)

            # Mock get_config_value to control start_year
            with patch.object(updater, "get_config_value", return_value="2022"):
                # Mock update_opening_balances to track calls
                with patch.object(updater, "update_opening_balances") as mock_update:
                    updater.run()

                    # Should process years 2022, 2023, and 2024
                    assert mock_update.call_count == 3
                    mock_update.assert_any_call(2022)
                    mock_update.assert_any_call(2023)
                    mock_update.assert_any_call(2024)

    @patch("dewey.core.bookkeeping.hledger_utils.HledgerUpdater")
    def test_main(self, mock_updater_class):
        """Test the main function."""
        mock_instance = MagicMock()
        mock_updater_class.return_value = mock_instance

        main()

        mock_updater_class.assert_called_once()
        mock_instance.run.assert_called_once()
