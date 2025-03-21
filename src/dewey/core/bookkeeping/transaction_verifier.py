#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm

from dewey.core.base_script import BaseScript
from dewey.core.bookkeeping.classification_engine import (
    ClassificationEngine,
    ClassificationError,
)
from dewey.core.bookkeeping.writers.journal_writer_fab1858b import (
    JournalWriter,
)


class LLMClientInterface(Protocol):
    """Interface for LLM clients."""

    def classify_text(self, text: str, instructions: str) -> Optional[str]:
        """Classify text using the LLM."""
        ...


class ClassificationVerifier(BaseScript):
    """Verifies transaction classifications and allows for correction via user feedback."""

    def __init__(
        self,
        classification_engine: Optional[ClassificationEngine] = None,
        journal_writer: Optional[JournalWriter] = None,
        llm_client: Optional[LLMClientInterface] = None,
    ) -> None:
        """Initializes the ClassificationVerifier."""
        super().__init__(config_section="bookkeeping")
        self.rules_path = self.get_path(
            self.get_config_value("rules_path", "import/mercury/classification_rules.json")
        )
        self.journal_path = self.get_path(
            self.get_config_value("journal_path", "~/.hledger.journal")
        ).expanduser()
        self.engine = classification_engine or ClassificationEngine(self.rules_path)
        self.writer = journal_writer or JournalWriter(self.journal_path.parent)
        self.processed_feedback = 0
        self.llm_client = llm_client or self.llm_client

        if not self.rules_path.exists():
            self.logger.error("Missing classification rules at %s", self.rules_path.resolve())
            sys.exit(1)

        if not self.journal_path.exists():
            self.logger.error(
                "Journal file not found at %s (using LEDGER_FILE environment variable)",
                self.journal_path.resolve(),
            )
            sys.exit(1)

    @property
    def valid_categories(self) -> List[str]:
        """Get valid classification categories from engine.

        Returns:
            list[str]: List of valid classification categories.
        """
        return self.engine.categories

    def get_ai_suggestion(self, description: str) -> str:
        """Get AI classification suggestion using an LLM.

        Args:
            description (str): Transaction description.

        Returns:
            str: AI classification suggestion.
        """
        try:
            instructions = "Return ONLY the account path as category1:category2"
            response = self.llm_client.classify_text(  # type: ignore
                text=f"Classify transaction: '{description}'",
                instructions=instructions,
            )
            return response if response else ""
        except Exception as e:
            self.logger.exception("AI classification failed: %s", str(e))
            return ""

    def _process_hledger_csv(self, csv_data: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Process hledger CSV data using DuckDB.

        Args:
            csv_data (str): CSV data from hledger.
            limit (int, optional): Maximum number of transactions to retrieve. Defaults to 50.

        Returns:
            List[Dict[str, Any]]: List of transaction dictionaries.
        """
        try:
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
                    [csv_data],
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
            self.logger.exception("DuckDB processing failed: %s", str(e))
            return []

    def get_transaction_samples(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get sample transactions using hledger + DuckDB.

        Args:
            limit (int, optional): Maximum number of transactions to retrieve. Defaults to 50.

        Returns:
            list[dict]: List of transaction dictionaries.
        """
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
                self.logger.error("hledger export failed: %s", result.stderr)
                return []

            return self._process_hledger_csv(result.stdout, limit)

        except Exception as e:
            self.logger.exception("DuckDB processing failed: %s", str(e))
            return []
        finally:
            pass

    def prompt_for_feedback(self, tx: Dict[str, Any]) -> None:
        """Interactive prompt for transaction verification.

        Args:
            tx (dict): Transaction dictionary.
        """
        if not isinstance(tx, dict):
            self.logger.error("Invalid transaction format - expected dict, got %s", type(tx))
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
                        self.logger.info(
                            "Updated classification: %s → %s",
                            account,
                            new_category,
                        )
                    except ClassificationError as e:
                        self.logger.exception("Invalid category: %s", str(e))
        except Exception as e:
            self.logger.exception("Error processing transaction: %s", str(e))
            self.logger.debug("Problematic transaction data: %s", tx)

    def generate_report(self, total: int) -> None:
        """Generate verification session summary.

        Args:
            total (int): Total number of transactions processed.
        """
        if self.processed_feedback > 0:
            pass

    def run(self) -> None:
        """Interactive verification workflow."""
        samples = self.get_transaction_samples()

        if not samples:
            self.logger.error("No transactions found for verification")
            return

        for _idx, tx in enumerate(samples, 1):
            self.prompt_for_feedback(tx)

        self.generate_report(len(samples))


if __name__ == "__main__":
    verifier = ClassificationVerifier()
    verifier.execute()
