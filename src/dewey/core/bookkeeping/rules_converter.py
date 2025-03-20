#!/usr/bin/env python3

import json
import re
from pathlib import Path
from typing import Any, Dict

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class RulesConverter(BaseScript):
    """Converts legacy rule formats to the current JSON format."""

    def __init__(self) -> None:
        """Initializes the RulesConverter."""
        super().__init__(config_section="rules_converter")
        self.db_conn: DatabaseConnection | None = None
        self.llm_client: LLMClient | None = None

    def clean_category(self, category: str) -> str:
        """Cleans and standardizes the category string.

        Args:
            category: The category string to clean.

        Returns:
            The cleaned category string.
        """
        if category.startswith("expenses:draw:all"):
            return "expenses:draw"
        if category.startswith("expenses:tech:all"):
            return "expenses:software:subscription"
        if category.startswith("expenses:food:all"):
            return "expenses:food:meals"
        if category.startswith("expenses:debt:all"):
            return "expenses:financial:debt"
        if category.startswith("expenses:fees:all"):
            return "expenses:financial:fees"
        if category.startswith("expenses:compliance:all"):
            return "expenses:professional:compliance"
        if category.startswith("expenses:taxes:all"):
            return "expenses:taxes"
        if category.startswith("expenses:insurance:all"):
            return "expenses:insurance"
        if category.startswith("expenses:travel:all"):
            return "expenses:travel"
        return category

    def parse_rules_file(self, rules_file: Path) -> Dict[str, Dict[str, Any]]:
        """Parses the old_mercury.rules file and extracts classification patterns.

        Args:
            rules_file: Path to the rules file.

        Returns:
            A dictionary containing classification patterns and their associated
            categories and examples.
        """
        classifications: Dict[str, Dict[str, Any]] = {}

        with open(rules_file) as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments that don't start with #
                if not line or (line.startswith("#") and "based on" not in line.lower()):
                    continue

                # Check for category headers in comments
                if line.startswith("# Expense transactions based on"):
                    continue

                # Parse classification rules
                if line.startswith("if") and "then account2" in line:
                    # Extract pattern and category
                    pattern_match = re.search(r'if /(.+?)/ then account2 "([^"]+)"', line)
                    if pattern_match:
                        # Escape regex special characters and normalize whitespace
                        pattern = re.escape(pattern_match.group(1)).replace(r"\ ", "\\s+")
                        category = pattern_match.group(2)

                        # Validate regex syntax
                        try:
                            re.compile(pattern, re.IGNORECASE)
                        except re.error as e:
                            self.logger.exception(
                                "Skipping invalid regex pattern '%s': %s",
                                pattern,
                                str(e),
                            )
                            continue

                        # Convert old category format to new format
                        category = category.replace(">", ":")

                        # Clean up the category
                        category = self.clean_category(category)

                        # Store in classifications
                        if pattern not in classifications:
                            classifications[pattern] = {
                                "category": category,
                                "examples": [],
                            }

        return classifications

    def analyze_transactions(
        self,
        journal_dir: Path,
        classifications: Dict[str, Dict[str, Any]],
    ) -> None:
        """Analyzes existing transactions to find examples for each pattern.

        Args:
            journal_dir: Path to the directory containing journal files.
            classifications: A dictionary containing classification patterns.
        """
        for journal_file in journal_dir.glob("**/*.journal"):
            with open(journal_file) as f:
                content = f.read()

                # Find all transactions
                transactions = re.findall(
                    r"\d{4}-\d{2}-\d{2}\s+(.+?)\n\s+[^\\n]+\n\s+[^\\n]+",
                    content,
                    re.MULTILINE,
                )

                # Match transactions against patterns
                for desc in transactions:
                    desc = desc.strip()
                    for pattern, data in classifications.items():
                        if re.search(pattern, desc, re.IGNORECASE):
                            if desc not in data["examples"]:
                                data["examples"].append(desc)

    def generate_rules_json(
        self, classifications: Dict[str, Dict[str, Any]], output_file: Path,
    ) -> None:
        """Generates a JSON file with classification rules.

        Args:
            classifications: A dictionary containing classification patterns.
            output_file: Path to the output JSON file.
        """
        # Convert to a more efficient format for the classifier
        rules: Dict[str, Any] = {
            "patterns": {},
            "categories": set(),
            "stats": {"total_patterns": len(classifications), "patterns_with_examples": 0},
        }

        for pattern, data in classifications.items():
            category = data["category"]
            rules["patterns"][pattern] = {
                "category": category,
                "examples": data["examples"][:5],  # Store up to 5 examples
            }
            rules["categories"].add(category)
            if data["examples"]:
                rules["stats"]["patterns_with_examples"] += 1

        # Convert sets to lists for JSON serialization
        rules["categories"] = sorted(list(rules["categories"]))

        # Save to JSON file
        with open(output_file, "w") as f:
            json.dump(rules, f, indent=2)

        self.logger.info(f"Generated rules file: {output_file}")
        self.logger.info(f"Total patterns: {rules['stats']['total_patterns']}")
        self.logger.info(f"Patterns with examples: {rules['stats']['patterns_with_examples']}")
        self.logger.info(f"Unique categories: {len(rules['categories'])}")

    def run(self) -> None:
        """Orchestrates the rule parsing, analysis, and generation."""
        base_dir = Path(__file__).resolve().parent.parent
        rules_file = base_dir / "old_mercury.rules"
        journal_dir = base_dir / "import" / "mercury" / "journal"
        output_file = base_dir / "import" / "mercury" / "classification_rules.json"

        self.logger.info(f"Parsing rules file: {rules_file}")
        classifications = self.parse_rules_file(rules_file)

        self.logger.info(f"Analyzing transactions in: {journal_dir}")
        self.analyze_transactions(journal_dir, classifications)

        self.logger.info(f"Generating rules file: {output_file}")
        self.generate_rules_json(classifications, output_file)


def main() -> None:
    """Main entry point for the script."""
    RulesConverter().run()


if __name__ == "__main__":
    main()
