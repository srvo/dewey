#!/usr/bin/env python3
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Protocol, Tuple

from dewey.core.base_script import BaseScript


class FileSystemInterface(Protocol):
    """Interface for file system operations."""

    def open(self, path: Path, mode: str = "r") -> Any: ...

    def copy2(self, src: Path, dst: Path) -> None: ...

    def move(self, src: Path, dst: Path) -> None: ...

    def exists(self, path: Path) -> bool: ...


class RealFileSystem:
    """Real file system operations."""

    def open(self, path: Path, mode: str = "r") -> Any:
        return open(path, mode)

    def copy2(self, src: Path, dst: Path) -> None:
        shutil.copy2(src, dst)

    def move(self, src: Path, dst: Path) -> None:
        shutil.move(src, dst)

    def exists(self, path: Path) -> bool:
        return path.exists()


class RuleLoaderInterface(Protocol):
    """Interface for loading classification rules."""

    def load_rules(self) -> dict: ...


class DatabaseInterface(Protocol):
    """Interface for database operations."""

    def execute(self, query: str) -> list: ...

    def close(self) -> None: ...


class JournalProcessor(BaseScript):
    """Automatically categorizes transactions based on predefined rules."""

    def __init__(
        self,
        file_system: FileSystemInterface = RealFileSystem(),
        rule_loader: RuleLoaderInterface | None = None,
        database: DatabaseInterface | None = None,
    ) -> None:
        """Initializes the JournalProcessor."""
        super().__init__(config_section="bookkeeping")

        self.file_system: FileSystemInterface = file_system
        self.rule_loader: RuleLoaderInterface | None = rule_loader
        self.database: DatabaseInterface | None = database

        # Use self.config for configuration values
        self.rule_sources: list[tuple[str, int]] = [
            ("overrides.json", 0),  # Highest priority
            ("manual_rules.json", 1),
            ("base_rules.json", 2),  # Lowest priority
        ]

        # TODO: Fix search/replace block

        # Use self.config for file paths
        self.classification_file: Path = Path(
            self.get_config_value(
                "classification_file",
                str(Path.home() / "books/import/mercury/classification_rules.json"),
            )
        )
        self.ledger_file: Path = Path(
            self.get_config_value("ledger_file", str(Path.home() / ".hledger.journal"))
        )
        self.backup_ext: str = self.get_config_value("backup_ext", ".bak")

    def load_classification_rules(self) -> dict:
        """Load classification rules from JSON files.

        Returns:
            A dictionary containing the classification rules.

        """
        self.logger.info("Loading classification rules")
        if self.rule_loader:
            return self.rule_loader.load_rules()
        return {}  # Placeholder

    def process_transactions(self, transactions: list[dict], rules: dict) -> list[dict]:
        """Process transactions and categorize them based on rules.

        Args:
            transactions: A list of transaction dictionaries.
            rules: A dictionary containing the classification rules.

        Returns:
            A list of processed transaction dictionaries.

        """
        self.logger.info("Processing transactions")
        return transactions  # Placeholder

    def _parse_journal_entry(self, line: str, current_tx: dict[str, Any]) -> None:
        """Helper function to parse a single line of a journal entry."""
        if not current_tx.get("date"):
            # Transaction header line
            date_match = re.match(r"^(\d{4}-\d{2}-\d{2})(\s+.*?)$", line)
            if date_match:
                current_tx["date"] = date_match.group(1)
                current_tx["description"] = date_match.group(2).strip()
            return

        # Parse posting lines
        if line.startswith("    "):
            parts = re.split(r"\s{2,}", line.strip(), 1)
            account = parts[0].strip()
            amount = parts[1].strip() if len(parts) > 1 else ""
            current_tx["postings"].append({"account": account, "amount": amount})

    def parse_journal_entries(self, file_path: Path) -> list[dict]:
        """Parse hledger journal file into structured transactions.

        Args:
            file_path: The path to the hledger journal file.

        Returns:
            A list of structured transactions.

        """
        self.logger.info(f"Parsing journal file: {file_path}")

        with self.file_system.open(file_path) as f:
            content = f.read()

        transactions: list[dict[str, Any]] = []
        current_tx: dict[str, Any] = {"postings": []}

        for line in content.split("\n"):
            line = line.rstrip()
            if not line:
                if current_tx.get("postings"):
                    transactions.append(current_tx)
                    current_tx = {"postings": []}
                continue

            self._parse_journal_entry(line, current_tx)

        if current_tx.get("postings"):
            transactions.append(current_tx)

        self.logger.info(f"Found {len(transactions)} transactions")
        return transactions

    def serialize_transactions(self, transactions: list[dict]) -> str:
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
            self.file_system.copy2(file_path, backup_path)

            # Write new content
            self.logger.info(f"Writing updated journal to {file_path}")
            with self.file_system.open(file_path, "w") as f:
                f.write(content)

        except Exception as e:
            self.logger.exception(f"Failed to write journal file: {e!s}")
            if self.file_system.exists(backup_path):
                self.logger.info("Restoring from backup")
                self.file_system.move(backup_path, file_path)
            raise

    def execute(self) -> None:
        """Main processing workflow."""
        # Load configuration
        rules = self.load_classification_rules()

        # Process journal entries
        transactions = self.parse_journal_entries(self.ledger_file)
        updated_transactions = self.process_transactions(transactions, rules)
        new_content = self.serialize_transactions(updated_transactions)

        # Write results
        self.write_journal_file(new_content, self.ledger_file)


def main() -> None:
    """Main entrypoint to run the journal processor."""
    processor = JournalProcessor()
    processor.execute()


if __name__ == "__main__":
    main()
