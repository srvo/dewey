from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Tuple
from unittest.mock import mock_open, patch

import pytest
from dateutil.relativedelta import relativedelta
from pytest import LogCaptureFixture

from dewey.core.bookkeeping.forecast_generator import JournalEntryGenerator
from dewey.core.base_script import BaseScript


class TestJournalEntryGenerator:
    """Unit tests for the JournalEntryGenerator class."""

    @pytest.fixture
    def generator(self) -> JournalEntryGenerator:
        """Fixture to create a JournalEntryGenerator instance."""
        return JournalEntryGenerator()

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Fixture to mock the configuration."""
        return {
            "bookkeeping": {
                "complete_ledger_file": "complete_ledger.journal",
                "forecast_ledger_file": "forecast.ledger",
            },
            "core": {"logging": {"level": "INFO", "format": "%(message)s"}},
        }

    @pytest.fixture
    def mock_open_func(self) -> Any:
        """Fixture to mock the open function."""
        return mock_open()

    def test_init(self, generator: JournalEntryGenerator, mock_config: Dict[str, Any]) -> None:
        """Test the __init__ method."""
        assert generator.complete_ledger_file == ""
        assert generator.forecast_ledger_file == ""
        assert generator.name == "JournalEntryGenerator"

    @patch("dewey.core.bookkeeping.forecast_generator.JournalEntryGenerator.get_config_value")
    def test_init_with_config(
        self,
        mock_get_config_value: Any,
    ) -> None:
        """Test the __init__ method with configuration values."""
        mock_get_config_value.side_effect = lambda key, default: (
            "test_complete_ledger.journal" if key == "complete_ledger_file" else "test_forecast_ledger.journal"
        )
        generator = JournalEntryGenerator()
        assert generator.complete_ledger_file == "test_complete_ledger.journal"
        assert generator.forecast_ledger_file == "test_forecast_ledger.journal"

    @patch("builtins.input", return_value="y")
    def test_validate_assumptions_yes(
        self,
        mock_input: Any,
        generator: JournalEntryGenerator,
        caplog: LogCaptureFixture,
    ) -> None:
        """Test validate_assumptions when the user enters 'y'."""
        with caplog.at_level(logging.WARNING):
            generator.validate_assumptions()
            assert "Invalid input" not in caplog.text

    @patch("builtins.input", return_value="n")
    def test_validate_assumptions_no(self, mock_input: Any, generator: JournalEntryGenerator) -> None:
        """Test validate_assumptions when the user enters 'n'."""
        with pytest.raises(SystemExit):
            generator.validate_assumptions()

    @patch("builtins.input", return_value="invalid")
    def test_validate_assumptions_invalid(
        self,
        mock_input: Any,
        generator: JournalEntryGenerator,
        caplog: LogCaptureFixture,
    ) -> None:
        """Test validate_assumptions when the user enters an invalid input."""
        with caplog.at_level(logging.WARNING):
            with pytest.raises(SystemExit):
                generator.validate_assumptions()
            assert "Invalid input. Please enter 'y' or 'n'." in caplog.text

    def test_create_acquisition_entry(self, generator: JournalEntryGenerator) -> None:
        """Test create_acquisition_entry."""
        acquisition_date = date(2023, 12, 1)
        entry = generator.create_acquisition_entry(acquisition_date)
        expected_entry = """\
2023-12-01 Acquired Mormair_E650 via barter
    Assets:PPE:Mormair_E650             £2500.00
    Assets:Cash                            £-25.00
    Income:Consulting:Services          £-2475.00

