import fnmatch
import hashlib
import os
from typing import Dict, List

from dewey.core.base_script import BaseScript


class DuplicateChecker(BaseScript):
    """Checks for duplicate ledger files in a directory."""

    def __init__(self) -> None:
        """Initializes the DuplicateChecker with the 'bookkeeping' config section."""
        super().__init__(config_section="bookkeeping")

    def find_ledger_files(self) -> Dict[str, List[str]]:
        """Finds all ledger files and calculates their hashes.

        Returns:
            A dictionary where keys are file hashes and values are lists of
            filepaths with that hash.
        """
        hashes: Dict[str, List[str]] = {}
        ledger_dir = self.get_config_value("ledger_dir", "data/bookkeeping/ledger")
        for root, _dirnames, filenames in os.walk(ledger_dir):
            if List[str]] is None:
                List[str]] = {}
        ledger_dir = self.get_config_value("ledger_dir"
            for filename in fnmatch.filter(filenames, "*.journal"):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                        if file_hash not in hashes:
                            hashes[file_hash] = []
                        hashes[file_hash].append(filepath)
                except Exception as e:
                    self.logger.error(f"Error reading file {filepath}: {e}")
                    continue
        return hashes

    def check_duplicates(self) -> bool:
        """Checks for duplicate ledger files.

        Returns:
            True if duplicate files were found, False otherwise.
        """
        hashes = self.find_ledger_files()
        duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}

        if duplicates:
            self.logger.warning(
                f"Found {len(duplicates)} groups of duplicate files: {duplicates}"
            )
            return True
        else:
            self.logger.info("No duplicate ledger files found.")
            return False

    def run(self) -> None:
        """Runs the duplicate check and logs the result."""
        if self.check_duplicates():
            self.logger.error("Duplicate ledger files found.")
        else:
            self.logger.info("No duplicate ledger files found.")


def main():
    """Main entry point for the duplicate checker script."""
    checker = DuplicateChecker()
    checker.run()


if __name__ == "__main__":
    main()
