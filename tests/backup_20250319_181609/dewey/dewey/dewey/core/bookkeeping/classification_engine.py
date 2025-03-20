import json
import logging
import re
from datetime import datetime
from pathlib import Path
from re import Pattern
import fnmatch
from typing import TYPE_CHECKING, List, Tuple, Dict
import logging
from dewey.core.base_script import BaseScript

if TYPE_CHECKING:
    from src.dewey.core.bookkeeping.writers.journal_writer_fab1858b import JournalWriter
import logging
from dewey.core.base_script import BaseScript

logger = logging.getLogger(__name__)


class ClassificationError(BaseScript):
    """Exception for classification failures."""


    def __init__(self):
        super().__init__(config_section='bookkeeping')

class ClassificationEngine(BaseScript):
    """Handles transaction categorization logic."""

    def __init__(self, rules_path: Path, ledger_file: Path) -> None:
        """Initializes the ClassificationEngine.

        Args:
        ----
            rules_path: Path to the JSON file containing classification rules.

        """
        self.ledger_file = ledger_file
        self.rules: dict = self._load_rules(rules_path)
        self.compiled_patterns: dict[str, Pattern] = self._compile_patterns()
        self._valid_categories: list[str] = self.rules["categories"]
        self.RULE_SOURCES = [
            ("overrides.json", 0),  # Highest priority
            ("manual_rules.json", 1),
            ("base_rules.json", 2)]  # Lowest priority

    @property
    def categories(self) -> list[str]:
        """Accessor for valid classification categories.

        Returns
        -------
            A list of valid classification categories.

        """
        return self._valid_categories

    def _load_rules(self, rules_path: Path) -> dict:
        """Load classification rules from JSON file.

        Args:
        ----
            rules_path: Path to the JSON file.

        Returns:
        -------
            A dictionary containing the loaded rules.  Returns default rules on failure.

        """
        try:
            with open(rules_path) as f:
                rules: dict = json.load(f)

            loaded_rules: dict = {
                "patterns": rules.get("patterns", {}),
                "categories": rules.get("categories", []),
                "defaults": rules.get(
                    "defaults",
                    {"positive": "income:unknown", "negative": "expenses:unknown"},
                ),
                "overrides": rules.get("overrides", {}),
                "sources": rules.get("sources", []),
            }

            if "source" not in loaded_rules:
                loaded_rules["source"] = str(rules_path)

            return loaded_rules
        except Exception as e:
            self.logger.exception(f"Failed to load classification rules: {e!s}")
            return {
                "patterns": {},
                "categories": [],
                "defaults": {
                    "positive": "income:unknown",
                    "negative": "expenses:unknown",
                },
                "overrides": {},
                "sources": [],
            }

    def _compile_patterns(self) -> dict[str, Pattern]:
        """Compile regex patterns for classification.

        Returns
        -------
            A dictionary mapping patterns to compiled regex objects.

        Raises
        ------
            ClassificationError: If an invalid regex pattern is encountered.

        """
        compiled: dict[str, Pattern] = {}
        for pattern in self.rules["patterns"]:
            try:
                compiled[pattern] = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                self.logger.exception("Invalid regex pattern '%s': %s", pattern, str(e))
                msg = f"Invalid regex pattern '{pattern}': {e!s}"
                raise ClassificationError(
                    msg,
                ) from None
        return compiled

   def load_classification_rules(self) -> List[Tuple[Pattern, str, int]]:
       """Load and compile classification rules with priority.

       Returns
       -------
           A list of compiled rules with their associated category and priority.

       """
       self.logger.info("Loading classification rules with priority system")

       rules = self.load_prioritized_rules()
       compiled_rules = []

       for (pattern, data), priority in rules:
           category = data["category"]
           formatted_category = self.format_category(category)

           # Handle different pattern types
           compiled = self.compile_pattern(pattern)

           compiled_rules.append((compiled, formatted_category, priority))

       self.logger.info(f"Loaded {len(compiled_rules)} classification rules")
   def export_hledger_rules(self, output_path: Path) -> None:
       """Export rules in hledger's CSV format.

        Args:
        ----
            output_path: Path to the output file.

        """
        self.logger.info("📝 Generating hledger rules file at: %s", output_path)

        rules: list[str] = [
            "skip 1",
            "separator ,",
            "fields date,description,amount",
            f"currency {self.rules.get('hledger', {}).get('currency', '$')}",
            f"date-format {self.rules.get('hledger', {}).get('date_format', '%Y-%m-%d')}",
            "account1 assets:mercury:checking",
        ]

        rules.extend(
            [
                "if %amount < 0",
                "    account2 expenses:unknown",
                "if %amount > 0",
                "    account2 income:unknown",
            ],
        )

        self.logger.debug(
            "Converting %d patterns to hledger rules",
            len(self.rules["patterns"]),
        )
        for pattern, account in self.rules["patterns"].items():
            rules.append(f"if {pattern}")
            rules.append(f"    account2 {account}")
            self.logger.debug("Added pattern: %s => %s", pattern, account)

        self.logger.debug("Adding amount-based account switching")

        with open(output_path, "w") as f:
            f.write("\n".join(rules))
        self.logger.info("Successfully wrote %d lines to rules file", len(rules))

    def export_paisa_template(self, output_path: Path) -> None:
        """Export rules in Paisa's template format.

        Args:
        ----
            output_path: Path to the output file.

        """
        self.logger.info("📝 Generating Paisa template at: %s", output_path)

        template: list[str] = [
            "{{#if (isDate ROW.A date_format)}}",
            "{{date ROW.A date_format}} {{ROW.B}}",
            "    {{match ROW.B",
        ]

        for pattern, account in self.rules["patterns"].items():
            clean_pattern: str = pattern.replace("|", "\\\\|")
            template.append(f'        {account}="{clean_pattern}" \\')

        template.extend(
            [
                "    }}",
                "    Assets:Mercury:Checking  {{negate (amount ROW.C)}}",
                "{{/if}}",
            ],
        )

        template_str: str = "\n".join(template).replace(
            "date_format",
            f'"{self.rules.get("hledger", {}).get("date_format", "%Y-%m-%d")}"',
        )

        with open(output_path, "w") as f:
            f.write(template_str)
        self.logger.info(
            "Generated Paisa template with %d patterns",
            len(self.rules["patterns"]),
        )

    def classify(self, description: str, amount: float) -> tuple[str, str, float]:
        """Classify transaction using rules and AI fallback.

        Args:
        ----
            description: Transaction description.
            amount: Transaction amount.

        Returns:
        -------
            A tuple containing the income account, expense account, and absolute amount.

        """
        for pattern, compiled in self.compiled_patterns.items():
            if compiled.search(description):
                account: str = self.rules["patterns"][pattern]
                if amount < 0:
                    return (account, self.rules["defaults"]["negative"], abs(amount))
                return (self.rules["defaults"]["positive"], account, amount)

        if amount < 0:
            return (
                self.rules["defaults"]["negative"],
                self.rules["defaults"]["negative"],
                abs(amount),
            )
        return (
            self.rules["defaults"]["positive"],
            self.rules["defaults"]["positive"],
            amount,
        )

    def process_feedback(self, feedback: str, journal_writer: "JournalWriter") -> None:
        """Process user feedback to improve classification rules.

        Args:
        ----
            feedback: User feedback string.
            journal_writer: JournalWriter instance for logging.

        """
        try:
            parsed: tuple[str, str] = self._parse_feedback(feedback)
        except ClassificationError:
            parsed = self._parse_with_ai(feedback)

        pattern, category = parsed
        self._validate_category(category)

        self.rules["overrides"][pattern] = {
            "category": category,
            "examples": [feedback],
            "timestamp": datetime.now().isoformat(),
        }

        journal_writer.log_classification_decision(
            tx_hash="feedback_system",
            pattern=pattern,
            category=category,
        )

        self._save_overrides()
        self._compile_patterns()
        self.logger.info(f"Processed feedback: {pattern} → {category}")

    def _parse_feedback(self, feedback: str) -> tuple[str, str]:
        """Parse natural language feedback.

        Args:
        ----
            feedback: User feedback string.

        Returns:
        -------
            A tuple containing the pattern and category.

        Raises:
        ------
            ClassificationError: If the feedback format is invalid.

        """
        match: re.Match = re.search(
            r'(?i)classify\s+[\'"](.+?)[\'"].+?as\s+([\w:]+)',
            feedback,
        )
        if not match:
            msg = f"Invalid feedback format: {feedback}"
            raise ClassificationError(msg)
        return match.group(1).strip(), match.group(2).lower()

    def _parse_with_ai(self, feedback: str) -> tuple[str, str]:
        """Use DeepInfra to parse complex feedback.

        Args:
        ----
            feedback: User feedback string.

        Returns:
        -------
            A tuple containing the pattern and category.

        Raises:
        ------
            ClassificationError: If AI parsing fails.

        """
        from bin.deepinfra_client import classify_errors
