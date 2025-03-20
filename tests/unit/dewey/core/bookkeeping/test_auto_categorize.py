"""Tests for dewey.core.bookkeeping.auto_categorize."""

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.auto_categorize import (
    FileSystemInterface,
    JournalProcessor,
    RuleLoaderInterface,
)


class MockFileSystem:
    """Mock implementation of the FileSystemInterface."""

    def __init__(self, files: Dict[Path, str] = {}) -> None:
        """Initializes the MockFileSystem with a dictionary of files."""
        self.files = files
        self.copied: List[Tuple[Path, Path]] = []
        self.moved: List[Tuple[Path, Path]] = []
        self.written: Dict[Path, str] = {}
        self.exists_values: Dict[Path, bool] = {}

    def open(self, path: Path, mode: str = "r") -> Any:
        """Mocks opening a file."""
        if mode == "r":
            if path not in self.files:
                raise FileNotFoundError(f"File not found: {path}")
            return mock_open(read_data=self.files[path]).return_value
        elif mode == "w":
            return self._mock_file_writer(path)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    def copy2(self, src: Path, dst: Path) -> None:
        """Mocks copying a file."""
        if src not in self.files:
            raise FileNotFoundError(f"Source file not found: {src}")
        self.copied.append((src, dst))

    def move(self, src: Path, dst: Path) -> None:
        """Mocks moving a file."""
        if src not in self.files:
            raise FileNotFoundError(f"Source file not found: {src}")
        self.moved.append((src, dst))

    def exists(self, path: Path) -> bool:
        """Mocks checking if a file exists."""
        return self.exists_values.get(path, path in self.files)

    def _mock_file_writer(self, path: Path) -> Any:
        """Returns a mock file writer that records written content."""
        mock_file = MagicMock()
        def write(content: str) -> None:
            self.written[path] = content
        mock_file.write = write
        return mock_file


class MockRuleLoader:
    """Mock implementation of the RuleLoaderInterface."""

    def __init__(self, rules: Dict) -> None:
        """Initializes the MockRuleLoader with a dictionary of rules."""
        self.rules = rules

    def load_rules(self) -> Dict:
        """Mocks loading rules."""
        return self.rules


@pytest.fixture
def mock_base_script() -> MagicMock:
    """Mock BaseScript instance."""
    mock_script = MagicMock(spec=BaseScript)
    mock_script.get_config_value.side_effect = lambda key, default=None: {
        "classification_file": "/path/to/classification_rules.json",
        "ledger_file": "/path/to/ledger.journal",
        "backup_ext": ".bak",
    }.get(key, default)
    mock_script.logger = MagicMock()
    mock_script.PROJECT_ROOT = Path("/project/root")  # Set PROJECT_ROOT
    return mock_script


@pytest.fixture
def journal_processor(mock_base_script: MagicMock) -> JournalProcessor:
    """Fixture to create a JournalProcessor instance with mocked dependencies."""
    with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
        processor = JournalProcessor()
        processor.config = {
            "bookkeeping": {
                "classification_file": "/path/to/classification_rules.json",
                "ledger_file": "/path/to/ledger.journal",
                "backup_ext": ".bak",
            }
        }
        processor.logger = mock_base_script.logger
        processor.classification_file = Path("/path/to/classification_rules.json")
        processor.ledger_file = Path("/path/to/ledger.journal")
        processor.backup_ext = ".bak"
        processor.PROJECT_ROOT = Path("/project/root")  # Set PROJECT_ROOT
        return processor


def create_journal_file(file_path: Path, content: str) -> None:
    """Helper function to create a journal file with the given content."""
    with open(file_path, "w") as f:
        f.write(content)


def create_classification_file(file_path: Path, content: Dict) -> None:
    """Helper function to create a classification file with the given content."""
    with open(file_path, "w") as f:
        json.dump(content, f)


