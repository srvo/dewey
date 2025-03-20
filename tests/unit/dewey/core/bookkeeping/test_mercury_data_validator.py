"""Tests for dewey.core.bookkeeping.mercury_data_validator."""

from datetime import date, datetime
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.mercury_data_validator import (
    DataValidationError,
    LLMInterface,
    MercuryDataValidator,
)


@pytest.fixture
def mock_base_script() -> MagicMock:
    """Fixture to create a mock BaseScript instance."""
    mock_script = MagicMock(spec=BaseScript)
    mock_script.get_config_value.return_value = "test_value"
    mock_script.logger = MagicMock()
    return mock_script


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Fixture to create a mock LLM client."""
    mock_llm = MagicMock(spec=LLMInterface)
    mock_llm.call_llm.return_value = "LLM response"
    return mock_llm


@pytest.fixture
def mock_db_conn() -> MagicMock:
    """Fixture to create a mock database connection."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value = "db_result"
    return mock_conn


@pytest.fixture
def mercury_validator(mock_llm_client: MagicMock, mock_db_conn: MagicMock) -> MercuryDataValidator:
    """Fixture to create an instance of MercuryDataValidator with mocked dependencies."""
    with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
        validator = MercuryDataValidator(llm_client=mock_llm_client, db_conn=mock_db_conn)
        validator.logger = MagicMock()  # Mock the logger
        return validator


def test_mercury_data_validator_initialization(mercury_validator: MercuryDataValidator) -> None:
    """Test that MercuryDataValidator initializes correctly."""
    assert mercury_validator.name == "MercuryDataValidator"
    assert mercury_validator.config_section == "bookkeeping"
    assert mercury_validator.logger is not None


def test_normalize_description(mercury_validator: MercuryDataValidator) -> None:
    """Test normalize_description method."""
    assert mercury_validator.normalize_description("  Test   Description  ") == "Test Description"
    assert mercury_validator.normalize_description("Test\n\nDescription") == "Test Description"
    assert mercury_validator.normalize_description("") == ""
    assert mercury_validator.normalize_description(None) == ""


class TestDateParsing:
    """Tests for date parsing and validation."""

    def test_parse_date_valid(self, mercury_validator: MercuryDataValidator) -> None:
        """Test _parse_date method with valid date."""
        valid_date_str = "2023-01-01"
        valid_date = date(2023, 1, 1)
        assert mercury_validator._parse_date(valid_date_str) == valid_date

    def test_parse_date_invalid(self, mercury_validator: MercuryDataValidator) -> None:
        """Test _parse_date method with invalid date format."""
        invalid_date_str = "invalid-date"
        with pytest.raises(ValueError, match=f"Invalid date format: {invalid_date_str}"):
            mercury_validator._parse_date(invalid_date_str)

    def test_validate_date_valid(self, mercury_validator: MercuryDataValidator) -> None:
        """Test _validate_date method with a valid date."""
        valid_date = date(2023, 1, 1)
        assert mercury_validator._validate_date(valid_date) == valid_date

    def test_validate_date_invalid_year(self, mercury_validator: MercuryDataValidator) -> None:
        """Test _validate_date method with a year before 2000."""
        invalid_date = date(1999, 12, 31)
        with pytest.raises(ValueError, match=f"Invalid date {invalid_date}"):
            mercury_validator._validate_date(invalid_date)

    def test_validate_date_future(self, mercury_validator: MercuryDataValidator) -> None:
        """Test _validate_date method with a future date."""
        future_date = date(datetime.now().year + 1, 1, 1)
        with pytest.raises(ValueError, match=f"Invalid date {future_date}"):
            mercury_validator._validate_date(future_date)

    def test_parse_and_validate_date_valid(self, mercury_validator: MercuryDataValidator) -> None:
        """Test parse_and_validate_date with a valid date string."""
        date_str = "2023-01-15"
        expected_date = date(2023, 1, 15)
        assert mercury_validator.parse_and_validate_date(date_str) == expected_date

    def test_parse_and_validate_date_invalid(self, mercury_validator: MercuryDataValidator) -> None:
        """Test parse_and_validate_date with an invalid date string."""
        invalid_date_str = "1999-12-31"
        with pytest.raises(ValueError, match="Invalid date"):
            mercury_validator.parse_and_validate_date(invalid_date_str)


