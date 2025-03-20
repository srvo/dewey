import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from dewey.core.base_script import BaseScript


class JournalWriteError(Exception):
    """Exception for journal writing failures."""


class JournalWriter(BaseScript):
    """Handles journal file writing and management."""

    def __init__(self, output_dir: Union[str, Path]) -> None:
        """Initializes the JournalWriter.

        Args:
            output_dir: The directory to write journal files to.
        """
        super().__init__(config_section="bookkeeping")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_hashes_file = self.output_dir / ".processed_hashes"
        self.seen_hashes: set[str] = self._load_processed_hashes()
        self.audit_log: List[Dict[str, str]]=None):
                if str]] is None:
                    str]] = []

    def run(self) -> None:
        """Runs the journal writer script.

        This method contains the core logic for writing journal entries.
        """
        self.logger.info("JournalWriter run method called.")
        # TODO: Implement actual script logic here

    def _load_processed_hashes(self) -> set[str]:
        """Load previously processed transaction hashes.

        Returns:
            A set of processed transaction hashes.
        """
        try:
            if self.processed_hashes_file.exists(
                with open(self.processed_hashes_file) as f:
                    return set(f.read().splitlines())
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
            with open(self.processed_hashes_file, "w") as f:
                f.write("\n".join(seen_hashes))
        except Exception as e:
            self.logger.exception(f"Failed to save processed hashes: {e!s}")

    def _write_file_with_backup(self, filename: Path, entries: List[str]) -> None:
        """Write file with versioned backup if it exists.

        Args:
            filename: Path to the file to write.
            entries: List of journal entries to write.
        """
        try:
            if filename.exists():
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                backup_name = f"{filename.stem}_{timestamp}{filename.suffix}"
                shutil.copy(filename, filename.parent / backup_name)

            with open(filename, "a", encoding="utf-8") as f:
                f.write("\n".join(entries) + "\n")
        except Exception as e:
            self.logger.exception(f"Failed to write file with backup: {e!s}")

    def _group_entries_by_account_and_year(
        self,
        entries: Dict[str, List[str]],
    ) -> Dict[Tuple[str, str], List[str]]:
        """Organize entries by account ID and year.

        Args:
            entries: Dictionary of journal entries, keyed by year.

        Returns:
            A dictionary of grouped entries, keyed by (account_id, year).
        """
        grouped: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        for year, entries in entries.items():
            for entry in entries:
                # Extract account ID from entry metadata
                account_id = self.get_config_value("default_account_id", "8542")  # TODO: Get from transaction data
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
