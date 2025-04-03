import fnmatch
import hashlib
import os
from typing import Dict, List, Protocol, runtime_checkable


@runtime_checkable
class FileSystemInterface(Protocol):
    """Interface for file system operations."""

    def walk(self, directory: str) -> object:  # type: ignore
        """Walks through a directory."""
        ...

    def open(self, path: str, mode: str = "r") -> object:
        """Opens a file."""
        ...


class RealFileSystem:
    """Real file system operations."""

    def walk(self, directory: str) -> object:  # type: ignore
        """Walks through a directory."""
        return os.walk(directory)

    def open(self, path: str, mode: str = "r") -> object:
        """Opens a file."""
        return open(path, mode)


from dewey.core.base_script import BaseScript


def calculate_file_hash(file_content: bytes) -> str:
    """Calculates the SHA256 hash of a file's content."""
    return hashlib.sha256(file_content).hexdigest()


class DuplicateChecker(BaseScript):
    """Checks for duplicate ledger files in a directory."""

    def __init__(
        self,
        file_system: FileSystemInterface = RealFileSystem(),
        ledger_dir: str | None = None,
    ) -> None:
        """Initializes the DuplicateChecker with the 'bookkeeping' config section."""
        super().__init__(config_section="bookkeeping")
        self.file_system = file_system
        self.ledger_dir = (
            ledger_dir
            if ledger_dir is not None
            else self.get_config_value("ledger_dir", "data/bookkeeping/ledger")
        )

    def find_ledger_files(self) -> dict[str, list[str]]:
        """Finds all ledger files and calculates their hashes.

        Returns:
            A dictionary where keys are file hashes and values are lists of
            filepaths with that hash.

        """
        hashes: dict[str, list[str]] = {}
        for root, _dirnames, filenames in self.file_system.walk(self.ledger_dir):
            for filename in fnmatch.filter(filenames, "*.journal"):
                filepath = os.path.join(root, filename)
                try:
                    with self.file_system.open(filepath, "rb") as f:
                        file_hash = calculate_file_hash(f.read())
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

    def execute(self) -> None:
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
