#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict

# from dewey.config import logging  # Centralized logging

# File header: Validates accounts in the Hledger journal against predefined rules.


def load_rules(rules_file: Path) -> Dict:
    """Load classification rules from a JSON file.

    Args:
        rules_file (Path): The path to the JSON rules file.

    Returns:
        Dict: A dictionary containing the classification rules.

    Raises:
        SystemExit: If the rules file cannot be loaded.
    """
    try:
        with open(rules_file) as f:  # type: ignore
            return json.load(f)
    except Exception as e:
        logger.exception(f"Failed to load rules: {e!s}")
        sys.exit(1)


def validate_accounts(journal_file: Path, rules: Dict) -> bool:
    """Verify that all accounts in the rules exist in the journal file.

    Args:
        journal_file (Path): The path to the hledger journal file.
        rules (Dict): A dictionary containing the classification rules.

    Returns:
        bool: True if all accounts are valid, False otherwise.
    """
    try:
        # Get both declared and used accounts
        result = subprocess.run(  # type: ignore
            ["hledger", "accounts", "-f", journal_file, "--declared", "--used"],
            capture_output=True,
            text=True,
            check=True,
        )
        existing_accounts = set(result.stdout.splitlines())

        # Check all categories from rules
        missing = [acc for acc in rules["categories"] if acc not in existing_accounts]

        if missing:
            logger.error("Missing accounts required for classification:")
            for acc in missing:
                logger.error(f"  {acc}")
            logger.error("\nAdd these account declarations to your journal file:")
            for acc in missing:
                logger.error(f"account {acc}")
            return False

        return True
    except Exception as e:
        logger.exception(f"Account validation failed: {e!s}")
        return False


def main() -> None:
    """Main function to execute the hledger classification process."""
    if len(sys.argv) != 3:  # type: ignore
        sys.exit(1)

    journal_file = Path(sys.argv[1])
    rules_file = Path(sys.argv[2])

    if not journal_file.exists():
        logger.error(f"Journal file not found: {journal_file}")
        sys.exit(1)

    if not rules_file.exists():
        logger.error(f"Rules file not found: {rules_file}")
        sys.exit(1)

    rules = load_rules(rules_file)

    if not validate_accounts(journal_file, rules):
        sys.exit(1)


if __name__ == "__main__":
    main()  # type: ignore
