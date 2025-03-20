#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

from dewey.core.base_script import BaseScript


class AccountValidator(BaseScript):
    """Validates accounts in the Hledger journal against predefined rules.

    Inherits from BaseScript for standardized configuration and logging.
    """

    def __init__(self) -> None:
        """Initializes the AccountValidator with bookkeeping configuration."""
        super().__init__(config_section='bookkeeping')

    def load_rules(self, rules_file: Path) -> Dict:
        """Load classification rules from a JSON file.

        Args:
            rules_file: The path to the JSON rules file.

        Returns:
            A dictionary containing the classification rules.

        Raises:
            SystemExit: If the rules file cannot be loaded.
        """
        try:
            with open(rules_file) as f:
                return json.load(f)
        except Exception as e:
            self.logger.exception(f"Failed to load rules: {e!s}")
            sys.exit(1)

    def validate_accounts(self, journal_file: Path, rules: Dict) -> bool:
        """Verify that all accounts in the rules exist in the journal file.

        Args:
            journal_file: The path to the hledger journal file.
            rules: A dictionary containing the classification rules.

        Returns:
            True if all accounts are valid, False otherwise.
        """
        try:
            # Get both declared and used accounts
            result = subprocess.run(
                ["hledger", "accounts", "-f", journal_file, "--declared", "--used"],
                capture_output=True,
                text=True,
                check=True,
            )
            existing_accounts = set(result.stdout.splitlines())

            # Check all categories from rules
            missing: List[str] = [
                acc for acc in rules["categories"] if acc not in existing_accounts
            ]

            if missing:
                self.logger.error("Missing accounts required for classification:")
                for acc in missing:
                    self.logger.error(f"  {acc}")
                self.logger.error("\nAdd these account declarations to your journal file:")
                for acc in missing:
                    self.logger.error(f"account {acc}")
                return False

            return True
        except subprocess.CalledProcessError as e:
            self.logger.exception(f"Hledger command failed: {e!s}")
            return False
        except Exception as e:
            self.logger.exception(f"Account validation failed: {e!s}")
            return False

    def run(self) -> None:
        """Main function to execute the hledger classification process."""
        if len(sys.argv) != 3:
            self.logger.error("Usage: account_validator.py <journal_file> <rules_file>")
            sys.exit(1)

        journal_file = Path(sys.argv[1])
        rules_file = Path(sys.argv[2])

        if not journal_file.exists():
            self.logger.error(f"Journal file not found: {journal_file}")
            sys.exit(1)

        if not rules_file.exists():
            self.logger.error(f"Rules file not found: {rules_file}")
            sys.exit(1)

        rules = self.load_rules(rules_file)

        if not self.validate_accounts(journal_file, rules):
            sys.exit(1)


if __name__ == "__main__":
    validator = AccountValidator()
    validator.run()
