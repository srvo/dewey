import logging
from datetime import date, datetime
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.bookkeeping.mercury_data_validator import (
    DataValidationError,
    MercuryDataValidator,
)


@pytest.fixture
def mercury_validator() -> MercuryDataValidator:
    """Fixture to create an instance of MercuryDataValidator."""
    return MercuryDataValidator()


def test_mercury_data_validator_initialization(
    mercury_validator: MercuryDataValidator,
) -> None:
    """Test that MercuryDataValidator initializes correctly."""
    assert mercury_validator.name == "MercuryDataValidator"
    assert mercury_validator.config_section == "bookkeeping"
    assert mercury_validator.logger is not None


def test_normalize_description(mercury_validator: MercuryDataValidator) -> None:
    """Test normalize_description method."""
    assert (
        mercury_validator.normalize_description("  Test   Description  ")
        == "Test Description"
    )
    assert (
        mercury_validator.normalize_description("Test\n\nDescription")
        == "Test Description"
    )
    assert mercury_validator.normalize_description("") == ""
    assert mercury_validator.normalize_description(None) == ""  # type: ignore


def test_parse_and_validate_date(mercury_validator: MercuryDataValidator) -> None:
    """Test _parse_and_validate_date method."""
    valid_date_str = "2023-01-01"
    valid_date = date(2023, 1, 1)
    assert mercury_validator._parse_and_validate_date(valid_date_str) == valid_date

    with pytest.raises(ValueError, match="Invalid date 1999-12-31"):
        mercury_validator._parse_and_validate_date("1999-12-31")

    future_date_str = (datetime.now().year + 1).__str__() + "-01-01"
    with pytest.raises(ValueError, match=f"Invalid date {future_date_str}"):
        mercury_validator._parse_and_validate_date(future_date_str)

    with pytest.raises(
        ValueError, match="time data 'invalid-date' does not match format '%Y-%m-%d'"
    ):
        mercury_validator._parse_and_validate_date("invalid-date")


def test_normalize_amount(mercury_validator: MercuryDataValidator) -> None:
    """Test normalize_amount method."""
    assert mercury_validator.normalize_amount("1,234.56") == 1234.56
    assert mercury_validator.normalize_amount("1234.56") == 1234.56
    assert mercury_validator.normalize_amount("  1234.56  ") == 1234.56
    assert mercury_validator.normalize_amount("0.00") == 0.0


def test_validate_row(mercury_validator: MercuryDataValidator) -> None:
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

    row_income: Dict[str, str] = {
        "date": "2023-01-01",
        "description": "Test Income",
        "amount": "1234.56",
        "account_id": "123",
    }
    validated_row_income: Dict[str, Any] = mercury_validator.validate_row(row_income)
    assert validated_row_income["is_income"] is True
    assert validated_row_income["amount"] == 1234.56


def test_validate_row_invalid_data(mercury_validator: MercuryDataValidator) -> None:
    """Test validate_row method with invalid data."""
    with pytest.raises(DataValidationError, match="Invalid transaction data: 'date'"):
        mercury_validator.validate_row(
            {"description": "Test", "amount": "100", "account_id": "123"}  # type: ignore
        )

    with pytest.raises(
        DataValidationError, match="Invalid transaction data: Invalid date 202"
    ):
        mercury_validator.validate_row(
            {"date": "202", "description": "Test", "amount": "100", "account_id": "123"}
        )

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

    with pytest.raises(
        DataValidationError, match="Invalid transaction data: 'account_id'"
    ):
        mercury_validator.validate_row(
            {"date": "2023-01-01", "description": "Test", "amount": "100"}  # type: ignore
        )


@patch("dewey.core.bookkeeping.mercury_data_validator.call_llm")
@patch("dewey.core.bookkeeping.mercury_data_validator.DatabaseConnection")
def test_run_method(
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
    mercury_validator.db_conn = mock_db_conn_instance

    # Mock LLM call
    mock_call_llm.return_value = "llm_response"
    mercury_validator.llm_client = MagicMock()

    # Mock logger
    mercury_validator.logger = MagicMock()

    # Run the method
    mercury_validator.run()

    # Assertions
    mercury_validator.get_config_value.assert_called_with("example_config")
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
    mock_call_llm.assert_called_once()
    mercury_validator.logger.info.assert_any_call("LLM response: llm_response")


@patch("dewey.core.bookkeeping.mercury_data_validator.call_llm")
@patch("dewey.core.bookkeeping.mercury_data_validator.DatabaseConnection")
def test_run_method_no_db_or_llm(
    mock_db_connection: MagicMock,
    mock_call_llm: MagicMock,
    mercury_validator: MercuryDataValidator,
) -> None:
    """Test the run method when DB and LLM are not initialized."""
    mercury_validator.db_conn = None
    mercury_validator.llm_client = None
    mercury_validator.logger = MagicMock()

    mercury_validator.run()

    mercury_validator.logger.warning.assert_any_call(
        "Database connection not initialized."
    )
    mercury_validator.logger.warning.assert_any_call("LLM client not initialized.")
