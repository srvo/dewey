#!/usr/bin/env python3
import logging
import os
import subprocess
import sys
from pathlib import Path

from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm

# Absolute path to project root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.dewey.core.bookkeeping.engines.classification_engine_60acc1e2 import ClassificationEngine, ClassificationError
from src.dewey.llm.api_clients.deepinfra import classify_errors

# Import AFTER path configuration
from dotenv import find_dotenv, load_dotenv
from src.dewey.core.bookkeeping.writers.journal_writer_fab1858b import JournalWriter

# Load environment variables from nearest .env file
load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Configure DeepInfra
deepinfra_api_key = os.getenv("DEEPINFRA_API_KEY")
model_name = os.getenv("DEEPINFRA_DEFAULT_MODEL")

if not deepinfra_api_key:
    logger.error("DEEPINFRA_API_KEY environment variable not set.")
    sys.exit(1)
if not model_name:
    logger.error("DEEPINFRA_DEFAULT_MODEL environment variable not set.")
    sys.exit(1)


class ClassificationVerifier:
    def __init__(self, rules_path: Path, journal_path: Path) -> None:
        self.engine = ClassificationEngine(rules_path)
        self.writer = JournalWriter(journal_path.parent)
        self.journal_path = journal_path
        self.processed_feedback = 0

    @property
    def valid_categories(self) -> list[str]:
        """Get valid classification categories from engine."""
        return self.engine.categories

    def get_ai_suggestion(self, description: str) -> str:
        """Get AI classification suggestion using DeepInfra."""
        try:
            response = classify_errors(
                [f"Classify transaction: '{description}'"],
                instructions="Return ONLY the account path as category1:category2",
            )
            return response[0]["category"] if response else ""
        except Exception as e:
            logger.exception("AI classification failed: %s", str(e))
            return ""

    def get_transaction_samples(self, limit: int = 50) -> list[dict]:
        """Get sample transactions using hledger + DuckDB."""
        try:
            # Get CSV data directly from hledger
            cmd = [
                "hledger",
                "-f",
                str(self.journal_path),
                "print",
                "-O",
                "csv",
                "date:lastmonth",
                "not:unknown",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                logger.error("hledger export failed: %s", result.stderr)
                return []

            # Connect to in-memory DuckDB database
            import duckdb

            with duckdb.connect(":memory:") as con:
                # Create temp table from CSV data
                con.execute(
                    """
                    CREATE TEMP TABLE txns AS
                    SELECT * FROM 'csv:stdin' (header=true)
                    WHERE date BETWEEN
                        DATE_TRUNC('month', CURRENT_DATE - INTERVAL 1 MONTH) AND
                        DATE_TRUNC('month', CURRENT_DATE) - INTERVAL 1 DAY
                """,
                    [result.stdout],
                )

                # Query with proper typing and ordering
                query = f"""
                    SELECT
                        date,
                        description,
                        amount,
                        account,
                        STRFTIME(STRPTIME(date, '%Y-%m-%d'), '%Y-%m-%d') AS parsed_date
                    FROM txns
                    ORDER BY parsed_date DESC
                    LIMIT {limit}
                """
                result = con.execute(query).fetchall()
                columns = [col[0] for col in con.description]

                return [dict(zip(columns, row, strict=False)) for row in result]

        except Exception as e:
            logger.exception("DuckDB processing failed: %s", str(e))
            return []

    def prompt_for_feedback(self, tx: dict) -> None:
        """Interactive prompt for transaction verification."""
        if not isinstance(tx, dict):
            logger.error("Invalid transaction format - expected dict, got %s", type(tx))
            return

        try:
            desc = tx.get("description", "Unknown transaction")
            account = tx.get("account", "UNCLASSIFIED")
            # hledger's register amounts are strings like "$-1.00" or "$2.50"
            amount_str = tx.get("amount", "0")
            # Split currency symbol and number, handle negative amounts
            "".join(
                [c for c in amount_str.split()[-1] if c in "0123456789-."],
            ) or "0.00"

            # Get AI suggestion
            suggested_category = self.get_ai_suggestion(desc)
            if suggested_category:
                pass

            response = confirm("Is this classification correct?", default=True)

            if not response:
                default = suggested_category if suggested_category else ""
                new_category = prompt(
                    "Enter correct account path: ",
                    default=default,
                ).strip()

                if new_category:
                    feedback = f"Classify '{desc}' as {new_category}"
                    try:
                        self.engine.process_feedback(feedback, self.writer)
                        self.processed_feedback += 1
                        logger.info(
                            "Updated classification: %s → %s",
                            account,
                            new_category,
                        )
                    except ClassificationError as e:
                        logger.exception("Invalid category: %s", str(e))
        except Exception as e:
            logger.exception("Error processing transaction: %s", str(e))
            logger.debug("Problematic transaction data: %s", tx)

    def generate_report(self, total: int) -> None:
        """Generate verification session summary."""
        if self.processed_feedback > 0:
            pass

    def main(self) -> None:
        """Interactive verification workflow."""
        samples = self.get_transaction_samples()

        if not samples:
            logger.error("No transactions found for verification")
            return

        for _idx, tx in enumerate(samples, 1):
            self.prompt_for_feedback(tx)

        self.generate_report(len(samples))


if __name__ == "__main__":
    rules_path = Path("import/mercury/classification_rules.json")
    journal_path = Path(
        os.environ.get("LEDGER_FILE", "~/.hledger.journal"),
    ).expanduser()

    if not rules_path.exists():
        logger.error("Missing classification rules at %s", rules_path.resolve())
        sys.exit(1)

    if not journal_path.exists():
        logger.error(
            "Journal file not found at %s (using LEDGER_FILE environment variable)",
            journal_path.resolve(),
        )
        sys.exit(1)

    verifier = ClassificationVerifier(rules_path, journal_path)
    verifier.main()
