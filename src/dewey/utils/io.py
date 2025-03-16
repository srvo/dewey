import logging
from pathlib import Path

import ibis

logger = logging.getLogger(__name__)


def read_csv_to_ibis(file_path: str) -> ibis.expr.types.Table:
    """Read a CSV file into an Ibis table expression.

    Args:
    ----
        file_path: Path to CSV file

    Returns:
    -------
        Ibis table expression representing the CSV data

    Raises:
    ------
        FileNotFoundError: If CSV file doesn't exist

    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"CSV file not found: {file_path}")
        msg = f"CSV file not found: {file_path}"
        raise FileNotFoundError(msg)

    return ibis.read_csv(path)