def test_normalize_amount(mercury_validator: MercuryDataValidator) -> None:
    """Test normalize_amount method."""
    assert mercury_validator.normalize_amount("1,234.56") == 1234.56
    assert mercury_validator.normalize_amount("1234.56") == 1234.56
    assert mercury_validator.normalize_amount("  1234.56  ") == 1234.56
    assert mercury_validator.normalize_amount("0.00") == 0.0


class TestValidateRow:
    """Tests for the validate_row method."""

    def test_validate_row_valid(self, mercury_validator: MercuryDataValidator) -> None:
        """Test validate_row method with valid data."""
        row: Dict[str, str] = {
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": "1234.56",
            "account_id": "123",
        }
        validated_row: Dict[str, Any] = mercury_validator.validate_row(row)
        assert validated_row["date"] == "2023-01-01"
        assert validated_row["description"] == "Test Transaction"
        assert validated_row["amount"] == 1234.56
        assert validated_row["is_income"] is False
        assert validated_row["account_id"] == "123"
        assert validated_row["raw"] == row

    def test_validate_row_income(self, mercury_validator: MercuryDataValidator) -> None:
        """Test validate_row method with income."""
        row_income: Dict[str, str] = {
            "date": "2023-01-01",
            "description": "Test Income",
            "amount": "1234.56",
            "account_id": "123",
        }
        validated_row_income: Dict[str, Any] = mercury_validator.validate_row(row_income)
        assert validated_row_income["is_income"] is True
        assert validated_row_income["amount"] == 1234.56

    def test_validate_row_negative_amount(self, mercury_validator: MercuryDataValidator) -> None:
        """Test validate_row method with a negative amount."""
        row: Dict[str, str] = {
            "date": "2023-01-01",
            "description": "Test Refund",
            "amount": "-1234.56",
            "account_id": "123",
        }
        validated_row: Dict[str, Any] = mercury_validator.validate_row(row)
        assert validated_row["is_income"] is False
        assert validated_row["amount"] == 1234.56

    def test_validate_row_missing_fields(self, mercury_validator: MercuryDataValidator) -> None:
        """Test validate_row method with missing fields."""
        with pytest.raises(DataValidationError, match="Invalid transaction data: 'date'"):
            mercury_validator.validate_row(
                {"description": "Test", "amount": "100", "account_id": "123"}  # type: ignore
            )

        with pytest.raises(DataValidationError, match="Invalid transaction data: 'account_id'"):
            mercury_validator.validate_row(
                {"date": "2023-01-01", "description": "Test", "amount": "100"}  # type: ignore
            )

    def test_validate_row_invalid_date(self, mercury_validator: MercuryDataValidator) -> None:
        """Test validate_row method with invalid date."""
        with pytest.raises(DataValidationError, match="Invalid transaction data: Invalid date"):
            mercury_validator.validate_row(
                {"date": "202", "description": "Test", "amount": "100", "account_id": "123"}
            )

    def test_validate_row_invalid_amount(self, mercury_validator: MercuryDataValidator) -> None:
        """Test validate_row method with invalid amount."""
        with pytest.raises(
            DataValidationError,
            match="Invalid transaction data: could not convert string to float",
        ):
            mercury_validator.validate_row(
                {
                    "date": "2023-01-01",
                    "description": "Test",
                    "amount": "abc",
                    "account_id": "123",
                }
            )

    def test_validate_row_empty_values(self, mercury_validator: MercuryDataValidator) -> None:
        """Test validate_row method with empty values."""
        row: Dict[str, str] = {
            "date": "2023-01-01",
            "description": "",
            "amount": "0.00",
            "account_id": "123",
        }
        validated_row: Dict[str, Any] = mercury_validator.validate_row(row)
        assert validated_row["description"] == ""
        assert validated_row["amount"] == 0.0
        assert validated_row["is_income"] is False


