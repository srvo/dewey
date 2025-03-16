import logging
import re
from datetime import datetime
from typing import Any

# File header: Validates raw transaction data from Mercury CSV files.

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Exception for invalid transaction data."""


def normalize_description(description: str) -> str:
    """Normalize transaction description.

    Args:
    ----
        description: The transaction description string.

    Returns:
    -------
        The normalized transaction description string.

    """
    if not description:
        return ""
    # Remove extra whitespace and normalize case
    return re.sub(r"\s{2,}", " ", description.strip())


def _parse_and_validate_date(date_str: str) -> datetime.date:
    """Parse and validate the date string.

    Args:
    ----
        date_str: The date string in 'YYYY-MM-DD' format.

    Returns:
    -------
        The datetime.date object.

    Raises:
    ------
        ValueError: If the date is invalid or outside the allowed range.

    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    if date_obj.year < 2000 or date_obj > datetime.now():
        msg = f"Invalid date {date_str}"
        raise ValueError(msg)
    return date_obj.date()


def _normalize_amount(amount_str: str) -> float:
    """Normalize the amount string.

    Args:
    ----
        amount_str: The amount string.

    Returns:
    -------
        The normalized amount as a float.

    """
    return float(amount_str.replace(",", "").strip())


class MercuryDataValidator:
    """Validates raw transaction data from Mercury CSV files."""

    def validate_row(self, row: dict[str, str]) -> dict[str, Any]:
        """Validate and normalize a transaction row.

        Args:
        ----
            row: A dictionary representing a transaction row.

        Returns:
        -------
            A dictionary containing the validated and normalized transaction data.

        Raises:
        ------
            DataValidationError: If the transaction data is invalid.

        """
        try:
            # Clean and validate fields
            date_str = row["date"].strip()
            description = _normalize_description(row["description"])
            amount_str = row["amount"].replace(",", "").strip()
            account_id = row["account_id"].strip()

            # Parse date with validation
            date_obj = parse_and_validate_date(date_str)

            # Normalize amount with type detection
            amount = normalize_amount(amount_str)
            is_income = amount > 0
            abs_amount = abs(amount)

            return  {
                "date": date_obj.isoformat(),
                "description": description,
                "amount": abs_amount,
                "is_income": is_income,
                "account_id": account_id,
                "raw": row,  # Keep original for error context
            }

        except (KeyError, ValueError) as e:
            logger.exception("CSV validation error: %s", str(e))
            msg = f"Invalid transaction data: {e!s}"
            raise DataValidationError(msg)
