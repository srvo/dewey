#!/usr/bin/env python3

import json
import logging
import os
import re
from pathlib import Path
import shutil
import sys
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_classification_rules(rules_file: str) -> dict[str, Any]:
    """Load classification rules from JSON file.

    Args:
    ----
        rules_file: Path to the JSON file containing classification rules.

    Returns:
    -------
        A dictionary containing the classification rules.

    Raises:
    ------
        FileNotFoundError: If the rules file does not exist.
        json.JSONDecodeError: If the rules file is not a valid JSON.

    """
    logger.info("Loading classification rules from %s", rules_file)
    try:
        with open(rules_file) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.exception("Classification rules file not found: %s", rules_file)
        raise
    except json.JSONDecodeError as e:
        logger.exception("Failed to load classification rules: %s", str(e))
        raise


def create_backup(file_path: Path) -> str:
    """Create a backup of the journal file.

    Args:
    ----
        file_path: Path to the journal file.

    Returns:
    -------
        The path to the backup file.

    Raises:
    ------
        Exception: If the backup creation fails.

    """
    backup_path = file_path + ".bak"
    try:
        shutil.copy2(file_path, backup_path)
        logger.debug("Created backup at %s", backup_path)
        return backup_path
    except Exception as e:
        logger.exception("Backup failed for %s: %s", file_path, str(e))
        raise


def classify_transaction(transaction: dict[str, Any], rules: dict[str, Any]) -> str:
    """Classify a transaction based on the provided rules.

    Args:
    ----
        transaction: A dictionary representing the transaction.
        rules: A dictionary containing the classification rules.

    Returns:
    -------
        The category to which the transaction belongs.

    """
    description = transaction["description"].lower()
    for pattern in rules["patterns"]:
        if re.search(pattern["regex"], description):
            return pattern["category"]
    return rules["default_category"]


def process_journal_file(file_path: Path, rules: dict[str, Any]) -> bool:
    """Process a journal file and categorize its transactions.

    Args:
    ----
        file_path: Path to the journal file.
        rules: A dictionary containing the classification rules.

    Returns:
    -------
        True if the processing was successful, False otherwise.

    """
    logger.info("Processing journal file: %s", file_path)

    try:
        backup_path = create_backup(file_path)
    except Exception:
        return False

    try:
        with open(file_path) as f:
            journal = json.load(f)
    except Exception as e:
        logger.exception("Failed to load journal file: %s", str(e))
        return False

    modified = False
    for trans in journal["transactions"]:
        if "category" not in trans:
            new_category = classify_transaction(trans, rules)
            trans["category"] = new_category
            modified = True

            logger.debug(
                "Classifying transaction: %s ($%.2f)",
                trans["description"],
                trans["amount"],
            )
            logger.debug("Classified as: %s", new_category)

    if modified:
        try:
            with open(file_path, "w") as f:
                json.dump(journal, f, indent=4)
            logger.info("Journal file updated: %s", file_path)
        except Exception as e:
            logger.exception("Failed to update journal file: %s", str(e))
            # Restore from backup
            try:
                shutil.copy2(backup_path, file_path)
                logger.warning("Journal file restored from backup.")
            except Exception as restore_e:
                logger.exception(
                    "Failed to restore journal from backup: %s",
                    str(restore_e),
                )
            return False

    return True


def process_by_year_files(base_dir: Path, rules: dict[str, Any]) -> None:
    """Process all journal files within a base directory, organized by year.

    Args:
    ----
        base_dir: The base directory containing the journal files.
        rules: A dictionary containing the classification rules.

    """
    for year_dir in os.listdir(base_dir):
        year_path = os.path.join(base_dir, year_dir)
        if os.path.isdir(year_path):
            for filename in os.listdir(year_path):
                if filename.endswith(".json"):
                    file_path = os.path.join(year_path, filename)
                    process_journal_file(file_path, rules)


def main() -> int:
    """Main function to process all journal files.

    Returns
    -------
        0 if the process was successful, 1 otherwise.

    """
    logger.info("Starting transaction categorization")

    base_dir = os.environ.get("JOURNAL_BASE_DIR", ".")
    rules_file = os.environ.get("CLASSIFICATION_RULES", "classification_rules.json")

    logger.info("Using base directory: %s", base_dir)
    logger.info("Using classification rules file: %s", rules_file)

    try:
        rules = load_classification_rules(rules_file)
        logger.info(
            "Processing files with %d classification patterns",
            len(rules["patterns"]),
        )
        process_by_year_files(base_dir, rules)
    except Exception as e:
        logger.error("Categorization failed: %s", str(e), exc_info=True)
        return 1

    logger.info("Transaction categorization completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