class TestRunMethod:
    """Tests for the run method."""

    @patch("dewey.core.bookkeeping.mercury_data_validator.call_llm")
    @patch("dewey.core.db.connection.DatabaseConnection")
    def test_run_method_successful(
        self,
        mock_db_connection: MagicMock,
        mock_call_llm: MagicMock,
        mercury_validator: MercuryDataValidator,
    ) -> None:
        """Test the run method with mocked dependencies."""
        # Mock config values
        mercury_validator.get_config_value = MagicMock(return_value="test_value")

        # Mock database connection and execution
        mock_db_conn_instance = mock_db_connection.return_value
        mock_db_conn_instance.execute.return_value = "db_result"
        mercury_validator._db_conn = mock_db_conn_instance

        # Mock LLM call
        mock_call_llm.return_value = "llm_response"
        mercury_validator._llm_client = MagicMock()
        mercury_validator._llm_client.call_llm.return_value = "llm_response"

        # Mock logger
        mercury_validator.logger = MagicMock()

        # Run the method
        mercury_validator.run()

        # Assertions
        mercury_validator.get_config_value.assert_called_with("utils.example_config")
        mercury_validator.logger.info.assert_any_call("MercuryDataValidator is running.")
        mercury_validator.logger.info.assert_any_call("Example config value: test_value")

        # Assert database interaction
        mercury_validator.logger.info.assert_any_call("Attempting database operation...")
        mock_db_conn_instance.execute.assert_called_with(
            "SELECT * FROM transactions LIMIT 10"
        )
        mercury_validator.logger.info.assert_any_call("Database query result: db_result")

        # Assert LLM interaction
        mercury_validator.logger.info.assert_any_call("Attempting LLM call...")
        mercury_validator._llm_client.call_llm.assert_called_once_with(
            "Summarize the following text: Example text."
        )
        mercury_validator.logger.info.assert_any_call("LLM response: llm_response")

    def test_run_method_no_db_or_llm(self, mercury_validator: MercuryDataValidator) -> None:
        """Test the run method when DB and LLM are not initialized."""
        mercury_validator._db_conn = None
        mercury_validator._llm_client = None
        mercury_validator.logger = MagicMock()

        mercury_validator.run()

        mercury_validator.logger.warning.assert_any_call(
            "Database connection not initialized."
        )
        mercury_validator.logger.warning.assert_any_call("LLM client not initialized.")

    @patch("dewey.core.bookkeeping.mercury_data_validator.call_llm")
    @patch("dewey.core.db.connection.DatabaseConnection")
    def test_run_method_db_exception(
        self,
        mock_db_connection: MagicMock,
        mock_call_llm: MagicMock,
        mercury_validator: MercuryDataValidator,
    ) -> None:
        """Test the run method handles database exceptions correctly."""
        mercury_validator.logger = MagicMock()
        mercury_validator._db_conn = MagicMock()
        mercury_validator._llm_client = MagicMock()
        mercury_validator.get_config_value = MagicMock(return_value="test_value")

        # Simulate a database exception
        mercury_validator._db_conn.execute.side_effect = Exception("Database error")

        mercury_validator.run()

        mercury_validator.logger.error.assert_called_with(
            "Error during database operation: Database error"
        )

    @patch("dewey.core.bookkeeping.mercury_data_validator.call_llm")
    @patch("dewey.core.db.connection.DatabaseConnection")
    def test_run_method_llm_exception(
        self,
        mock_db_connection: MagicMock,
        mock_call_llm: MagicMock,
        mercury_validator: MercuryDataValidator,
    ) -> None:
        """Test the run method handles LLM exceptions correctly."""
        mercury_validator.logger = MagicMock()
        mercury_validator._db_conn = MagicMock()
        mercury_validator._llm_client = MagicMock()
        mercury_validator._llm_client.call_llm.side_effect = Exception("LLM error")
        mercury_validator.get_config_value = MagicMock(return_value="test_value")

        mercury_validator.run()

        mercury_validator.logger.error.assert_called_with("Error during LLM call: LLM error")
