#!/usr/bin/env python3

import os
from pathlib import Path
from typing import IO, Dict, List, Protocol

from dewey.core.base_script import BaseScript


class FileSystemInterface(Protocol):
    """Interface for file system operations."""

    def open(self, path: str, mode: str = "r") -> IO:
        ...

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        ...

    def basename(self, path: str) -> str:
        ...

    def join(self, path1: str, path2: str) -> str:
        ...

    def listdir(self, path: str) -> List[str]:
        ...


class RealFileSystem:
    """Real file system operations."""

    def open(self, path: str, mode: str = "r") -> IO:
        return open(path, mode)

    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        Path(path).mkdir(parents=parents, exist_ok=exist_ok)

    def basename(self, path: str) -> str:
        return os.path.basename(path)

    def join(self, path1: str, path2: str) -> str:
        return os.path.join(path1, path2)

    def listdir(self, path: str) -> List[str]:
        return os.listdir(path)


class ConfigInterface(Protocol):
    """Interface for configuration."""

    def get_config_value(self, key: str) -> str:
        ...


class JournalSplitter(BaseScript):
    """
    Splits a journal file into separate files by year.
    """

    def __init__(self, file_system: FileSystemInterface = None, config: ConfigInterface = None) -> None:
        """Initializes the JournalSplitter."""
        super().__init__(config_section='bookkeeping')
        self.file_system: FileSystemInterface = file_system or RealFileSystem()
        self.config: ConfigInterface = config or self  # type: ignore[assignment]

    def _process_transaction_line(self, line: str, bank_account: str) -> str:
        """Processes a single transaction line, replacing generic accounts."""
        if "expenses:unknown" in line:
            line = line.replace("expenses:unknown", "expenses:unclassified")
        if "income:unknown" in line:
            line = line.replace("income:unknown", bank_account)
        return line

    def _extract_year(self, line: str) -> str | None:
        """Extracts the year from a transaction line."""
        try:
            return line.split("-")[0]
        except Exception:
            return None

    def split_journal_by_year(self, input_file: str, output_dir: str) -> None:
        """Split a journal file into separate files by year.

        Args:
            input_file: Path to the input journal file.
            output_dir: Path to the output directory.

        Returns:
            None
        """
        # Create output directory if it doesn't exist
        self.file_system.mkdir(output_dir, parents=True, exist_ok=True)

        # Get account number from filename
        account_num = self.file_system.basename(input_file).split("_")[1].split(".")[0]
        bank_account = f"assets:checking:mercury{account_num}"

        # Initialize files dict to store transactions by year
        files: Dict[str, IO] = {}
        current_year: str | None = None
        current_transaction: List[str] = []

        with self.file_system.open(input_file) as f:
            for line in f:
                # Check if this is a new transaction (starts with a date)
                if line.strip() and line[0].isdigit():
                    # If we have a previous transaction, write it
                    if current_transaction and current_year:
                        if current_year not in files:
                            output_file = self.file_system.join(
                                output_dir,
                                f"{self.file_system.basename(input_file).replace('.journal', '')}_{current_year}.journal",
                            )
                            files[current_year] = self.file_system.open(output_file, "w")
                        files[current_year].write("".join(current_transaction))

                    # Start new transaction
                    current_transaction = [line]
                    current_year = self._extract_year(line)
                else:
                    # Continue current transaction
                    if line.strip():
                        line = self._process_transaction_line(line, bank_account)
                    current_transaction.append(line)

        # Write last transaction
        if current_transaction and current_year:
            if current_year not in files:
                output_file = self.file_system.join(
                    output_dir,
                    f"{self.file_system.basename(input_file).replace('.journal', '')}_{current_year}.journal",
                )
                files[current_year] = self.file_system.open(output_file, "w")
            files[current_year].write("".join(current_transaction))

        # Close all files
        for f in files.values():
            f.close()

    def run(self) -> None:
        """Process all journal files."""
        input_dir = self.config.get_config_value("bookkeeping.journal_dir")
        output_dir = self.file_system.join(input_dir, "by_year")

        # Process each journal file
        for file in self.file_system.listdir(input_dir):
            if file.endswith(".journal") and not file.startswith("."):
                input_file = self.file_system.join(input_dir, file)
                self.logger.info(f"Splitting journal file: {input_file}")
                self.split_journal_by_year(input_file, output_dir)
                self.logger.info(f"Journal file split: {input_file}")

    def get_config_value(self, key: str) -> str:
        """Get a config value."""
        return super().get_config_value(key)


def main() -> None:
    """Main entrypoint for the script."""
    splitter = JournalSplitter()
    splitter.execute()


if __name__ == "__main__":
    main()
