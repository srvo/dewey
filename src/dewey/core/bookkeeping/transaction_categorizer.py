#!/usr/bin/env python3

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

from dewey.core.base_script import BaseScript


class JournalCategorizer(BaseScript):
    """Categorizes transactions in journal files based on predefined rules."""

    def __init__(self) -> None:
        """Initializes the JournalCategorizer with bookkeeping config."""
        super().__init__(config_section="bookkeeping")

    def load_classification_rules(self, rules_file: str) -> Dict[str, Any]:
        """Load classification rules from JSON file.

        Args:
            rules_file: Path to the JSON file containing classification rules.

        Returns:
            A dictionary containing the classification rules.

        Raises:
            FileNotFoundError: If the rules file does not exist.
            json.JSONDecodeError: If the rules file is not a valid JSON.
        """
        self.logger.info(f"Loading classification rules from {rules_file}")
        try:
            with open(rules_file) as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.exception(
                f"Classification rules file not found: {rules_file}"
            )
            raise
        except json.JSONDecodeError as e:
            self.logger.exception(f"Failed to load classification rules: {str(e)}")
            raise

    def create_backup(self, file_path: Path) -> str:
        """Create a backup of the journal file.

        Args:
            file_path: Path to the journal file.

        Returns:
            The path to the backup file.

        Raises:
            Exception: If the backup creation fails.
        """
        backup_path = str(file_path) + ".bak"
        try:
            shutil.copy2(file_path, backup_path)
            self.logger.debug(f"Created backup at {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.exception(f"Backup failed for {file_path}: {str(e)}")
            raise

    def classify_transaction(self, transaction: Dict[str, Any], rules: Dict[str, Any]) -> str:
        """Classify a transaction based on the provided rules.

        Args:
            transaction: A dictionary representing the transaction.
            rules: A dictionary containing the classification rules.

        Returns:
            The category to which the transaction belongs.
        """
        description = transaction["description"].lower()
        for pattern in rules["patterns"]:
            if re.search(pattern["regex"], description):
                return pattern["category"]
        return rules["default_category"]

    def process_journal_file(self, file_path: str, rules: Dict[str, Any]) -> bool:
        """Process a journal file and categorize its transactions.

        Args:
            file_path: Path to the journal file.
            rules: A dictionary containing the classification rules.

        Returns:
            True if the processing was successful, False otherwise.
        """
        self.logger.info(f"Processing journal file: {file_path}")

        try:
            backup_path = self.create_backup(Path(file_path))
        except Exception:
            return False

        try:
            with open(file_path) as f:
                journal = json.load(f)
        except Exception as e:
            self.logger.exception(f"Failed to load journal file: {str(e)}")
            return False

        modified = False
        for trans in journal["transactions"]:
            if "category" not in trans:
                new_category = self.classify_transaction(trans, rules)
                trans["category"] = new_category
                modified = True

                self.logger.debug(
                    f"Classifying transaction: {trans['description']} (${trans['amount']:.2f})"
                )
                self.logger.debug(f"Classified as: {new_category}")

        if modified:
            try:
                with open(file_path, "w") as f:
                    json.dump(journal, f, indent=4)
                self.logger.info(f"Journal file updated: {file_path}")
            except Exception as e:
                self.logger.exception(f"Failed to update journal file: {str(e)}")
                # Restore from backup
                try:
                    shutil.copy2(backup_path, file_path)
                    self.logger.warning("Journal file restored from backup.")
                except Exception as restore_e:
                    self.logger.exception(
                        f"Failed to restore journal from backup: {str(restore_e)}"
                    )
                return False

        return True

    def process_by_year_files(self, base_dir: str, rules: Dict[str, Any]) -> None:
        """Process all journal files within a base directory, organized by year.

        Args:
            base_dir: The base directory containing the journal files.
            rules: A dictionary containing the classification rules.
        """
        for year_dir in os.listdir(base_dir):
            year_path = os.path.join(base_dir, year_dir)
            if os.path.isdir(year_path):
                for filename in os.listdir(year_path):
                    if filename.endswith(".json"):
                        file_path = os.path.join(year_path, filename)
                        self.process_journal_file(file_path, rules)

    def run(self) -> int:
        """Main function to process all journal files.

        Returns:
            0 if the process was successful, 1 otherwise.
        """
        self.logger.info("Starting transaction categorization")

        base_dir = self.get_config_value("journal_base_dir", ".")
        rules_file = self.get_config_value("classification_rules", "classification_rules.json")

        self.logger.info(f"Using base directory: {base_dir}")
        self.logger.info(f"Using classification rules file: {rules_file}")

        try:
            rules = self.load_classification_rules(rules_file)
            self.logger.info(
                f"Processing files with {len(rules['patterns'])} classification patterns"
            )
            self.process_by_year_files(base_dir, rules)
        except Exception as e:
            self.logger.error(f"Categorization failed: {str(e)}", exc_info=True)
            return 1

        self.logger.info("Transaction categorization completed successfully")
        return 0


def main() -> int:
    """Main entrypoint for the script."""
    categorizer = JournalCategorizer()
    return categorizer.run()


if __name__ == "__main__":
    sys.exit(main())
