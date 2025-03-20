"""Tests for dewey.core.bookkeeping.deferred_revenue."""

import os
import re
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, mock_open, patch

import pytest
from dateutil.relativedelta import relativedelta

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.deferred_revenue import AltruistIncomeProcessor


class TestAltruistIncomeProcessor:
    """Tests for the AltruistIncomeProcessor class."""

    @pytest.fixture
    def processor(self) -> AltruistIncomeProcessor:
        """Fixture for creating an AltruistIncomeProcessor instance."""
        return AltruistIncomeProcessor()

    def test_init(self, processor: AltruistIncomeProcessor) -> None:
        """Test the __init__ method."""
        assert processor.name == "Altruist Income Processor"
        assert processor.description == "Processes Altruist income for deferred revenue recognition."
        assert processor.config_section == "bookkeeping"
        assert processor.requires_db is False
        assert processor.enable_llm is False

    def test_parse_altruist_transactions_empty(self, processor: AltruistIncomeProcessor) -> None:
        """Test _parse_altruist_transactions with empty journal content."""
        journal_content = ""
        matches = processor._parse_altruist_transactions(journal_content)
        assert matches == []

    def test_parse_altruist_transactions_no_match(self, processor: AltruistIncomeProcessor) -> None:
        """Test _parse_altruist_transactions with no matching transactions."""
        journal_content = "2024-01-01 Some other transaction 100.00"
        matches = processor._parse_altruist_transactions(journal_content)
        assert matches == []

    def test_parse_altruist_transactions_single_match(self, processor: AltruistIncomeProcessor) -> None:
        """Test _parse_altruist_transactions with a single matching transaction."""
        journal_content = "2024-01-01 Altruist transaction description\n    Income:Altruist  123.45"
        matches = processor._parse_altruist_transactions(journal_content)
        assert len(matches) == 1
        assert matches[0].group(1) == "2024-01-01"
        assert matches[0].group(2) == "Altruist transaction description"
        assert matches[0].group(3) == "123.45"

    def test_parse_altruist_transactions_multiple_matches(self, processor: AltruistIncomeProcessor) -> None:
        """Test _parse_altruist_transactions with multiple matching transactions."""
        journal_content = """
2024-01-01 Altruist transaction 1\n    Income:Altruist  100.00
2024-02-01 Altruist transaction 2\n    Income:Altruist  200.00
"""
        matches = processor._parse_altruist_transactions(journal_content)
        assert len(matches) == 2
        assert matches[0].group(1) == "2024-01-01"
        assert matches[0].group(2) == "Altruist transaction 1"
        assert matches[0].group(3) == "100.00"
        assert matches[1].group(1) == "2024-02-01"
        assert matches[1].group(2) == "Altruist transaction 2"
        assert matches[1].group(3) == "200.00"

    def test_parse_altruist_transactions_case_insensitive(self, processor: AltruistIncomeProcessor) -> None:
        """Test _parse_altruist_transactions with case-insensitive matching."""
        journal_content = "2024-01-01 aLtRuIsT transaction\n    Income:Altruist  100.00"
        matches = processor._parse_altruist_transactions(journal_content)
        assert len(matches) == 1

    def test_generate_deferred_revenue_transactions(self, processor: AltruistIncomeProcessor) -> None:
        """Test _generate_deferred_revenue_transactions."""
        match = MagicMock()
        match.group.side_effect = ["2024-01-15", "Test Altruist Transaction", "300.00"]
        transactions = processor._generate_deferred_revenue_transactions(match)
        assert len(transactions) == 5
        assert "2024-01-15 * Fee income from Altruist" in transactions[0]
        assert "income:fees    100.0" in transactions[0]
        assert "assets:deferred_revenue   -100.0" in transactions[0]
        assert "2024-01-15 * Deferred revenue from Altruist" in transactions[1]
        assert "assets:bank                      -300.0" in transactions[1]
        assert "assets:deferred_revenue         300.0" in transactions[1]
        assert "2024-02-15 * Fee income from Altruist" in transactions[2]
        assert "assets:deferred_revenue   -100.0" in transactions[2]
        assert "income:fees    100.0" in transactions[2]
        assert "2024-03-15 * Fee income from Altruist" in transactions[3]
        assert "assets:deferred_revenue   -100.0" in transactions[3]
        assert "income:fees    100.0" in transactions[3]

    def test_generate_deferred_revenue_transactions_rounding(self, processor: AltruistIncomeProcessor) -> None:
        """Test _generate_deferred_revenue_transactions with rounding."""
        match = MagicMock()
        match.group.side_effect = ["2024-01-15", "Test Altruist Transaction", "100.00"]
        transactions = processor._generate_deferred_revenue_transactions(match)
        assert len(transactions) == 5
        assert "income:fees    33.33" in transactions[0]
        assert "assets:deferred_revenue   -33.33" in transactions[0]
        assert "assets:deferred_revenue   -33.33" in transactions[2]
        assert "income:fees    33.33" in transactions[2]
        assert "assets:deferred_revenue   -33.33" in transactions[3]
        assert "income:fees    33.33" in transactions[3]

    @patch("os.path.exists", return_value=False)
    def test_process_altruist_income_file_not_found(self, mock_exists: MagicMock, processor: AltruistIncomeProcessor, tmp_path) -> None:
        """Test process_altruist_income when the journal file is not found."""
        journal_file = str(tmp_path / "nonexistent_journal.txt")
        with pytest.raises(FileNotFoundError) as excinfo:
            processor.process_altruist_income(journal_file)
        assert str(excinfo.value) == f"Could not find journal file at: {journal_file}"
        mock_exists.assert_called_once_with(journal_file)

    @patch("os.path.exists", return_value=True)
    def test_process_altruist_income_no_matches(self, mock_exists: MagicMock, processor: AltruistIncomeProcessor, tmp_path) -> None:
        """Test process_altruist_income when no Altruist transactions are found."""
        journal_file = str(tmp_path / "journal.txt")
        with open(journal_file, "w") as f:
            f.write("Some other transaction")
        result = processor.process_altruist_income(journal_file)
        assert result == "Some other transaction"
        mock_exists.assert_called_once_with(journal_file)

    @patch("os.path.exists", return_value=True)
    def test_process_altruist_income_single_match(self, mock_exists: MagicMock, processor: AltruistIncomeProcessor, tmp_path) -> None:
        """Test process_altruist_income with a single Altruist transaction."""
        journal_file = str(tmp_path / "journal.txt")
        with open(journal_file, "w") as f:
            f.write("2024-01-01 Altruist transaction\n    Income:Altruist  300.00")

        with patch.object(processor, "_generate_deferred_revenue_transactions") as mock_generate:
            mock_generate.return_value = ["transaction1", "transaction2"]
            result = processor.process_altruist_income(journal_file)
            assert "transaction1" in result
            assert "transaction2" in result
        mock_exists.assert_called_once_with(journal_file)

    @patch("os.path.exists", return_value=True)
    def test_process_altruist_income_multiple_matches(self, mock_exists: MagicMock, processor: AltruistIncomeProcessor, tmp_path) -> None:
        """Test process_altruist_income with multiple Altruist transactions."""
        journal_file = str(tmp_path / "journal.txt")
        with open(journal_file, "w") as f:
            f.write("""
2024-01-01 Altruist transaction 1\n    Income:Altruist  100.00
2024-02-01 Altruist transaction 2\n    Income:Altruist  200.00
""")
        with patch.object(processor, "_generate_deferred_revenue_transactions") as mock_generate:
            mock_generate.side_effect = [["transaction1", "transaction2"], ["transaction3", "transaction4"]]
            result = processor.process_altruist_income(journal_file)
            assert "transaction1" in result
            assert "transaction2" in result
            assert "transaction3" in result
            assert "transaction4" in result
        mock_exists.assert_called_once_with(journal_file)

    @patch("os.path.exists", return_value=True)
    def test_process_altruist_income_generate_transactions_error(self, mock_exists: MagicMock, processor: AltruistIncomeProcessor, tmp_path) -> None:
        """Test process_altruist_income when _generate_deferred_revenue_transactions raises an exception."""
        journal_file = str(tmp_path / "journal.txt")
        with open(journal_file, "w") as f:
            f.write("2024-01-01 Altruist transaction\n    Income:Altruist  300.00")

        with patch.object(processor, "_generate_deferred_revenue_transactions") as mock_generate:
            mock_generate.side_effect = Exception("Failed to generate transactions")
            result = processor.process_altruist_income(journal_file)
            assert result == "2024-01-01 Altruist transaction\n    Income:Altruist  300.00"
        mock_exists.assert_called_once_with(journal_file)

    @patch("os.path.exists", return_value=True)
    def test_process_altruist_income_no_new_transactions(self, mock_exists: MagicMock, processor: AltruistIncomeProcessor, tmp_path) -> None:
        """Test process_altruist_income when no new transactions are added."""
        journal_file = str(tmp_path / "journal.txt")
        with open(journal_file, "w") as f:
            f.write("2024-01-01 Altruist transaction\n    Income:Altruist  300.00")

        with patch.object(processor, "_generate_deferred_revenue_transactions") as mock_generate:
            mock_generate.return_value = []
            result = processor.process_altruist_income(journal_file)
            assert result == "2024-01-01 Altruist transaction\n    Income:Altruist  300.00"
        mock_exists.assert_called_once_with(journal_file)

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="Initial journal content")
    @patch.object(AltruistIncomeProcessor, "_parse_altruist_transactions")
    @patch.object(AltruistIncomeProcessor, "_generate_deferred_revenue_transactions")
    def test_process_altruist_income_success(
        self,
        mock_generate: MagicMock,
        mock_parse: MagicMock,
        mock_file_open: MagicMock,
        mock_exists: MagicMock,
        processor: AltruistIncomeProcessor,
        tmp_path: pytest.TempPathFactory,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test process_altruist_income when the processing is successful."""
        journal_file = str(tmp_path / "journal.txt")
        mock_parse.return_value = [MagicMock()]
        mock_generate.return_value = ["transaction1", "transaction2"]

        result = processor.process_altruist_income(journal_file)

        assert "Initial journal content" in result
        assert "transaction1" in result
        assert "transaction2" in result
        assert "Successfully processed 1 Altruist transactions" in caplog.text
        mock_exists.assert_called_once_with(journal_file)
        mock_file_open.assert_called_with(journal_file)
        mock_parse.assert_called_once()
        mock_generate.assert_called_once()

    @patch("os.path.exists", return_value=True)
    @patch("sys.argv", ["script.py", "journal.txt"])
    @patch.object(AltruistIncomeProcessor, "process_altruist_income", return_value="Updated journal content")
    def test_run_success(
        self,
        mock_process_altruist_income: MagicMock,
        mock_exists: MagicMock,
        processor: AltruistIncomeProcessor,
        tmp_path: pytest.TempPathFactory,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test the run method with successful processing."""
        journal_file = str(tmp_path / "journal.txt")
        backup_file = journal_file + ".bak"

        with patch("builtins.open", new_callable=mock_open) as mock_open_func, \
             patch("os.rename") as mock_rename:
            processor.run()

        captured = capsys.readouterr()
        assert "Journal file updated successfully" in captured.out
        mock_exists.assert_called_with("journal.txt")
        mock_process_altruist_income.assert_called_once_with("journal.txt")
        assert mock_open_func.call_count == 2  # Called twice (read and write)
        assert mock_rename.call_count == 0

    @patch("os.path.exists", return_value=True)
    @patch("sys.argv", ["script.py", "nonexistent_journal.txt"])
    @patch.object(AltruistIncomeProcessor, "process_altruist_income", side_effect=FileNotFoundError("File not found"))
    def test_run_file_not_found(
        self,
        mock_process_altruist_income: MagicMock,
        mock_exists: MagicMock,
        processor: AltruistIncomeProcessor,
        tmp_path: pytest.TempPathFactory,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test the run method when the journal file is not found."""
        journal_file = str(tmp_path / "nonexistent_journal.txt")

        with pytest.raises(SystemExit) as excinfo:
            processor.run()
        assert excinfo.value.code == 1

        captured = capsys.readouterr()
        assert "Journal file not found" in captured.err
        mock_exists.assert_called_with("nonexistent_journal.txt")
        mock_process_altruist_income.assert_called_once_with("nonexistent_journal.txt")

    @patch("os.path.exists", return_value=True)
    @patch("sys.argv", ["script.py", "journal.txt"])
    @patch.object(AltruistIncomeProcessor, "process_altruist_income", side_effect=Exception("Unexpected error"))
    def test_run_unexpected_error(
        self,
        mock_process_altruist_income: MagicMock,
        mock_exists: MagicMock,
        processor: AltruistIncomeProcessor,
        tmp_path: pytest.TempPathFactory,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test the run method when an unexpected error occurs."""
        journal_file = str(tmp_path / "journal.txt")

        with pytest.raises(SystemExit) as excinfo:
            processor.run()
        assert excinfo.value.code == 1

        captured = capsys.readouterr()
        assert "An unexpected error occurred" in captured.err
        mock_exists.assert_called_with("journal.txt")
        mock_process_altruist_income.assert_called_once_with("journal.txt")

    @patch("sys.argv", ["script.py"])
    def test_run_usage_error(self, processor: AltruistIncomeProcessor, capsys: pytest.CaptureFixture) -> None:
        """Test the run method when the usage is incorrect."""
        with pytest.raises(SystemExit) as excinfo:
            processor.run()
        assert excinfo.value.code == 1

        captured = capsys.readouterr()
        assert "Usage: python script.py <journal_file>" in captured.err

    def test_get_path_absolute(self, processor: AltruistIncomeProcessor, tmp_path: pytest.TempPathFactory) -> None:
        """Test get_path with an absolute path."""
        absolute_path = tmp_path / "test.txt"
        resolved_path = processor.get_path(str(absolute_path))
        assert resolved_path == absolute_path

    def test_get_path_relative(self, processor: AltruistIncomeProcessor) -> None:
        """Test get_path with a relative path."""
        relative_path = "data/test.txt"
        expected_path = processor.PROJECT_ROOT / relative_path
        resolved_path = processor.get_path(relative_path)
        assert resolved_path == expected_path

    def test_get_config_value_existing_key(self, processor: AltruistIncomeProcessor) -> None:
        """Test get_config_value with an existing key."""
        processor.config = {"level1": {"level2": "value"}}
        value = processor.get_config_value("level1.level2")
        assert value == "value"

    def test_get_config_value_missing_key(self, processor: AltruistIncomeProcessor) -> None:
        """Test get_config_value with a missing key."""
        processor.config = {"level1": {"level2": "value"}}
        value = processor.get_config_value("level1.level3", "default")
        assert value == "default"

    def test_get_config_value_missing_level(self, processor: AltruistIncomeProcessor) -> None:
        """Test get_config_value with a missing level."""
        processor.config = {"level1": {"level2": "value"}}
        value = processor.get_config_value("level3.level4", "default")
        assert value == "default"

    def test_get_config_value_default_none(self, processor: AltruistIncomeProcessor) -> None:
        """Test get_config_value with a missing key and default=None."""
        processor.config = {"level1": {"level2": "value"}}
        value = processor.get_config_value("level1.level3")
        assert value is None

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_log_level(self, mock_parse_args: MagicMock, processor: AltruistIncomeProcessor) -> None:
        """Test parse_args with log level argument."""
        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_args.config = None
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with patch.object(processor.logger, "setLevel") as mock_set_level:
            processor.parse_args()
            mock_set_level.assert_called_once_with(10)  # DEBUG = 10

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config(self, mock_parse_args: MagicMock, processor: AltruistIncomeProcessor, tmp_path: pytest.TempPathFactory) -> None:
        """Test parse_args with config argument."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            f.write("test: value")

        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = str(config_file)
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        processor.parse_args()
        assert processor.config == {"test": "value"}

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config_not_found(self, mock_parse_args: MagicMock, processor: AltruistIncomeProcessor, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture) -> None:
        """Test parse_args when the config file is not found."""
        config_file = tmp_path / "nonexistent_config.yaml"

        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = str(config_file)
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with pytest.raises(SystemExit) as excinfo:
            processor.parse_args()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert f"Configuration file not found: {config_file}" in captured.err

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_db_connection_string(self, mock_parse_args: MagicMock, processor: AltruistIncomeProcessor) -> None:
        """Test parse_args with db_connection_string argument."""
        processor.requires_db = True
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.db_connection_string = "test_connection_string"
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with patch("dewey.core.db.connection.get_connection") as mock_get_connection:
            processor.parse_args()
            mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})
            assert processor.db_conn == mock_get_connection.return_value

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_llm_model(self, mock_parse_args: MagicMock, processor: AltruistIncomeProcessor) -> None:
        """Test parse_args with llm_model argument."""
        processor.enable_llm = True
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.db_connection_string = None
        mock_args.llm_model = "test_llm_model"
        mock_parse_args.return_value = mock_args

        with patch("dewey.llm.llm_utils.get_llm_client") as mock_get_llm_client:
            processor.parse_args()
            mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})
            assert processor.llm_client == mock_get_llm_client.return_value

    def test_setup_argparse(self, processor: AltruistIncomeProcessor) -> None:
        """Test setup_argparse method."""
        parser = processor.setup_argparse()
        assert parser.description == processor.description
        assert parser._actions[1].dest == "config"
        assert parser._actions[2].dest == "log_level"

    def test_setup_argparse_with_db(self, processor: AltruistIncomeProcessor) -> None:
        """Test setup_argparse method when requires_db is True."""
        processor.requires_db = True
        parser = processor.setup_argparse()
        assert parser._actions[3].dest == "db_connection_string"

    def test_setup_argparse_with_llm(self, processor: AltruistIncomeProcessor) -> None:
        """Test setup_argparse method when enable_llm is True."""
        processor.enable_llm = True
        parser = processor.setup_argparse()
        assert parser._actions[3].dest == "llm_model"

    def test_cleanup(self, processor: AltruistIncomeProcessor) -> None:
        """Test _cleanup method."""
        mock_db_conn = MagicMock()
        processor.db_conn = mock_db_conn
        processor._cleanup()
        mock_db_conn.close.assert_called_once()

    def test_cleanup_no_db_conn(self, processor: AltruistIncomeProcessor) -> None:
        """Test _cleanup method when db_conn is None."""
        processor.db_conn = None
        processor._cleanup()
        # Assert that no exception is raised

    def test_cleanup_db_conn_error(self, processor: AltruistIncomeProcessor, caplog: pytest.LogCaptureFixture) -> None:
        """Test _cleanup method when db_conn.close() raises an exception."""
        mock_db_conn = MagicMock()
        mock_db_conn.close.side_effect = Exception("Failed to close connection")
        processor.db_conn = mock_db_conn
        processor._cleanup()
        assert "Error closing database connection" in caplog.text

    @patch("sys.exit")
    @patch("os.path.exists", return_value=True)
    def test_execute_keyboard_interrupt(self, mock_exists: MagicMock, mock_sys_exit: MagicMock, processor: AltruistIncomeProcessor) -> None:
        """Test execute method when KeyboardInterrupt is raised."""
        with patch.object(processor, "parse_args") as mock_parse_args, \
             patch.object(processor, "run", side_effect=KeyboardInterrupt):
            mock_parse_args.return_value = MagicMock()
            processor.execute()
            mock_sys_exit.assert_called_once_with(1)

    @patch("sys.exit")
    @patch("os.path.exists", return_value=True)
    def test_execute_exception(self, mock_exists: MagicMock, mock_sys_exit: MagicMock, processor: AltruistIncomeProcessor) -> None:
        """Test execute method when an exception is raised."""
        with patch.object(processor, "parse_args") as mock_parse_args, \
             patch.object(processor, "run", side_effect=Exception("Test exception")):
            mock_parse_args.return_value = MagicMock()
            processor.execute()
            mock_sys_exit.assert_called_once_with(1)

    @patch("os.path.exists", return_value=True)
    def test_execute_success(self, mock_exists: MagicMock, processor: AltruistIncomeProcessor) -> None:
        """Test execute method when the script runs successfully."""
        with patch.object(processor, "parse_args") as mock_parse_args, \
             patch.object(processor, "run") as mock_run, \
             patch.object(processor, "_cleanup") as mock_cleanup:
            mock_parse_args.return_value = MagicMock()
            processor.execute()
            mock_run.assert_called_once()
            mock_cleanup.assert_called_once()

    def test_abstract_run(self, processor: AltruistIncomeProcessor) -> None:
        """Test that the run method is abstract."""
        with pytest.raises(TypeError):
            BaseScript().run()
