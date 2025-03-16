#!/usr/bin/env python3

import json
import logging
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_rules(rules_file: Path) -> dict:
    """Load classification rules from a JSON file.

    Args:
    ----
        rules_file: The path to the JSON rules file.

    Returns:
    -------
        A dictionary containing the classification rules.

    Raises:
    ------
        SystemExit: If the rules file cannot be loaded.

    """
    try:
        with open(rules_file) as f:
            return json.load(f)
    except Exception as e:
        logger.exception(f"Failed to load rules: {e!s}")
        sys.exit(1)


def validate_accounts(journal_file: Path, rules: dict) -> bool:
    """Verify that all accounts in the rules exist in the journal file.

    Args:
    ----
        journal_file: The path to the hledger journal file.
        rules: A dictionary containing the classification rules.

    Returns:
    -------
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


def classify_transaction(content: str, pattern: str, rule: dict) -> tuple[str, int]:
    """Classify transactions based on a given pattern and rule.

    Args:
    ----
        content: The content of the journal file.
        pattern: The regex pattern to match transaction descriptions.
        rule: The classification rule to apply.

    Returns:
    -------
        A tuple containing the updated content and the number of replacements made.

    """
    pattern_re = re.compile(
        rf"^(?P<date>\d{{4}}-\d{{2}}-\d{{2}})\s+(?P<desc>.*{pattern}.*)\n"
        rf"(\s{{4}}.*\n)*\s{{4}}Expenses:Unknown\b",
        re.IGNORECASE | re.MULTILINE,
    )

    new_content, count = pattern_re.subn(
        lambda m: f"{m.group('date')} {m.group('desc')}\n    {rule['category']}",
        content,
    )
    return new_content, count


def apply_classification_rules(journal_file: Path, rules: dict) -> dict[str, int]:
    """Apply classification rules to a journal file.

    Args:
    ----
        journal_file: The path to the hledger journal file.
        rules: A dictionary containing the classification rules.

    Returns:
    -------
        A dictionary containing the number of replacements made for each account.

    """
    try:
        with open(journal_file, encoding="utf-8") as f:
            content = f.read()

        replacements: dict[str, int] = defaultdict(int)
        new_content = content

        for pattern, rule in rules["patterns"].items():
            new_content, count = classify_transaction(new_content, pattern, rule)
            if count > 0:
                replacements[rule["category"]] += count

        with open(journal_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        return replacements

    except Exception as e:
        logger.exception(f"Classification failed: {e!s}")
        sys.exit(1)


def log_replacement_results(replacements: dict[str, int]) -> None:
    """Log the results of the classification process.

    Args:
    ----
        replacements: A dictionary containing the number of replacements made for each account.

    """
    logger.info(f"Made {sum(replacements.values())} replacements:")
    for account, count in replacements.items():
        logger.info(f" - {count} => {account}")


def main() -> None:
    """Main function to execute the hledger classification process."""
    if len(sys.argv) != 3:
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

    replacements = apply_classification_rules(journal_file, rules)
    log_replacement_results(replacements)
    logger.info("Classification completed successfully")


if __name__ == "__main__":
    main()
