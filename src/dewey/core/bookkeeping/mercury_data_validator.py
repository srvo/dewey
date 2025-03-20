import logging
import re
from datetime import datetime
from typing import Any, Dict

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.core.db.utils import create_table, insert_data
from dewey.llm.llm_utils import call_llm


class DataValidationError(Exception):
    """Exception for invalid transaction data."""

    pass


class MercuryDataValidator(BaseScript):
    """Validates raw transaction data from Mercury CSV files."""

    def __init__(self) -> None:
        """Initializes the MercuryDataValidator."""
        super().__init__(config_section="bookkeeping")

    def run(self) -> None:
        """Placeholder for the main execution logic."""
        self.logger.info("MercuryDataValidator is running.")
        # Example usage of config, db, and llm
        example_config_value = self.get_config_value("example_config")
        self.logger.info(f"Example config value: {example_config_value}")

        if self.db_conn:
            try:
                # Example database operation
                self.logger.info("Attempting database operation...")
                # Assuming you have a table named 'transactions'
                # and you want to fetch some data
                query = "SELECT * FROM transactions LIMIT 10"
                result = self.db_conn.execute(query)
                self.logger.info(f"Database query result: {result}")
            except Exception as e:
                self.logger.error(f"Error during database operation: {e}")
        else:
            self.logger.warning("Database connection not initialized.")

        if self.llm_client:
            try:
                # Example LLM call
                self.logger.info("Attempting LLM call...")
                prompt = "Summarize the following text: Example text."
                response = call_llm(self.llm_client, prompt)
                self.logger.info(f"LLM response: {response}")
            except Exception as e:
                self.logger.error(f"Error during LLM call: {e}")
        else:
            self.logger.warning("LLM client not initialized.")

    def normalize_description(self, description: str) -> str:
        """Normalize transaction description.

        Args:
            description: The transaction description string.

        Returns:
            The normalized transaction description string.
        """
        if not description:
            return ""
        # Remove extra whitespace and normalize case
        return re.sub(r"\s{2,}", " ", description.strip())

    def _parse_and_validate_date(self, date_str: str) -> datetime.date:
        """Parse and validate the date string.

        Args:
            date_str: The date string in 'YYYY-MM-DD' format.

        Returns:
            The datetime.date object.

        Raises:
            ValueError: If the date is invalid or outside the allowed range.
        """
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if date_obj.year < 2000 or date_obj > datetime.now():
            msg = f"Invalid date {date_str}"
            raise ValueError(msg)
        return date_obj.date()

    def normalize_amount(self, amount_str: str) -> float:
        """Normalize the amount string.

        Args:
            amount_str: The amount string.

        Returns:
            The normalized amount as a float.
        """
        return float(amount_str.replace(",", "").strip())

    def validate_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Validate and normalize a transaction row.

        Args:
            row: A dictionary representing a transaction row.

        Returns:
            A dictionary containing the validated and normalized transaction data.

        Raises:
            DataValidationError: If the transaction data is invalid.
        """
        try:
            # Clean and validate fields
            date_str = row["date"].strip()
            description = self.normalize_description(row["description"])
            amount_str = row["amount"].replace(",", "").strip()
            account_id = row["account_id"].strip()

            # Parse date with validation
            date_obj = self._parse_and_validate_date(date_str)

            # Normalize amount with type detection
            amount = self.normalize_amount(amount_str)
            is_income = amount > 0
            abs_amount = abs(amount)

            return {
                "date": date_obj.isoformat(),
                "description": description,
                "amount": abs_amount,
                "is_income": is_income,
                "account_id": account_id,
                "raw": row,  # Keep original for error context
            }

        except (KeyError, ValueError) as e:
            self.logger.exception("CSV validation error: %s", str(e))
            msg = f"Invalid transaction data: {e!s}"
            raise DataValidationError(msg)
