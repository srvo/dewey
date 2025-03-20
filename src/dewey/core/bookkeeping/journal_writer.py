import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union, Callable, Protocol

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class JournalWriteError(Exception):
    """Exception for journal writing failures."""


class IOServiceInterface(Protocol):
    """Interface for file operations."""

    def read_text(self, path: Path) -> str:
        """Read text from a file."""

    def write_text(self, path: Path, text: str) -> None:
        """Write text to a file."""

    def copy_file(self, src: Path, dest: Path) -> None:
        """Copy a file from source to destination."""


class IOService:
    """Default implementation of IOServiceInterface using standard file operations."""

    def read_text(self, path: Path) -> str:
        """Read text from a file."""
        with open(path, "r") as f:
            return f.read()

    def write_text(self, path: Path, text: str) -> None:
        """Write text to a file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def copy_file(self, src: Path, dest: Path) -> None:
        """Copy a file from source to destination."""
        shutil.copy(src, dest)


class ConfigInterface(Protocol):
    """Interface for config operations."""

    def get_config_value(self, key: str, default: Any) -> str:
        """Get a config value."""


class JournalWriter(BaseScript):
    """Handles journal file writing and management."""

    def __init__(
        self,
        io_service: IOServiceInterface | None = None,
        config_source: ConfigInterface | None = None,
    ) -> None:
        """Initializes the JournalWriter."""
        super().__init__(config_section="bookkeeping")
        self.config_source = config_source or self
        self.output_dir: Path = Path(self.config_source.get_config_value("journal_dir", "data/bookkeeping/journals"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_hashes_file: Path = self.output_dir / ".processed_hashes"
        self.io_service: IOServiceInterface = io_service or IOService()
        self.seen_hashes: set[str] = self._load_processed_hashes()
        self.audit_log: List[Dict[str, str]] = []
        self.db_conn: DatabaseConnection | None = None
        self.llm_client: LLMClient | None = None

    def run(self) -> None:
        """Runs the journal writer script.

        This method contains the core logic for writing journal entries.
        """
        self.logger.info("JournalWriter run method called.")
        # TODO: Implement actual script logic here
        # Example usage of config and database:
        example_config_value = self.config_source.get_config_value("utils.example_config", "default_value")
        self.logger.info(f"Example config value: {example_config_value}")

        if self.db_conn:
            try:
                result = self.db_conn.execute("SELECT 1")
                self.logger.info(f"Database connection test: {result}")
            except Exception as e:
                self.logger.error(f"Error connecting to the database: {e}")

    def _load_processed_hashes(self) -> set[str]:
        """Load previously processed transaction hashes.

        Returns:
            A set of processed transaction hashes.
        """
        try:
            if self.processed_hashes_file.exists():
                content = self.io_service.read_text(self.processed_hashes_file)
                return set(content.splitlines())
            return set()
        except Exception as e:
            self.logger.exception(f"Failed to load processed hashes: {e!s}")
            return set()

    def _save_processed_hashes(self, seen_hashes: set[str]) -> None:
        """Persist processed hashes between runs.

        Args:
            seen_hashes: Set of processed transaction hashes to save.
        """
        try:
            self.io_service.write_text(self.processed_hashes_file, "\n".join(seen_hashes))
        except Exception as e:
            self.logger.exception(f"Failed to save processed hashes: {e!s}")

    def _write_file_with_backup(
        self,
        filename: Path,
        entries: List[str],
        now_func: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Write file with versioned backup if it exists.

        Args:
            filename: Path to the file to write.
            entries: List of journal entries to write.
            now_func: Function to get the current datetime (for testing).
        """
        try:
            if filename.exists():
                timestamp = now_func().strftime("%Y%m%d%H%M%S")
                backup_name = f"{filename.stem}_{timestamp}{filename.suffix}"
                self.io_service.copy_file(filename, filename.parent / backup_name)

            self.io_service.write_text(filename, "\n".join(entries) + "\n")
        except Exception as e:
            self.logger.exception(f"Failed to write file with backup: {e!s}")

    def _get_account_id(self) -> str:
        """Get the account ID from the config."""
        return self.config_source.get_config_value("default_account_id", "8542")

    def _group_entries_by_account_and_year(
        self,
        entries: Dict[str, List[str]],
        get_account_id: Callable[[], str] | None = None,
    ) -> Dict[Tuple[str, str], List[str]]:
        """Organize entries by account ID and year.

        Args:
            entries: Dictionary of journal entries, keyed by year.
            get_account_id: Function to retrieve the account ID.

        Returns:
            A dictionary of grouped entries, keyed by (account_id, year).
        """
        grouped: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        get_account_id = get_account_id or self._get_account_id
        for year, entries in entries.items():
            for entry in entries:
                # Extract account ID from entry metadata
                account_id = get_account_id()  # TODO: Get from transaction data
                grouped[(account_id, year)].append(entry)
        return grouped

    def write_entries(self, entries: Dict[str, List[str]]) -> None:
        """Write journal entries to appropriate files.

        Args:
            entries: Dictionary of journal entries, keyed by year.
        """
        total_entries = sum(len(e) for e in entries.values())
        self.logger.info(f"Writing {total_entries} journal entries")

        for (account_id, year), entries in self._group_entries_by_account_and_year(
            entries,
        ).items():
            filename = self.output_dir / f"{account_id}_{year}.journal"
            self._write_file_with_backup(filename, entries)

        self._save_processed_hashes(self.seen_hashes)

    def log_classification_decision(
        self,
        tx_hash: str,
        pattern: str,
        category: str,
    ) -> None:
        """Record classification decisions for quality tracking.

        Args:
            tx_hash: The transaction hash.
            pattern: The pattern that matched.
            category: The category the transaction was classified into.
        """
        self.audit_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "tx_hash": tx_hash,
                "pattern": pattern,
                "category": category,
            },
        )

    def get_classification_report(self) -> Dict[str, Any]:
        """Generate classification quality metrics.

        Returns:
            A dictionary containing classification quality metrics.
        """
        unique_rules = len({entry["pattern"] for entry in self.audit_log})
        categories = [entry["category"] for entry in self.audit_log]

        return {
            "total_transactions": len(self.audit_log),
            "unique_rules_applied": unique_rules,
            "category_distribution": {
                cat: categories.count(cat) for cat in set(categories)
            },
        }


if __name__ == "__main__":
    writer = JournalWriter()
    writer.execute()
