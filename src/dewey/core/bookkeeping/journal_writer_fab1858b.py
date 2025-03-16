import logging
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class JournalWriteError(Exception):
    """Exception for journal writing failures."""


def _load_processed_hashes(processed_hashes_file: Path) -> set[str]:
    """Load previously processed transaction hashes.

    Args:
    ----
        processed_hashes_file: Path to the file containing processed hashes.

    Returns:
    -------
        A set of processed transaction hashes.

    """
    if processed_hashes_file.exists():
        with open(processed_hashes_file) as f:
            return set(f.read().splitlines())
    return set()


def _save_processed_hashes(processed_hashes_file: Path, seen_hashes: set[str]) -> None:
    """Persist processed hashes between runs.

    Args:
    ----
        processed_hashes_file: Path to the file to save processed hashes.
        seen_hashes: Set of processed transaction hashes to save.

    """
    with open(processed_hashes_file, "w") as f:
        f.write("\n".join(seen_hashes))


def _write_file_with_backup(filename: Path, entries: list[str]) -> None:
    """Write file with versioned backup if it exists.

    Args:
    ----
        filename: Path to the file to write.
        entries: List of journal entries to write.

    """
    if filename.exists():
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_name = f"{filename.stem}_{timestamp}{filename.suffix}"
        shutil.copy(filename, filename.parent / backup_name)

    with open(filename, "a", encoding="utf-8") as f:
        f.write("\n".join(entries) + "\n")


def _group_entries_by_account_and_year(
    entries: dict[str, list[str]],
) -> dict[tuple[str, str], list[str]]:
    """Organize entries by account ID and year.

    Args:
    ----
        entries: Dictionary of journal entries, keyed by year.

    Returns:
    -------
        A dictionary of grouped entries, keyed by (account_id, year).

    """
    grouped = defaultdict(list)
    for year, entries in entries.items():
        for entry in entries:
            # Extract account ID from entry metadata
            account_id = "8542"  # TODO: Get from transaction data
            grouped[(account_id, year)].append(entry)
    return grouped


class JournalWriter:
    """Handles journal file writing and management."""

    def __init__(self, output_dir: Path) -> None:
        """Initializes the JournalWriter.

        Args:
        ----
            output_dir: The directory to write journal files to.

        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_hashes_file = output_dir / ".processed_hashes"
        self.seen_hashes: set[str] = _load_processed_hashes(self.processed_hashes_file)
        self.audit_log: list[dict[str, str]] = []

    def write_entries(self, entries: dict[str, list[str]]) -> None:
        """Write journal entries to appropriate files.

        Args:
        ----
            entries: Dictionary of journal entries, keyed by year.

        """
        total_entries = sum(len(e) for e in entries.values())
        logger.info("Writing %d journal entries", total_entries)

        for (account_id, year), entries in _group_entries_by_account_and_year(
            entries,
        ).items():
            filename = self.output_dir / f"{account_id}_{year}.journal"
            _write_file_with_backup(filename, entries)

        _save_processed_hashes(self.processed_hashes_file, self.seen_hashes)

    def log_classification_decision(
        self,
        tx_hash: str,
        pattern: str,
        category: str,
    ) -> None:
        """Record classification decisions for quality tracking.

        Args:
        ----
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

    def get_classification_report(self) -> dict[str, any]:
        """Generate classification quality metrics.

        Returns
        -------
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
