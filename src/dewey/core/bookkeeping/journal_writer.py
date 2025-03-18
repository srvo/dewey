import shutil
from collections import defaultdict
from typing import Any
from datetime import datetime
from pathlib import Path
from dewey.utils import get_logger

class JournalWriteError(Exception):
    """Exception for journal writing failures."""


def _load_processed_hashes(processed_hashes_file: Path) -> set[str]:
    """Load previously processed transaction hashes."""
    logger = get_logger('journal_writer')
    
    try:
        if processed_hashes_file.exists():
            with open(processed_hashes_file) as f:
                return set(f.read().splitlines())
        return set()
    except Exception as e:
        logger.exception(f"Failed to load processed hashes: {str(e)}")
        return set()


def _save_processed_hashes(processed_hashes_file: Path, seen_hashes: set[str]) -> None:
    """Persist processed hashes between runs."""
    logger = get_logger('journal_writer')
    
    try:
        with open(processed_hashes_file, 'w') as f:
            f.write('\n'.join(sorted(seen_hashes)))
        logger.debug(f"Saved {len(seen_hashes)} processed hashes")
    except Exception as e:
        logger.exception(f"Failed to save processed hashes: {str(e)}")
        raise JournalWriteError(f"Failed to save processed hashes: {str(e)}")


def _write_file_with_backup(filename: Path, entries: list[str]) -> None:
    """Write entries to file with backup of existing file."""
    logger = get_logger('journal_writer')
    
    try:
        # Create backup if file exists
        if filename.exists():
            backup = filename.with_suffix('.bak')
            shutil.copy2(filename, backup)
            logger.debug(f"Created backup at {backup}")
        
        # Write new content
        with open(filename, 'w') as f:
            f.write('\n'.join(entries))
        logger.info(f"Wrote {len(entries)} entries to {filename}")
        
    except Exception as e:
        logger.exception(f"Failed to write file {filename}: {str(e)}")
        raise JournalWriteError(f"Failed to write file {filename}: {str(e)}")


def _group_entries_by_account_and_year(
    entries: dict[str, list[str]],
) -> dict[tuple[str, str], list[str]]:
    """Group journal entries by account and year."""
    logger = get_logger('journal_writer')
    grouped = defaultdict(list)
    
    try:
        for account, account_entries in entries.items():
            for entry in account_entries:
                # Extract year from first line of entry
                first_line = entry.split('\n')[0]
                try:
                    date_str = first_line.split()[0]
                    year = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y')
                    grouped[(account, year)].append(entry)
                except (IndexError, ValueError) as e:
                    logger.warning(f"Could not parse date from entry: {first_line}")
                    continue
                    
        logger.debug(f"Grouped entries into {len(grouped)} account-year combinations")
        return dict(grouped)
        
    except Exception as e:
        logger.exception(f"Error grouping entries: {str(e)}")
        raise JournalWriteError(f"Error grouping entries: {str(e)}")


class JournalWriter:
    """Handles writing and organizing journal entries."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.logger = get_logger('journal_writer')
        self.processed_hashes_file = self.output_dir / '.processed_hashes'
        self.seen_hashes = _load_processed_hashes(self.processed_hashes_file)
        self.classifications = defaultdict(lambda: defaultdict(int))
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Initialized journal writer with output directory: {output_dir}")

    def write_entries(self, entries: dict[str, list[str]]) -> None:
        """Write journal entries to appropriate files."""
        try:
            # Group entries by account and year
            grouped = _group_entries_by_account_and_year(entries)
            
            # Write each group to its own file
            for (account, year), group_entries in grouped.items():
                filename = self.output_dir / f"{account}_{year}.journal"
                _write_file_with_backup(filename, group_entries)
            
            # Save processed hashes
            _save_processed_hashes(self.processed_hashes_file, self.seen_hashes)
            
            self.logger.info(f"Successfully wrote entries to {len(grouped)} files")
            
        except Exception as e:
            self.logger.exception(f"Failed to write entries: {str(e)}")
            raise JournalWriteError(f"Failed to write entries: {str(e)}")

    def log_classification_decision(
        self,
        tx_hash: str,
        pattern: str,
        category: str,
    ) -> None:
        """Log a classification decision for reporting."""
        try:
            if tx_hash not in self.seen_hashes:
                self.seen_hashes.add(tx_hash)
                self.classifications[pattern][category] += 1
                self.logger.debug(
                    f"Logged classification: {pattern} -> {category} (hash: {tx_hash})"
                )
        except Exception as e:
            self.logger.exception(f"Failed to log classification: {str(e)}")

    def get_classification_report(self) -> dict[str, Any]:
        """Generate a report of classification decisions."""
        try:
            report = {
                'total_transactions': len(self.seen_hashes),
                'patterns': {
                    pattern: dict(categories)
                    for pattern, categories in self.classifications.items()
                }
            }
            self.logger.debug(f"Generated classification report: {report}")
            return report
        except Exception as e:
            self.logger.exception(f"Failed to generate classification report: {str(e)}")
            return {
                'total_transactions': 0,
                'patterns': {},
                'error': str(e)
            }
