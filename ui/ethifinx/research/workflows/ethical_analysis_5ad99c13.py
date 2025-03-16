```python
"""Ethical analysis workflow module."""

import csv
import json
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional

import duckdb

from ethifinx.core.config import config
from ethifinx.core.logging_config import setup_logging
from ethifinx.research.engines import DeepSeekEngine, DuckDuckGoEngine
from ethifinx.research.workflows.base import ResearchWorkflow
from ethifinx.research.workflows.output_handler import ResearchOutputHandler

logger = setup_logging(__name__)


class EthicalAnalysisWorkflow(ResearchWorkflow):
    """Enhanced ethical analysis workflow with resource management."""

    CHUNK_SIZE = 50  # Process companies in batches
    WORD_LIMIT = 50000  # Prevent memory overconsumption

    def __init__(self) -> None:
        """Initializes the EthicalAnalysisWorkflow."""
        super().__init__()
        self.search_engine = DuckDuckGoEngine()
        self.analysis_engine = DeepSeekEngine()
        self.output_handler = ResearchOutputHandler()
        self._word_count = 0

    def read_exclusions(self, file_path: Path) -> List[Dict]:
        """Reads exclusions from a CSV file and validates the schema.

        Args:
            file_path: The path to the CSV file.

        Returns:
            A list of dictionaries, where each dictionary represents a row
            in the CSV file.

        Raises:
            ValueError: If the CSV file is missing required columns.
            Exception: If there's an error reading the file.
        """
        try:
            with open(file_path, "r") as f:
                reader = csv.DictReader(f)

                if not {"Company", "Category", "Criteria"}.issubset(
                    reader.fieldnames
                ):
                    raise ValueError("Missing required CSV columns")

                return [
                    {k.strip(): v.strip() for k, v in row.items()}
                    for row in reader
                ]
        except Exception as e:
            logger.error(f"Invalid exclusions file: {str(e)}")
            raise

    def execute(self, data_dir: Optional[str] = None) -> Dict:
        """Executes the ethical analysis workflow.

        Args:
            data_dir: Optional directory to store data.
                      Defaults to config.data_dir.

        Returns:
            A dictionary containing the results of the analysis.
        """
        data_dir = Path(data_dir) if data_dir else config.data_dir
        data_dir.mkdir(exist_ok=True, parents=True)

        # Initialize with safety checks
        db_path = data_dir / "research.db"
        if db_path.exists() and db_path.stat().st_size > 1_000_000_000:  # 1GB
            logger.warning(
                f"Database size {db_path.stat().st_size/1e6:.1f}MB "
                "exceeds usual thresholds"
            )

        with closing(duckdb.connect(str(db_path))) as con:
            self._setup_database(con)
            # Process in chunks to limit memory usage
            for chunk in self._process_chunks(data_dir):
                # Batch database operations
                with con.cursor() as cursor:
                    self._process_chunk(cursor, chunk)

                # Check resource limits
                if self._word_count > self.WORD_LIMIT:
                    logger.warning(
                        f"Terminating early: Word limit {self.WORD_LIMIT} reached"
                    )
                    break

        # Existing statistics handling remains

    def _process_chunks(
        self, data_dir: Path
    ) -> Generator[List[Dict], None, None]:
        """Yields company chunks with progress tracking.

        Args:
            data_dir: The path to the data directory.

        Yields:
            A list of dictionaries, where each dictionary represents a company.
        """
        exclusions = self.read_exclusions(data_dir / "exclude.csv")
        logger.info(
            f"Processing {len(exclusions)} companies in chunks of "
            f"{self.CHUNK_SIZE}"
        )

        for i in range(0, len(exclusions), self.CHUNK_SIZE):
            yield exclusions[i : i + self.CHUNK_SIZE]

    def _process_chunk(
        self, cursor: duckdb.DuckDBPyConnection, chunk: List[Dict]
    ) -> None:
        """Processes a company batch with transaction.

        Args:
            cursor: The DuckDB connection cursor.
            chunk: A list of dictionaries, where each dictionary represents
                   a company.
        """
        cursor.execute("BEGIN TRANSACTION")
        try:
            for company in chunk:
                # Existing processing logic here
                self._word_count += self.word_count(company.get("snippet", ""))
            cursor.execute("COMMIT")
        except Exception as e:
            cursor.execute("ROLLBACK")
            logger.error(f"Chunk processing failed: {str(e)}")
            raise
```