import logging
from dewey.core.base_script import BaseScript

        prompt: list[str] = [
            "Convert this accounting feedback to a classification rule:",
            f"Original feedback: {feedback}",
            "Respond ONLY with JSON: {'pattern': string, 'category': string}",
        ]

        try:
            response: list[dict] = classify_errors(prompt)
            if not response:
                msg = "No response from AI"
                raise ClassificationError(msg)

            result: dict = json.loads(response[0]["example"])
            return result["pattern"], result["category"]
        except Exception as e:
            msg = f"AI parsing failed: {e!s}"
            raise ClassificationError(msg)

    def _save_overrides(self) -> None:
        """Persist override rules to file."""
        overrides_file: Path = Path(__file__).parent.parent / "rules" / "overrides.json"
        data: dict = {
            "patterns": self.rules["overrides"],
            "categories": list(set(self.rules["overrides"].values())),
            "last_updated": datetime.now().isoformat(),
        }

        with open(overrides_file, "w") as f:
            json.dump(data, f, indent=2)

    def _validate_category(self, category: str) -> None:
        """Validate if a category is in the allowed categories.

        Args:
        ----
            category: Category to validate.

        Raises:
        ------
            ValueError: If category is not in allowed categories.

        """
        if category not in self.categories:
            msg = f"Category {category} is not an allowed category."
            raise ValueError(msg)