class TestJournalProcessor:
    """Comprehensive test suite for the JournalProcessor class."""

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_init(self, mock_init: MagicMock, journal_processor: JournalProcessor) -> None:
        """Test the initialization of the JournalProcessor."""
        assert journal_processor.rule_sources == [
            ("overrides.json", 0),
            ("manual_rules.json", 1),
            ("base_rules.json", 2),
        ]
        assert journal_processor.classification_file == Path("/path/to/classification_rules.json")
        assert journal_processor.ledger_file == Path("/path/to/ledger.journal")
        assert journal_processor.backup_ext == ".bak"
        assert isinstance(journal_processor.logger, MagicMock)

    def test_load_classification_rules(self, journal_processor: JournalProcessor) -> None:
        """Test loading classification rules."""
        journal_processor.logger.info = MagicMock()
        rules = {"rule1": "value1"}
        rule_loader = MockRuleLoader(rules)
        journal_processor.rule_loader = rule_loader
        loaded_rules = journal_processor.load_classification_rules()
        assert loaded_rules == rules
        journal_processor.logger.info.assert_called_once_with("Loading classification rules")

    def test_process_transactions(self, journal_processor: JournalProcessor) -> None:
        """Test processing transactions (currently a placeholder)."""
        transactions: List[Dict] = [{"description": "Test transaction"}]
        rules: Dict = {}
        journal_processor.logger.info = MagicMock()
        processed_transactions = journal_processor.process_transactions(transactions, rules)
        assert processed_transactions == transactions
        journal_processor.logger.info.assert_called_once_with("Processing transactions")

    @pytest.mark.parametrize(
        "journal_content, expected_transactions",
        [
            (
                """
                2023-01-01 Description 1
                    Account1  100
                    Account2  -100

                2023-01-02 Description 2
                    Account3  50
                    Account4  -50
                """,
                [
                    {
                        "date": "2023-01-01",
                        "description": "Description 1",
                        "postings": [
                            {"account": "Account1", "amount": "100"},
                            {"account": "Account2", "amount": "-100"},
                        ],
                    },
                    {
                        "date": "2023-01-02",
                        "description": "Description 2",
                        "postings": [
                            {"account": "Account3", "amount": "50"},
                            {"account": "Account4", "amount": "-50"},
                        ],
                    },
                ],
            ),
            (
                """
                2023-01-03 Description 3
                    Account5
                    Account6
                """,
                [
                    {
                        "date": "2023-01-03",
                        "description": "Description 3",
                        "postings": [
                            {"account": "Account5", "amount": ""},
                            {"account": "Account6", "amount": ""},
                        ],
                    },
                ],
            ),
            ("", []),
            (
                """
                2023-01-04 Description 4
                """,
                [
                    {
                        "date": "2023-01-04",
                        "description": "Description 4",
                        "postings": [],
                    },
                ],
            ),
        ],
    )
    def test_parse_journal_entries(
        self,
        journal_processor: JournalProcessor,
        journal_content: str,
        expected_transactions: List[Dict[str, Any]],
    ) -> None:
        """Test parsing journal entries from a file."""
        ledger_file = Path("/path/to/ledger.journal")
        mock_fs = MockFileSystem({ledger_file: journal_content})
        journal_processor.file_system = mock_fs
        journal_processor.logger.info = MagicMock()
        transactions = journal_processor.parse_journal_entries(ledger_file)
        assert transactions == expected_transactions
        journal_processor.logger.info.assert_called_with(f"Parsing journal file: {ledger_file}")
        journal_processor.logger.info.assert_called_with(f"Found {len(transactions)} transactions")

    def test_serialize_transactions(self) -> None:
        """Test serializing transactions back to journal format."""
        transactions = [
            {
                "date": "2023-01-01",
                "description": "Description 1",
                "postings": [
                    {"account": "Account1", "amount": "100"},
                    {"account": "Account2", "amount": "-100"},
                ],
            }
        ]
        expected_output = """2023-01-01 Description 1
    Account1  100
    Account2  -100
"""
        processor = JournalProcessor()  # Need to instantiate without tmp_path
        processor.logger = MagicMock()
        output = processor.serialize_transactions(transactions)
        assert output == expected_output

    def test_write_journal_file(self, journal_processor: JournalProcessor) -> None:
        """Test writing the journal file with backup."""
        ledger_file = Path("/path/to/ledger.journal")
        backup_file = Path("/path/to/ledger.journal.bak")
        content = "Updated journal content"
        mock_fs = MockFileSystem({ledger_file: "Original journal content"})
        journal_processor.file_system = mock_fs
        journal_processor.logger.info = MagicMock()

        journal_processor.write_journal_file(content, ledger_file)

        assert mock_fs.copied == [(ledger_file, backup_file)]
        assert mock_fs.written[ledger_file] == content
        journal_processor.logger.info.assert_any_call(f"Creating backup at {backup_file}")
        journal_processor.logger.info.assert_any_call(f"Writing updated journal to {ledger_file}")

    def test_write_journal_file_exception(self, journal_processor: JournalProcessor) -> None:
        """Test handling exceptions during journal file writing."""
        ledger_file = Path("/path/to/ledger.journal")
        backup_file = Path("/path/to/ledger.journal.bak")
        content = "Updated journal content"
        mock_fs = MockFileSystem({ledger_file: "Original journal content"})
        mock_fs.copy2 = MagicMock(side_effect=Exception("Copy failed"))
        mock_fs.exists_values[backup_file] = True
        mock_fs.move = MagicMock()
        journal_processor.file_system = mock_fs
        journal_processor.logger.exception = MagicMock()
        journal_processor.logger.info = MagicMock()

        with pytest.raises(Exception, match="Copy failed"):
            journal_processor.write_journal_file(content, ledger_file)

        assert mock_fs.moved == [(backup_file, ledger_file)]
        journal_processor.logger.exception.assert_called_once()
        journal_processor.logger.info.assert_called_with("Restoring from backup")

    def test_write_journal_file_exception_no_backup(self, journal_processor: JournalProcessor) -> None:
        """Test handling exceptions during journal file writing when backup fails."""
        ledger_file = Path("/path/to/ledger.journal")
        backup_file = Path("/path/to/ledger.journal.bak")
        content = "Updated journal content"
        mock_fs = MockFileSystem({ledger_file: "Original journal content"})
        mock_fs.copy2 = MagicMock(side_effect=Exception("Copy failed"))
        mock_fs.exists_values[backup_file] = False
        mock_fs.move = MagicMock()
        journal_processor.file_system = mock_fs
        journal_processor.logger.exception = MagicMock()
        journal_processor.logger.info = MagicMock()

        with pytest.raises(Exception, match="Copy failed"):
            journal_processor.write_journal_file(content, ledger_file)

        assert mock_fs.moved == []
        journal_processor.logger.exception.assert_called_once()

    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.load_classification_rules")
    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.parse_journal_entries")
    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.process_transactions")
    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.serialize_transactions")
    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.write_journal_file")
    def test_run(
        self,
        mock_write_journal_file: MagicMock,
        mock_serialize_transactions: MagicMock,
        mock_process_transactions: MagicMock,
        mock_parse_journal_entries: MagicMock,
        mock_load_classification_rules: MagicMock,
        journal_processor: JournalProcessor,
    ) -> None:
        """Test the main run method."""
        ledger_file = Path("/path/to/ledger.journal")

        # Mock the return values of the methods
        mock_load_classification_rules.return_value = {}
        mock_parse_journal_entries.return_value = [
            {
                "date": "2023-01-01",
                "description": "Test Transaction",
                "postings": [
                    {"account": "Account1", "amount": "100"},
                    {"account": "Account2", "amount": "-100"},
                ],
            }
        ]
        mock_process_transactions.return_value = [
            {
                "date": "2023-01-01",
                "description": "Test Transaction",
                "postings": [
                    {"account": "Account1", "amount": "100"},
                    {"account": "Account2", "amount": "-100"},
                ],
            }
        ]
        mock_serialize_transactions.return_value = """2023-01-01 Test Transaction
    Account1  100
    Account2  -100
"""
        journal_processor.logger.info = MagicMock()

        journal_processor.run()

        # Assert that the methods were called
        mock_load_classification_rules.assert_called_once()
        mock_parse_journal_entries.assert_called_once_with(ledger_file)
        mock_process_transactions.assert_called_once()
        mock_serialize_transactions.assert_called_once()
        mock_write_journal_file.assert_called_once()
        journal_processor.logger.info.assert_called_with("Successfully updated journal entries")

    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.parse_journal_entries")
    def test_run_exception(self, mock_parse_journal_entries: MagicMock, journal_processor: JournalProcessor) -> None:
        """Test handling exceptions in the main run method."""
        # Mock the parse_journal_entries method to raise an exception
        mock_parse_journal_entries.side_effect = Exception("Parsing failed")
        journal_processor.logger.exception = MagicMock()

        with pytest.raises(Exception, match="Parsing failed"):
            journal_processor.run()

        # Assert that the exception was logged
        journal_processor.logger.exception.assert_called_once()

    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.run")
    def test_execute(self, mock_run: MagicMock, journal_processor: JournalProcessor, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method."""
        with caplog.at_level(logging.INFO):
            journal_processor.execute()
            assert mock_run.called
            assert "Starting execution of JournalProcessor" in caplog.text
            assert "Completed execution of JournalProcessor" in caplog.text

    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.parse_args")
    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.run", side_effect=KeyboardInterrupt)
    def test_execute_keyboard_interrupt(
        self, mock_run: MagicMock, mock_parse_args: MagicMock, journal_processor: JournalProcessor, capsys: pytest.CaptureFixture
    ) -> None:
        """Test handling KeyboardInterrupt in the execute method."""
        with pytest.raises(SystemExit) as excinfo:
            journal_processor.execute()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Script interrupted by user" in captured.err

    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.parse_args")
    @patch("dewey.core.bookkeeping.auto_categorize.JournalProcessor.run", side_effect=ValueError("Test Error"))
    def test_execute_exception(
        self, mock_run: MagicMock, mock_parse_args: MagicMock, journal_processor: JournalProcessor, capsys: pytest.CaptureFixture
    ) -> None:
        """Test handling exceptions in the execute method."""
        with pytest.raises(SystemExit) as excinfo:
            journal_processor.execute()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error executing script: Test Error" in captured.err

    def test_cleanup(self, journal_processor: JournalProcessor) -> None:
        """Test the cleanup method."""
        # Mock a database connection
        journal_processor.db_conn = MagicMock()
        journal_processor.logger.debug = MagicMock()

        journal_processor._cleanup()

        # Assert that the database connection was closed
        journal_processor.db_conn.close.assert_called_once()
        journal_processor.logger.debug.assert_called_with("Closing database connection")

    def test_cleanup_exception(self, journal_processor: JournalProcessor) -> None:
        """Test handling exceptions in the cleanup method."""
        # Mock a database connection that raises an exception when closed
        journal_processor.db_conn = MagicMock()
        journal_processor.db_conn.close.side_effect = Exception("Close failed")
        journal_processor.logger.warning = MagicMock()

        journal_processor._cleanup()

        # Assert that the exception was logged
        journal_processor.logger.warning.assert_called_once()

    def test_get_path_absolute(self, journal_processor: JournalProcessor) -> None:
        """Test getting an absolute path."""
        absolute_path = "/absolute/path"
        path = journal_processor.get_path(absolute_path)
        assert path == Path(absolute_path)

    def test_get_path_relative(self, journal_processor: JournalProcessor) -> None:
        """Test getting a relative path."""
        relative_path = "relative/path"
        path = journal_processor.get_path(relative_path)
        assert path == journal_processor.PROJECT_ROOT / relative_path

    def test_get_config_value(self, journal_processor: JournalProcessor) -> None:
        """Test getting a configuration value."""
        # Assuming the config has a value "llm.model"
        journal_processor.config = {"llm": {"model": "test_model"}}
        value = journal_processor.get_config_value("llm.model")
        assert value == "test_model"

    def test_get_config_value_default(self, journal_processor: JournalProcessor) -> None:
        """Test getting a configuration value with a default."""
        value = journal_processor.get_config_value("nonexistent.key", "default_value")
        assert value == "default_value"

    def test_get_config_value_nested(self, journal_processor: JournalProcessor) -> None:
        """Test getting a nested configuration value."""
        journal_processor.config = {"level1": {"level2": {"value": "nested_value"}}}
        value = journal_processor.get_config_value("level1.level2.value")
        assert value == "nested_value"

    def test_get_config_value_missing_level(self, journal_processor: JournalProcessor) -> None:
        """Test getting a configuration value when a level is missing."""
        journal_processor.config = {"level1": {"level2": {"value": "nested_value"}}}
        value = journal_processor.get_config_value("level1.missing.value", "default_value")
        assert value == "default_value"

    @patch("dewey.core.bookkeeping.auto_categorize.CONFIG_PATH", "mocked_config_path")
    @patch("builtins.open", new_callable=mock_open, read_data="""core:
  logging:
    level: DEBUG
    format: '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    date_format: '%Y-%m-%d %H:%M:%S'""")
    def test_setup_logging_from_config(self, mock_open_config: MagicMock, journal_processor: JournalProcessor) -> None:
        """Test setting up logging from the configuration file."""
        # Re-initialize the JournalProcessor to apply the new config
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            journal_processor = JournalProcessor()

            # Assert that the logging level and format are set correctly
            assert journal_processor.logger.level == logging.DEBUG
            # Check if any handler exists and has the correct formatter
            if hasattr(journal_processor.logger, 'handlers') and journal_processor.logger.handlers:
                assert journal_processor.logger.handlers[0].formatter._fmt == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            else:
                pytest.fail("No logging handlers found")

    @patch("dewey.core.bookkeeping.auto_categorize.CONFIG_PATH", "mocked_config_path")
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    def test_setup_logging_default(self, mock_open_config: MagicMock, journal_processor: JournalProcessor) -> None:
        """Test setting up logging with default values when config is missing."""
        # Re-initialize the JournalProcessor to apply the new config
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            journal_processor = JournalProcessor()

            # Assert that the logging level and format are set to default values
            assert journal_processor.logger.level == logging.INFO
            # Check if any handler exists and has the correct formatter
            if hasattr(journal_processor.logger, 'handlers') and journal_processor.logger.handlers:
                assert journal_processor.logger.handlers[0].formatter._fmt == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            else:
                pytest.fail("No logging handlers found")

    @patch("dewey.core.bookkeeping.auto_categorize.CONFIG_PATH", "mocked_config_path")
    @patch("builtins.open", new_callable=mock_open, read_data="invalid yaml")
    def test_setup_logging_config_error(self, mock_open_config: MagicMock, journal_processor: JournalProcessor) -> None:
        """Test setting up logging when the config file is invalid."""
        # Re-initialize the JournalProcessor to apply the new config
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            journal_processor = JournalProcessor()

            # Assert that the logging level and format are set to default values
            assert journal_processor.logger.level == logging.INFO
            # Check if any handler exists and has the correct formatter
            if hasattr(journal_processor.logger, 'handlers') and journal_processor.logger.handlers:
                assert journal_processor.logger.handlers[0].formatter._fmt == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            else:
                pytest.fail("No logging handlers found")

    @pytest.mark.parametrize(
        "line, current_tx, expected_tx",
        [
            (
                "2024-01-01 Description",
                {"postings": []},
                {"date": "2024-01-01", "description": "Description", "postings": []},
            ),
            (
                "    Account1  100",
                {"date": "2024-01-01", "description": "Description", "postings": []},
                {
                    "date": "2024-01-01",
                    "description": "Description",
                    "postings": [{"account": "Account1", "amount": "100"}],
                },
            ),
        ],
    )
    def test__parse_journal_entry(
        self, journal_processor: JournalProcessor, line: str, current_tx: Dict[str, Any], expected_tx: Dict[str, Any]
    ) -> None:
        """Test the _parse_journal_entry method."""
        journal_processor._parse_journal_entry(line, current_tx)
        assert current_tx == expected_tx
