```python
from typing import Any, Dict

from ethifinx.core.logger import setup_logger

logger = setup_logger("data_processor", "logs/data_processor.log")


def process_data(data: Any) -> Dict[str, Any]:
    """Processes raw data into a structured format.

    Args:
        data: The raw data to be processed.

    Returns:
        A dictionary containing the processed data.

    Raises:
        Exception: If an error occurs during data processing.
    """
    logger.debug("Processing data")
    try:
        processed_data = {"processed": True, "original_data": data}
        logger.info("Data processed successfully.")
        return processed_data
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        raise


class DataProcessor:
    """A class for processing data."""

    def process(self, data: Any) -> Dict[str, Any]:
        """Processes raw data into a structured format.

        Args:
            data: The raw data to be processed.

        Returns:
            A dictionary containing the processed data.

        Raises:
            Exception: If an error occurs during data processing.
        """
        return process_data(data)
```
