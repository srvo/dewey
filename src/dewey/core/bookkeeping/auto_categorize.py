#!/usr/bin/env python3
import fnmatch
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from dewey.config import load_config, logging  # Centralized logging
from dewey.core.base_script import BaseScript
from dewey.core.db.connection import (DatabaseConnection,
                                       get_connection,
                                       get_motherduck_connection)
from dewey.core.db.utils import (create_table, execute_query,
                                  table_exists)  # Schema operations and query building
from dewey.llm.llm_utils import get_llm_client  # LLM utilities


class JournalProcessor(BaseScript):
    """
    Automatically categorizes transactions based on predefined rules.
    """

    def __init__(self) -> None:
        """Initializes the JournalProcessor."""
        super().__init__(config_section='bookkeeping')

        # Use self.config for configuration values
        self.rule_sources: List[Tuple[str, int]] = [
            ("overrides.json", 0),  # Highest priority
            ("manual_rules.json", 1),
            ("base_rules.json", 2),  # Lowest priority
        ]

        # TODO: Fix search/replace block

        # Use self.config for file paths
        self.classification_file: Path = Path(self.get_config_value("classification_file", str(Path.home() / "books/import/mercury/classification_rules.json")))
        self.ledger_file: Path = Path(self.get_config_value("ledger_file", str(Path.home() / ".hledger.journal")))
        self.backup_ext: str = self.get_config_value("backup_ext", ".bak")

    def load_classification_rules(self) -> Dict:
        """Load classification rules from JSON files.

        Returns:
            A dictionary containing the classification rules.
        """
        self.logger.info("Loading classification rules")
        return {}  # Placeholder

    def process_transactions(self, transactions: List[Dict], rules: Dict) -> List[Dict]:
        """Process transactions and categorize them based on rules.

        Args:
            transactions: A list of transaction dictionaries.
            rules: A dictionary containing the classification rules.

        Returns:
            A list of processed transaction dictionaries.
        """
        self.logger.info("Processing transactions")
        return transactions  # Placeholder

    def parse_journal_entries(self, file_path: Path) -> List[Dict]:
        """Parse hledger journal file into structured transactions.

        Args:
            file_path: The path to the hledger journal file.

        Returns:
            A list of structured transactions.
        """
        self.logger.info(f"Parsing journal file: {file_path}")

        with open(file_path) as f:
            content = f.read()

        transactions = []
        current_tx: Dict[str, Any] = {"postings": []}

        for line in content.split("\n"):
            line = line.rstrip()
            if not line:
                if current_tx.get("postings"):
                    transactions.append(current_tx)
                    current_tx = {"postings": []}
                continue

            if not current_tx.get("date"):
                # Transaction header line
                date_match = re.match(r"^(\d{4}-\d{2}-\d{2})(\s+.*?)$", line)
                if date_match:
                    current_tx["date"] = date_match.group(1)
                    current_tx["description"] = date_match.group(2).strip()
                continue

            # Parse posting lines
            if line.startswith("    "):
                parts = re.split(r"\s{2,}", line.strip(), 1)
                account = parts[0].strip()
                amount = parts[1].strip() if len(parts) > 1 else ""
                current_tx["postings"].append({"account": account, "amount": amount})

        if current_tx.get("postings"):
            transactions.append(current_tx)

        self.logger.info(f"Found {len(transactions)} transactions")
        return transactions

    def serialize_transactions(self, transactions: List[Dict]) -> str:
        """Convert structured transactions back to journal format.

        Args:
            transactions: A list of structured transactions.

        Returns:
            A string representation of the transactions in journal format.
        """
        journal_lines = []

        for tx in transactions:
            header = f"{tx['date']} {tx['description']}"
            journal_lines.append(header)

            for posting in tx["postings"]:
                line = f"    {posting['account']}"
                if posting["amount"]:
                    line += f"  {posting['amount']}"
                journal_lines.append(line)

            journal_lines.append("")  # Empty line between transactions

        return "\n".join(journal_lines).strip() + "\n"

    def write_journal_file(self, content: str, file_path: Path) -> None:
        """Write updated journal file with backup.

        Args:
            content: The content to write to the journal file.
            file_path: The path to the journal file.

        Raises:
            Exception: If writing to the journal file fails.
        """
        backup_path = file_path.with_suffix(f".{self.backup_ext}")

        try:
            # Create backup
            self.logger.info(f"Creating backup at {backup_path}")
            shutil.copy2(file_path, backup_path)

            # Write new content
            self.logger.info(f"Writing updated journal to {file_path}")
            with open(file_path, "w") as f:
                f.write(content)

        except Exception as e:
            self.logger.exception(f"Failed to write journal file: {e!s}")
            if backup_path.exists():
                self.logger.info("Restoring from backup")
                shutil.move(backup_path, file_path)
            raise

    def run(self) -> None:
        """Main processing workflow."""
        try:
            # Load configuration
            rules = self.load_classification_rules()

            # Process journal entries
            transactions = self.parse_journal_entries(self.ledger_file)
            updated_transactions = self.process_transactions(transactions, rules)
            new_content = self.serialize_transactions(updated_transactions)

            # Write results
            self.write_journal_file(new_content, self.ledger_file)
            self.logger.info("Successfully updated journal entries")

        except Exception as e:
            self.logger.exception(f"Failed to process journal: {e!s}")
            raise


def main() -> None:
    """Main entrypoint to run the journal processor."""
    processor = JournalProcessor()
    processor.execute()


if __name__ == "__main__":
    main()