"""
        assert entry == expected_entry

    @patch("builtins.open", new_callable=mock_open)
    def test_append_acquisition_entry_new_file(
        self,
        mock_open_func: Any,
        generator: JournalEntryGenerator,
    ) -> None:
        """Test append_acquisition_entry when the file doesn't exist."""
        complete_ledger_file = "test_ledger.journal"
        acquisition_entry = "Test acquisition entry"
        generator.append_acquisition_entry(complete_ledger_file, acquisition_entry)
        mock_open_func.assert_called_with(complete_ledger_file, "a")
        mock_open_func().write.assert_called_with(acquisition_entry)

    @patch("builtins.open", new_callable=mock_open, read_data="Existing content")
    def test_append_acquisition_entry_exists(
        self,
        mock_open_func: Any,
        generator: JournalEntryGenerator,
    ) -> None:
        """Test append_acquisition_entry when the entry already exists."""
        complete_ledger_file = "test_ledger.journal"
        acquisition_entry = "Existing content"
        generator.append_acquisition_entry(complete_ledger_file, acquisition_entry)
        mock_open_func.assert_called_with(complete_ledger_file, "r")
        mock_open_func().write.assert_not_called()

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_append_acquisition_entry_file_not_found(
        self,
        mock_open_func: Any,
        generator: JournalEntryGenerator,
        caplog: LogCaptureFixture,
    ) -> None:
        """Test append_acquisition_entry when the file is not found."""
        complete_ledger_file = "test_ledger.journal"
        acquisition_entry = "Test acquisition entry"
        with caplog.at_level(logging.WARNING):
            generator.append_acquisition_entry(complete_ledger_file, acquisition_entry)
            assert f"File not found: {complete_ledger_file}" in caplog.text

    @patch("builtins.open", side_effect=Exception("Test error"))
    def test_append_acquisition_entry_error(
        self,
        mock_open_func: Any,
        generator: JournalEntryGenerator,
        caplog: LogCaptureFixture,
    ) -> None:
        """Test append_acquisition_entry when an error occurs."""
        complete_ledger_file = "test_ledger.journal"
        acquisition_entry = "Test acquisition entry"
        with caplog.at_level(logging.ERROR):
            generator.append_acquisition_entry(complete_ledger_file, acquisition_entry)
            assert "Error reading file: Test error" in caplog.text

    @patch("pathlib.Path.exists", return_value=False)
    @patch("builtins.open", new_callable=mock_open)
    def test_initialize_forecast_ledger_new_file(
        self,
        mock_open_func: Any,
        mock_path_exists: Any,
        generator: JournalEntryGenerator,
    ) -> None:
        """Test initialize_forecast_ledger when the file doesn't exist."""
        forecast_ledger_file = "test_forecast.journal"
        generator.initialize_forecast_ledger(forecast_ledger_file)
        mock_open_func.assert_called_with(forecast_ledger_file, "w")
        mock_open_func().write.assert_called()

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_initialize_forecast_ledger_existing_file(
        self,
        mock_open_func: Any,
        mock_path_exists: Any,
        generator: JournalEntryGenerator,
    ) -> None:
        """Test initialize_forecast_ledger when the file already exists."""
        forecast_ledger_file = "test_forecast.journal"
        generator.initialize_forecast_ledger(forecast_ledger_file)
        mock_open_func.assert_not_called()

    @patch("pathlib.Path.exists", return_value=False)
    @patch("builtins.open", side_effect=Exception("Test error"))
    def test_initialize_forecast_ledger_error(
        self,
        mock_open_func: Any,
        mock_path_exists: Any,
        generator: JournalEntryGenerator,
    ) -> None:
        """Test initialize_forecast_ledger when an error occurs."""
        forecast_ledger_file = "test_forecast.journal"
        with pytest.raises(Exception, match="Test error"):
            generator.initialize_forecast_ledger(forecast_ledger_file)

    def test_create_depreciation_entry(self, generator: JournalEntryGenerator) -> None:
        """Test create_depreciation_entry."""
        current_date = datetime(2026, 12, 31)
        entry = generator.create_depreciation_entry(current_date)
        expected_entry = (
            "2026-12-31 Depreciation - Mormair_E650\n"
            "    Expenses:Depreciation:Mormair_E650     £6.94\n"
            "    Assets:AccumulatedDepr:Mormair_E650   £-6.94\n\n"
        )
        assert entry == expected_entry

    @pytest.mark.parametrize(
        "recovered, expected_revenue_share",
        [
            (0, 0.5),
            (125974, 0.5),
            (125975, 0.01),
            (234000, 0.01),
            (359975, 0),
        ],
    )
    def test_create_revenue_entries(
        self,
        generator: JournalEntryGenerator,
        recovered: float,
        expected_revenue_share: float,
    ) -> None:
        """Test create_revenue_entries with different recovered amounts."""
        current_date = datetime(2026, 12, 31)
        generator_data = {"recovered": recovered, "last_revenue": 0}
        (
            lease_income_entry,
            revenue_share_payment_entry,
            hosting_fee_payment_entry,
        ) = generator.create_revenue_entries(current_date, generator_data)

        gross_revenue = 302495
        revenue_share_amount = gross_revenue * expected_revenue_share
        hosting_fee = gross_revenue * 0.25
        expected_cash = gross_revenue - revenue_share_amount - hosting_fee

        assert f"Assets:Cash                          £{expected_cash:.2f}" in lease_income_entry
        assert f"Expenses:RevenueShare:Mormair_E650  £{revenue_share_amount:.2f}" in revenue_share_payment_entry
        assert f"Expenses:Hosting:Mormair_E650        £{hosting_fee:.2f}" in hosting_fee_payment_entry

    @patch.object(JournalEntryGenerator, "create_acquisition_entry")
    @patch.object(JournalEntryGenerator, "append_acquisition_entry")
    @patch.object(JournalEntryGenerator, "initialize_forecast_ledger")
    @patch.object(JournalEntryGenerator, "create_depreciation_entry")
    @patch.object(JournalEntryGenerator, "create_revenue_entries")
    @patch("builtins.open", new_callable=mock_open)
    def test_generate_journal_entries(
        self,
        mock_open_func: Any,
        mock_create_revenue_entries: Any,
        mock_create_depreciation_entry: Any,
        mock_initialize_forecast_ledger: Any,
        mock_append_acquisition_entry: Any,
        mock_create_acquisition_entry: Any,
        generator: JournalEntryGenerator,
    ) -> None:
        """Test generate_journal_entries."""
        complete_ledger_file = "test_complete_ledger.journal"
        forecast_ledger_file = "test_forecast_ledger.journal"

        mock_create_acquisition_entry.return_value = "Acquisition Entry"
        mock_create_depreciation_entry.return_value = "Depreciation Entry"
        mock_create_revenue_entries.return_value = (
            "Lease Income Entry",
            "Revenue Share Entry",
            "Hosting Fee Entry",
        )

        generator.generate_journal_entries(complete_ledger_file, forecast_ledger_file)

        mock_create_acquisition_entry.assert_called()
        mock_append_acquisition_entry.assert_called_with(complete_ledger_file, "Acquisition Entry")
        mock_initialize_forecast_ledger.assert_called_with(forecast_ledger_file)
        assert mock_create_depreciation_entry.call_count == 30 * 12  # 30 years * 12 months
        assert mock_create_revenue_entries.call_count == 30 * 12

    @patch.object(BaseScript, "parse_args")
    @patch.object(JournalEntryGenerator, "validate_assumptions")
    @patch.object(JournalEntryGenerator, "generate_journal_entries")
    def test_run(
        self,
        mock_generate_journal_entries: Any,
        mock_validate_assumptions: Any,
        mock_parse_args: Any,
        generator: JournalEntryGenerator,
    ) -> None:
        """Test the run method."""
        generator.run()

        mock_validate_assumptions.assert_called_once()
        mock_generate_journal_entries.assert_called_once()

    def test_setup_argparse(self, generator: JournalEntryGenerator) -> None:
        """Test the setup_argparse method."""
        parser = generator.setup_argparse()
        assert parser.description == generator.description
        assert parser.prog == "JournalEntryGenerator"

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args(self, mock_parse_args: Any, generator: JournalEntryGenerator) -> None:
        """Test the parse_args method."""
        mock_args = mock_parse_args.return_value
        mock_args.log_level = "DEBUG"
        mock_args.config = None

        args = generator.parse_args()

        assert args == mock_args
        assert generator.logger.level == logging.DEBUG

    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.open", new_callable=mock_open, read_data="test: value")
    def test_parse_args_with_config(
        self,
        mock_open_func: Any,
        mock_parse_args: Any,
        generator: JournalEntryGenerator,
    ) -> None:
        """Test the parse_args method with a config file."""
        mock_args = mock_parse_args.return_value
        mock_args.log_level = None
        mock_args.config = "config.yaml"

        args = generator.parse_args()

        assert args == mock_args
        assert generator.config == {"test": "value"}

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_with_invalid_config(
        self,
        mock_parse_args: Any,
        generator: JournalEntryGenerator,
    ) -> None:
        """Test the parse_args method with an invalid config file."""
        mock_args = mock_parse_args.return_value
        mock_args.log_level = None
        mock_args.config = "config.yaml"

        with pytest.raises(SystemExit):
            generator.parse_args()

    @patch.object(JournalEntryGenerator, "parse_args")
    @patch.object(JournalEntryGenerator, "run")
    def test_execute(
        self,
        mock_run: Any,
        mock_parse_args: Any,
        generator: JournalEntryGenerator,
        caplog: LogCaptureFixture,
    ) -> None:
        """Test the execute method."""
        mock_parse_args.return_value = argparse.Namespace()

        with caplog.at_level(logging.INFO):
            generator.execute()

        assert f"Starting execution of {generator.name}" in caplog.text
        assert f"Completed execution of {generator.name}" in caplog.text
        mock_run.assert_called_once()

    @patch.object(JournalEntryGenerator, "parse_args")
    @patch.object(JournalEntryGenerator, "run", side_effect=KeyboardInterrupt)
    def test_execute_keyboard_interrupt(
        self,
        mock_run: Any,
        mock_parse_args: Any,
        generator: JournalEntryGenerator,
        caplog: LogCaptureFixture,
    ) -> None:
        """Test the execute method with a KeyboardInterrupt."""
        mock_parse_args.return_value = argparse.Namespace()

        with pytest.raises(SystemExit):
            with caplog.at_level(logging.WARNING):
                generator.execute()
                assert "Script interrupted by user" in caplog.text

        mock_run.assert_called_once()

    @patch.object(JournalEntryGenerator, "parse_args")
    @patch.object(JournalEntryGenerator, "run", side_effect=Exception("Test error"))
    def test_execute_exception(
        self,
        mock_run: Any,
        mock_parse_args: Any,
        generator: JournalEntryGenerator,
        caplog: LogCaptureFixture,
    ) -> None:
        """Test the execute method with an exception."""
        mock_parse_args.return_value = argparse.Namespace()

        with pytest.raises(SystemExit):
            with caplog.at_level(logging.ERROR):
                generator.execute()
                assert "Error executing script: Test error" in caplog.text

        mock_run.assert_called_once()

    def test_get_path_absolute(self, generator: JournalEntryGenerator) -> None:
        """Test get_path with an absolute path."""
        path = "/absolute/path"
        result = generator.get_path(path)
        assert result == Path(path)

    def test_get_path_relative(self, generator: JournalEntryGenerator) -> None:
        """Test get_path with a relative path."""
        path = "relative/path"
        result = generator.get_path(path)
        assert result == generator.PROJECT_ROOT / path

    def test_get_config_value(self, generator: JournalEntryGenerator, mock_config: Dict[str, Any]) -> None:
        """Test get_config_value."""
        generator.config = mock_config
        value = generator.get_config_value("bookkeeping.complete_ledger_file")
        assert value == "complete_ledger.journal"

    def test_get_config_value_default(self, generator: JournalEntryGenerator, mock_config: Dict[str, Any]) -> None:
        """Test get_config_value with a default value."""
        generator.config = mock_config
        value = generator.get_config_value("nonexistent.key", "default_value")
        assert value == "default_value"

    def test_get_config_value_nested_default(self, generator: JournalEntryGenerator, mock_config: Dict[str, Any]) -> None:
        """Test get_config_value with a nested default value."""
        generator.config = mock_config
        value = generator.get_config_value("bookkeeping.nonexistent", "default_value")
        assert value == "default_value"

    def test_get_config_value_missing(self, generator: JournalEntryGenerator, mock_config: Dict[str, Any]) -> None:
        """Test get_config_value when the key is missing."""
        generator.config = mock_config
        value = generator.get_config_value("missing.key")
        assert value is None
