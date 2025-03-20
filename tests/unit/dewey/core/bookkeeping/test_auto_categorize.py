import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.bookkeeping.auto_categorize import JournalProcessor


@pytest.fixture
def journal_processor(tmp_path: Path) -> JournalProcessor:
    """Fixture to create a JournalProcessor instance with a temporary directory."""
    # Create dummy config file
    config_path = tmp_path / "dewey.yaml"
    with open(config_path, "w") as f:
        yaml.dump({
            'bookkeeping': {
                'classification_file': str(tmp_path / "classification_rules.json"),
                'ledger_file': str(tmp_path / "ledger.journal"),
                'backup_ext': ".bak"
            },
            'logging': {
                'level': 'DEBUG',
                'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                'date_format': '%Y-%m-%d %H:%M:%S'
            }
        }, f)

    # Patch the CONFIG_PATH to point to the temporary config file
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        processor = JournalProcessor()
        processor.ledger_file = tmp_path / "ledger.journal"
        processor.classification_file = tmp_path / "classification_rules.json"
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

    def test_init(self, journal_processor: JournalProcessor) -> None:
        """Test the initialization of the JournalProcessor."""
        assert journal_processor.rule_sources == [
            ("overrides.json", 0), ("manual_rules.json", 1), ("base_rules.json", 2), ]
        assert isinstance(journal_processor.classification_file, Path)
        assert isinstance(journal_processor.ledger_file, Path)
        assert journal_processor.backup_ext == ".bak"
        assert isinstance(journal_processor.logger, logging.Logger)

    def test_load_classification_rules(self, journal_processor: JournalProcessor) -> None:
        """Test loading classification rules (currently a placeholder)."""
        rules = journal_processor.load_classification_rules()
        assert isinstance(rules, dict)
        assert not rules

    def test_process_transactions(self, journal_processor: JournalProcessor) -> None:
        """Test processing transactions (currently a placeholder)."""
        transactions=None, rules)
        assert processed_transactions == transactions

    @pytest.mark.parametrize(
        "journal_content, expected_transactions", [
            (
                """
                2023-01-01 Description 1
                    Account1  100
                    Account2  -100

                2023-01-02 Description 2
                    Account3  50
                    Account4  -50
                """, [
                    {
                        "date": "2023-01-01", "description": "Description 1", "postings": [
                            {"account": "Account1", "amount": "100"}, {"account": "Account2", "amount": "-100"}, ], }, {
                        "date": "2023-01-02", "description": "Description 2", "postings": [
                            {"account": "Account3", "amount": "50"}, {"account": "Account4", "amount": "-50"}, ], }, ], ), (
                """
                2023-01-03 Description 3
                    Account5
                    Account6
                """, [
                    {
                        "date": "2023-01-03", "description": "Description 3", "postings": [
                            {"account": "Account5", "amount": ""}, {"account": "Account6", "amount": ""}, ], }, ], ), (
                "", [], ), (
                """
                2023-01-04 Description 4
                """, [
                    {
                        "date": "2023-01-04", "description": "Description 4", "postings": [], }, ], ), ], )
    def test_parse_journal_entries(
        self, journal_processor: JournalProcessor, tmp_path: Path, journal_content: str, expected_transactions: List[Dict[str, Any]]
    ) -> None:
        """Test parsing journal entries from a file."""
        ledger_file = tmp_path / "ledger.journal"
        create_journal_file(ledger_file, journal_content)
        transactions = journal_processor.parse_journal_entries(ledger_file)
        assert transactions == expected_transactions

    def test_serialize_transactions(self) -> None:
        """Test serializing transactions back to journal format."""
        transactions = [
            {
                "date": "2023-01-01", "description": "Description 1", "postings": [
                    {"account": "Account1", "amount": "100"}, {"account": "Account2", "amount": "-100"}, ], }
        ]
        expected_output = """2023-01-01 Description 1
    Account1  100
    Account2  -100"""
        processor = JournalProcessor()  # Need to instantiate without tmp_path
        output = processor.serialize_transactions(transactions)
        assert output == expected_output

    def test_write_journal_file(self, journal_processor: JournalProcessor, tmp_path: Path) -> None:
        """Test writing the journal file with backup."""
        ledger_file = tmp_path / "ledger.journal"
        backup_ext = journal_processor.backup_ext
        backup_file = ledger_file.with_suffix(f".{backup_ext}")
        content = "Updated journal content"

        create_journal_file(ledger_file, "Original journal content")
        journal_processor.write_journal_file(content, ledger_file)

        assert ledger_file.exists()
        assert backup_file.exists()
        assert ledger_file.read_text() == content
        assert backup_file.read_text() == "Original journal content"

    def test_write_journal_file_exception(self, journal_processor: JournalProcessor, tmp_path: Path) -> None:
        """Test handling exceptions during journal file writing."""
        ledger_file = tmp_path / "ledger.journal"
        backup_ext = journal_processor.backup_ext
        backup_file = ledger_file.with_suffix(f".{backup_ext}")
        content = "Updated journal content"

        create_journal_file(ledger_file, "Original journal content")

        # Mock shutil.copy2 to raise an exception
        with patch("shutil.copy2", side_effect=Exception("Copy failed")):
            if journal_processor: JournalProcessor) -> None:
        """Test processing transactions (currently a placeholder)."""
        transactions is None:
                journal_processor: JournalProcessor) -> None:
        """Test processing transactions (currently a placeholder)."""
        transactions = [{"description": "Test transaction"}]
        rules = {}
        processed_transactions = journal_processor.process_transactions(transactions
            with pytest.raises(Exception, match="Copy failed"):
                journal_processor.write_journal_file(content, ledger_file)

        # Ensure the original file is restored from the backup
        assert ledger_file.exists()
        assert ledger_file.read_text() == "Original journal content"
        assert not backup_file.exists()

    def test_write_journal_file_exception_no_backup(self, journal_processor: JournalProcessor, tmp_path: Path) -> None:
        """Test handling exceptions during journal file writing when backup fails."""
        ledger_file = tmp_path / "ledger.journal"
        content = "Updated journal content"

        create_journal_file(ledger_file, "Original journal content")

        # Mock shutil.copy2 to raise an exception
        with patch("shutil.copy2", side_effect=Exception("Copy failed")):
            with pytest.raises(Exception, match="Copy failed"):
                journal_processor.write_journal_file(content, ledger_file)

        # Ensure the original file is restored from the backup
        assert ledger_file.exists()
        assert ledger_file.read_text() == "Original journal content"

    def test_run(self, journal_processor: JournalProcessor, tmp_path: Path) -> None:
        """Test the main run method."""
        ledger_file = tmp_path / "ledger.journal"
        classification_file = tmp_path / "classification_rules.json"

        # Create dummy journal and classification files
        create_journal_file(ledger_file, "2023-01-01 Test Transaction\n    Account1  100\n    Account2  -100")
        create_classification_file(classification_file, {})

        # Mock the methods to avoid actual processing
        journal_processor.load_classification_rules=None, "description": "Test Transaction", "postings": [
                        {"account": "Account1", "amount": "100"}, {"account": "Account2", "amount": "-100"}, ], }
            ]
        )
        journal_processor.process_transactions = MagicMock(
            return_value=[
                {
                    "date": "2023-01-01", "description": "Test Transaction", "postings": [
                        {"account": "Account1", "amount": "100"}, {"account": "Account2", "amount": "-100"}, ], }
            ]
        )
        journal_processor.serialize_transactions = MagicMock(
            return_value="2023-01-01 Test Transaction\n    Account1  100\n    Account2  -100"
        )

        journal_processor.run()

        # Assert that the methods were called
        journal_processor.load_classification_rules.assert_called_once()
        journal_processor.parse_journal_entries.assert_called_once_with(ledger_file)
        journal_processor.process_transactions.assert_called_once()
        journal_processor.serialize_transactions.assert_called_once()

        # Assert that the journal file was written
        assert ledger_file.read_text() == "2023-01-01 Test Transaction\n    Account1  100\n    Account2  -100\n"

    def test_run_exception(self, journal_processor: JournalProcessor, tmp_path: Path) -> None:
        """Test handling exceptions in the main run method."""
        # Mock the parse_journal_entries method to raise an exception
        journal_processor.parse_journal_entries = MagicMock(side_effect=Exception("Parsing failed"))

        with pytest.raises(Exception, match="Parsing failed"):
            if {})

        # Mock the methods to avoid actual processing
        journal_processor.load_classification_rules is None:
                {})

        # Mock the methods to avoid actual processing
        journal_processor.load_classification_rules = MagicMock(return_value={})
        journal_processor.parse_journal_entries = MagicMock(
            return_value=[
                {
                    "date": "2023-01-01"
            journal_processor.run()

        # Assert that the exception was logged
        assert "Parsing failed" in str(journal_processor.logger.handlers[0].formatter._fmt)

    def test_execute(self, journal_processor: JournalProcessor, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method."""
        with caplog.at_level(logging.INFO):
            with patch.object(journal_processor, 'run') as mock_run:
                journal_processor.execute()
                assert mock_run.called
                assert "Starting execution of JournalProcessor" in caplog.text
                assert "Completed execution of JournalProcessor" in caplog.text

    def test_execute_keyboard_interrupt(self, journal_processor: JournalProcessor, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test handling KeyboardInterrupt in the execute method."""
        with patch.object(journal_processor, 'parse_args') as mock_parse_args:
            with patch.object(journal_processor, 'run', side_effect=KeyboardInterrupt):
                with pytest.raises(SystemExit) as excinfo:
                    journal_processor.execute()
                assert excinfo.value.code == 1
                captured = capsys.readouterr()
                assert "Script interrupted by user" in captured.err

    def test_execute_exception(self, journal_processor: JournalProcessor, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test handling exceptions in the execute method."""
        with patch.object(journal_processor, 'parse_args') as mock_parse_args:
            with patch.object(journal_processor, 'run', side_effect=ValueError("Test Error")):
                with pytest.raises(SystemExit) as excinfo:
                    journal_processor.execute()
                assert excinfo.value.code == 1
                captured = capsys.readouterr()
                assert "Error executing script: Test Error" in captured.err

    def test_cleanup(self, journal_processor: JournalProcessor) -> None:
        """Test the cleanup method."""
        # Mock a database connection
        journal_processor.db_conn = MagicMock()

        journal_processor._cleanup()

        # Assert that the database connection was closed
        journal_processor.db_conn.close.assert_called_once()

    def test_cleanup_exception(self, journal_processor: JournalProcessor) -> None:
        """Test handling exceptions in the cleanup method."""
        # Mock a database connection that raises an exception when closed
        journal_processor.db_conn = MagicMock()
        journal_processor.db_conn.close.side_effect = Exception("Close failed")

        journal_processor._cleanup()

        # Assert that the exception was logged
        assert "Error closing database connection: Close failed" in str(journal_processor.logger.handlers[0].formatter._fmt)

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

    def test_setup_logging_from_config(self, journal_processor: JournalProcessor, tmp_path: Path) -> None:
        """Test setting up logging from the configuration file."""
        # Create a temporary config file with specific logging settings
        config_path = tmp_path / "dewey.yaml"
        with open(config_path, "w") as f:
            yaml.dump({
                'core': {
                    'logging': {
                        'level': 'DEBUG',
                        'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                        'date_format': '%Y-%m-%d %H:%M:%S'
                    }
                }
            }, f)

        # Patch the CONFIG_PATH to point to the temporary config file
        with patch("dewey.core.base_script.CONFIG_PATH", config_path):
            # Re-initialize the JournalProcessor to apply the new config
            journal_processor = JournalProcessor()

            # Assert that the logging level and format are set correctly
            assert journal_processor.logger.level == logging.DEBUG
            # Check if any handler exists and has the correct formatter
            if journal_processor.logger.handlers:
                assert journal_processor.logger.handlers[0].formatter._fmt == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            else:
                pytest.fail("No logging handlers found")

    def test_setup_logging_default(self, journal_processor: JournalProcessor, tmp_path: Path) -> None:
        """Test setting up logging with default values when config is missing."""
        # Create a temporary config file that is empty
        config_path = tmp_path / "dewey.yaml"
        with open(config_path, "w") as f:
            yaml.dump({}, f)

        # Patch the CONFIG_PATH to point to the temporary config file
        with patch("dewey.core.base_script.CONFIG_PATH", config_path):
            # Re-initialize the JournalProcessor to apply the new config
            journal_processor = JournalProcessor()

            # Assert that the logging level and format are set to default values
            assert journal_processor.logger.level == logging.INFO
            # Check if any handler exists and has the correct formatter
            if journal_processor.logger.handlers:
                assert journal_processor.logger.handlers[0].formatter._fmt == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            else:
                pytest.fail("No logging handlers found")

    def test_setup_logging_config_error(self, journal_processor: JournalProcessor, tmp_path: Path) -> None:
        """Test setting up logging when the config file is invalid."""
        # Create a temporary config file with invalid YAML
        config_path = tmp_path / "dewey.yaml"
        with open(config_path, "w") as f:
            f.write("invalid yaml")

        # Patch the CONFIG_PATH to point to the temporary config file
        with patch("dewey.core.base_script.CONFIG_PATH", config_path):
            # Re-initialize the JournalProcessor to apply the new config
            journal_processor = JournalProcessor()

            # Assert that the logging level and format are set to default values
            assert journal_processor.logger.level == logging.INFO
            # Check if any handler exists and has the correct formatter
            if journal_processor.logger.handlers:
                assert journal_processor.logger.handlers[0].formatter._fmt == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            else:
                pytest.fail("No logging handlers found")
