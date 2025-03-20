import re
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Any, Dict, Optional

from dewey.core.base_script import BaseScript
from dewey.llm.llm_utils import call_llm


class DataValidationError(Exception):
    """Exception for invalid transaction data."""

    pass


class LLMInterface(ABC):
    """
    An interface for LLM clients.
    """

    @abstractmethod
    def call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt."""
        pass


class DeweyLLM(LLMInterface):
    """
    A wrapper around the dewey LLM client to implement the LLMInterface.
    """

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt."""
        return call_llm(self.llm_client, prompt)


class MercuryDataValidator(BaseScript):
    """Validates raw transaction data from Mercury CSV files.

    This class inherits from BaseScript and leverages its
    configuration, logging, database, and LLM capabilities.
    """

    def __init__(
        self,
        llm_client: Optional[LLMInterface] = None,
        db_conn: Optional[Any] = None,
    ) -> None:
        """Initializes the MercuryDataValidator.

        Calls the superclass constructor to initialize the BaseScript
        with the 'bookkeeping' configuration section.
        """
        super().__init__(config_section="bookkeeping")
        self._llm_client = DeweyLLM(self.llm_client) if llm_client is None and self.llm_client else llm_client
        self._db_conn = db_conn if db_conn is not None else self.db_conn

    def run(self) -> None:
        """Executes the data validation process.

        This method retrieves configuration values, performs a database
        query (if a database connection is available), and makes an LLM
        call (if an LLM client is available).  It logs the progress and
        results of each operation.
        """
        self.logger.info("MercuryDataValidator is running.")

        # Example usage of config
        example_config_value = self.get_config_value("utils.example_config")
        self.logger.info(f"Example config value: {example_config_value}")

        # Example usage of database
        if self._db_conn:
            try:
                self.logger.info("Attempting database operation...")
                query = "SELECT * FROM transactions LIMIT 10"
                result = self._db_conn.execute(query)
                self.logger.info(f"Database query result: {result}")
            except Exception as e:
                self.logger.error(f"Error during database operation: {e}")
        else:
            self.logger.warning("Database connection not initialized.")

        # Example usage of LLM
        if self._llm_client:
            try:
                self.logger.info("Attempting LLM call...")
                prompt = "Summarize the following text: Example text."
                response = self._llm_client.call_llm(prompt)
                self.logger.info(f"LLM response: {response}")
            except Exception as e:
                self.logger.error(f"Error during LLM call: {e}")
        else:
            self.logger.warning("LLM client not initialized.")

    def normalize_description(self, description: Optional[str]) -> str:
        """Normalize transaction description.

        Removes extra whitespace and normalizes the case of the
        transaction description.

        Args:
            description: The transaction description string.

        Returns:
            The normalized transaction description string.
        """
        if not description:
            return ""
        # Remove extra whitespace and normalize case
        return re.sub(r"\s{2,}", " ", description.strip())

    def _parse_date(self, date_str: str) -> date:
        """Parse the date string.

        Parses the date string into a datetime.date object.

        Args:
            date_str: The date string in 'YYYY-MM-DD' format.

        Returns:
            The datetime.date object.

        Raises:
            ValueError: If the date string is invalid.
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            return date_obj
        except ValueError as e:
            msg = f"Invalid date format: {date_str}"
            raise ValueError(msg) from e

    def _validate_date(self, date_obj: date) -> date:
        """Validate the date object.

        Validates that the date is within the allowed range
        (year >= 2000 and not in the future).

        Args:
            date_obj: The datetime.date object.

        Returns:
            The datetime.date object.

        Raises:
            ValueError: If the date is outside the allowed range.
        """
        if date_obj.year < 2000 or date_obj > datetime.now().date():
            msg = f"Invalid date {date_obj}"
            raise ValueError(msg)
        return date_obj

    def parse_and_validate_date(self, date_str: str) -> date:
        """Parse and validate the date string.

        Parses the date string and validates that it is within the
        allowed range (year >= 2000 and not in the future).

        Args:
            date_str: The date string in 'YYYY-MM-DD' format.

        Returns:
            The datetime.date object.

        Raises:
            ValueError: If the date is invalid or outside the allowed range.
        """
        date_obj = self._parse_date(date_str)
        return self._validate_date(date_obj)

    def normalize_amount(self, amount_str: str) -> float:
        """Normalize the amount string.

        Removes commas and whitespace from the amount string and converts
        it to a float.

        Args:
            amount_str: The amount string.

        Returns:
            The normalized amount as a float.
        """
        return float(amount_str.replace(",", "").strip())

    def validate_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Validate and normalize a transaction row.

        Validates and normalizes the data in a transaction row,
        including the date, description, amount, and account ID.

        Args:
            row: A dictionary representing a transaction row.

        Returns:
            A dictionary containing the validated and normalized
            transaction data.

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
            date_obj = self.parse_and_validate_date(date_str)

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
