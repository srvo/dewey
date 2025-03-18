import re
from datetime import datetime
from typing import Any
from dewey.utils import get_logger

# File header: Validates raw transaction data from Mercury CSV files.

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
    logger = get_logger('mercury_validator')
    
    if not description:
        logger.debug("Empty description provided")
        return ""
    # Remove extra whitespace and normalize case
    normalized = re.sub(r"\s{2,}", " ", description.strip())
    logger.debug(f"Normalized description: '{description}' -> '{normalized}'")
    return normalized


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
    logger = get_logger('mercury_validator')
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if date_obj.year < 2000 or date_obj > datetime.now():
            raise ValueError(f"Date {date_str} is outside allowed range")
        return date_obj.date()
    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}")
        raise


def _normalize_amount(amount_str: str) -> float:
    """Normalize and validate amount string.

    Args:
    ----
        amount_str: The amount string.

    Returns:
    -------
        The normalized amount as a float.

    Raises:
    ------
        ValueError: If the amount format is invalid.

    """
    logger = get_logger('mercury_validator')
    
    try:
        # Remove currency symbols and commas
        cleaned = amount_str.replace('$', '').replace(',', '').strip()
        amount = float(cleaned)
        logger.debug(f"Normalized amount: '{amount_str}' -> {amount}")
        return amount
    except ValueError:
        logger.error(f"Invalid amount format: {amount_str}")
        raise ValueError(f"Invalid amount format: {amount_str}")


class MercuryDataValidator:
    """Validates raw transaction data from Mercury CSV files."""

    def __init__(self):
        self.logger = get_logger('mercury_validator')

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
            # Required fields
            if not all(key in row for key in ['date', 'description', 'amount']):
                missing = [k for k in ['date', 'description', 'amount'] if k not in row]
                self.logger.error(f"Missing required fields: {missing}")
                raise DataValidationError(f"Missing required fields: {missing}")
            
            # Validate and normalize fields
            validated = {
                'date': _parse_and_validate_date(row['date']),
                'description': normalize_description(row['description']),
                'amount': _normalize_amount(row['amount'])
            }
            
            # Optional fields
            if 'category' in row:
                validated['category'] = row['category'].strip()
            if 'notes' in row:
                validated['notes'] = row['notes'].strip()
                
            self.logger.debug(f"Validated row: {validated}")
            return validated
            
        except (ValueError, DataValidationError) as e:
            self.logger.error(f"Validation failed: {str(e)}")
            raise DataValidationError(f"Validation failed: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during validation: {str(e)}")
            raise
