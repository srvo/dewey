#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Protocol
from collections.abc import Callable

from dewey.core.base_script import BaseScript


class FileSystemInterface(Protocol):
    """Interface for file system operations."""

    def open(self, path: Path, mode: str = "r") -> object:
        """Open a file."""
        ...

    def exists(self, path: Path) -> bool:
        """Check if a file exists."""
        ...


class RealFileSystem:
    """Real file system operations."""

    def open(self, path: Path, mode: str = "r") -> object:
        """Open a file."""
        return open(path, mode)

    def exists(self, path: Path) -> bool:
        """Check if a file exists."""
        return path.exists()


class AccountValidator(BaseScript):
    """Validates accounts in the Hledger journal against predefined rules.

    Inherits from BaseScript for standardized configuration and logging.
    """

    def __init__(self, fs: FileSystemInterface = RealFileSystem()) -> None:
        """Initializes the AccountValidator with bookkeeping configuration."""
        super().__init__(config_section="bookkeeping")
        self.fs: FileSystemInterface = fs

    def load_rules(self, rules_file: Path) -> dict:
        """Load classification rules from a JSON file.

        Args:
            rules_file: The path to the JSON rules file.

        Returns:
            A dictionary containing the classification rules.

        Raises:
            Exception: If the rules file cannot be loaded.

        """
        try:
            with self.fs.open(rules_file) as f:
                return json.load(f)
        except Exception as e:
            self.logger.exception(f"Failed to load rules: {e!s}")
            raise

    def validate_accounts(
        self,
        journal_file: Path,
        rules: dict,
        run_command: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ) -> bool:
        """Verify that all accounts in the rules exist in the journal file.

        Args:
            journal_file: The path to the hledger journal file.
            rules: A dictionary containing the classification rules.
            run_command: A function to run a subprocess command.

        Returns:
            True if all accounts are valid, False otherwise.

        Raises:
            Exception: If the hledger command fails or account validation fails.

        """
        try:
            # Get both declared and used accounts
            result = run_command(
                ["hledger", "accounts", "-f", journal_file, "--declared", "--used"],
                capture_output=True,
                text=True,
                check=True,
            )
            existing_accounts = set(result.stdout.splitlines())

            # Check all categories from rules
            missing: list[str] = [
                acc for acc in rules["categories"] if acc not in existing_accounts
            ]

            if missing:
                self.logger.error("Missing accounts required for classification:")
                for acc in missing:
                    self.logger.error(f"  {acc}")
                self.logger.error(
                    "\nAdd these account declarations to your journal file:"
                )
                for acc in missing:
                    self.logger.error(f"account {acc}")
                return False

            return True
        except subprocess.CalledProcessError as e:
            self.logger.exception(f"Hledger command failed: {e!s}")
            raise
        except Exception as e:
            self.logger.exception(f"Account validation failed: {e!s}")
            raise

    def execute(self) -> None:
        """Main function to execute the hledger classification process."""
        if len(sys.argv) != 3:
            self.logger.error("Usage: account_validator.py <journal_file> <rules_file>")
            sys.exit(1)

        journal_file = Path(sys.argv[1])
        rules_file = Path(sys.argv[2])

        if not self.fs.exists(journal_file):
            self.logger.error(f"Journal file not found: {journal_file}")
            sys.exit(1)

        if not self.fs.exists(rules_file):
            self.logger.error(f"Rules file not found: {rules_file}")
            sys.exit(1)

        rules = self.load_rules(rules_file)
        if not self.validate_accounts(journal_file, rules):
            sys.exit(1)


if __name__ == "__main__":
    validator = AccountValidator()
    validator.execute()
