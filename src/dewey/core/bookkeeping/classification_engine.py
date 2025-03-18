import json
import re
from datetime import datetime
from pathlib import Path
from re import Pattern
import fnmatch
from typing import TYPE_CHECKING, List, Tuple, Dict, Optional, Any

from dewey.utils import get_logger

if TYPE_CHECKING:
    from src.dewey.core.bookkeeping.writers.journal_writer_fab1858b import JournalWriter


class ClassificationError(Exception):
    """Exception for classification failures."""


class ClassificationEngine:
    """Handles transaction categorization logic."""

    def __init__(self, rules_path: Path, ledger_file: Path) -> None:
        """Initialize the ClassificationEngine."""
        self.logger = get_logger('classification_engine')
        self.ledger_file = ledger_file
        self.rules: Dict[str, Any] = self._load_rules(rules_path)
        self.compiled_patterns: Dict[str, Pattern] = self._compile_patterns()
        self._valid_categories: List[str] = self.rules["categories"]
        self.RULE_SOURCES = [
            ("overrides.json", 0),  # Highest priority
            ("manual_rules.json", 1),
            ("base_rules.json", 2)   # Lowest priority
        ]
        self.logger.info(f"Initialized with {len(self.rules['patterns'])} patterns")

    @property
    def categories(self) -> List[str]:
        """Get valid classification categories."""
        return self._valid_categories

    def _load_rules(self, rules_path: Path) -> Dict[str, Any]:
        """Load classification rules from JSON file."""
        try:
            with open(rules_path) as f:
                rules = json.load(f)
            self.logger.debug(f"Loaded {len(rules['patterns'])} rules from {rules_path}")
            return rules
        except Exception as e:
            self.logger.exception(f"Failed to load rules from {rules_path}: {str(e)}")
            raise ClassificationError(f"Failed to load rules: {str(e)}")

    def _compile_patterns(self) -> Dict[str, Pattern]:
        """Compile regex patterns for efficient matching."""
        try:
            patterns = {}
            for pattern_str in self.rules["patterns"]:
                try:
                    patterns[pattern_str] = re.compile(pattern_str, re.IGNORECASE)
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern '{pattern_str}': {str(e)}")
                    continue
            self.logger.debug(f"Compiled {len(patterns)} regex patterns")
            return patterns
        except Exception as e:
            self.logger.exception(f"Failed to compile patterns: {str(e)}")
            raise ClassificationError(f"Failed to compile patterns: {str(e)}")

    def load_classification_rules(self) -> List[Tuple[Pattern, str, int]]:
        """Load and prioritize classification rules from multiple sources."""
        try:
            rules = []
            for source, priority in self.RULE_SOURCES:
                try:
                    with open(source) as f:
                        source_rules = json.load(f)
                        for pattern_str, rule in source_rules.items():
                            try:
                                pattern = re.compile(pattern_str, re.IGNORECASE)
                                rules.append((pattern, rule["category"], priority))
                            except re.error as e:
                                self.logger.warning(f"Invalid regex in {source}: {pattern_str} - {str(e)}")
                except FileNotFoundError:
                    self.logger.debug(f"Rules file not found: {source}")
                    continue
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON in {source}: {str(e)}")
                    continue
            
            self.logger.info(f"Loaded {len(rules)} classification rules")
            return sorted(rules, key=lambda x: x[2])  # Sort by priority
            
        except Exception as e:
            self.logger.exception(f"Failed to load classification rules: {str(e)}")
            raise ClassificationError(f"Failed to load classification rules: {str(e)}")

    def export_hledger_rules(self, output_path: Path) -> None:
        """Export rules in hledger format."""
        try:
            rules_text = []
            
            # Add header
            rules_text.append("; Generated by Dewey Classification Engine")
            rules_text.append(f"; Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            rules_text.append("")
            
            # Add rules sorted by category
            for category in sorted(self._valid_categories):
                rules_text.append(f"; {category}")
                for pattern, rule in self.rules["patterns"].items():
                    if rule["category"] == category:
                        rules_text.append(f"if /{pattern}/ then account2 {category}")
                rules_text.append("")
            
            # Write to file
            with open(output_path, 'w') as f:
                f.write('\n'.join(rules_text))
            
            self.logger.info(f"Exported {len(self.rules['patterns'])} rules to {output_path}")
            
        except Exception as e:
            self.logger.exception(f"Failed to export hledger rules: {str(e)}")
            raise ClassificationError(f"Failed to export hledger rules: {str(e)}")

    def export_paisa_template(self, output_path: Path) -> None:
        """Export rules in Paisa template format."""
        try:
            template = {
                "version": "1.0",
                "rules": []
            }
            
            # Convert rules to Paisa format
            for pattern, rule in self.rules["patterns"].items():
                template["rules"].append({
                    "pattern": pattern,
                    "category": rule["category"],
                    "examples": rule.get("examples", [])
                })
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(template, f, indent=2)
            
            self.logger.info(f"Exported {len(template['rules'])} rules to {output_path}")
            
        except Exception as e:
            self.logger.exception(f"Failed to export Paisa template: {str(e)}")
            raise ClassificationError(f"Failed to export Paisa template: {str(e)}")

    def classify(self, description: str, amount: float) -> Tuple[str, str, float]:
        """Classify a transaction based on its description and amount."""
        try:
            # Try each pattern in priority order
            for pattern_str, pattern in self.compiled_patterns.items():
                if pattern.search(description):
                    rule = self.rules["patterns"][pattern_str]
                    category = rule["category"]
                    self.logger.debug(f"Matched pattern '{pattern_str}' for '{description}'")
                    return category, pattern_str, amount
            
            # No match found
            self.logger.warning(f"No matching pattern for '{description}'")
            return "expenses:unknown", "", amount
            
        except Exception as e:
            self.logger.exception(f"Classification failed for '{description}': {str(e)}")
            raise ClassificationError(f"Classification failed: {str(e)}")

    def process_feedback(self, feedback: str, journal_writer: "JournalWriter") -> None:
        """Process user feedback to improve classification."""
        try:
            # Parse feedback
            pattern, category = self._parse_feedback(feedback)
            
            # Validate category
            self._validate_category(category)
            
            # Add override rule
            self.rules["patterns"][pattern] = {
                "category": category,
                "source": "user_feedback",
                "added": datetime.now().isoformat()
            }
            
            # Update compiled patterns
            try:
                self.compiled_patterns[pattern] = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                self.logger.error(f"Invalid regex pattern '{pattern}': {str(e)}")
                raise ClassificationError(f"Invalid regex pattern: {str(e)}")
            
            # Save overrides
            self._save_overrides()
            
            self.logger.info(f"Added override rule: '{pattern}' -> {category}")
            
        except Exception as e:
            self.logger.exception(f"Failed to process feedback: {str(e)}")
            raise ClassificationError(f"Failed to process feedback: {str(e)}")

    def _parse_feedback(self, feedback: str) -> Tuple[str, str]:
        """Parse user feedback into pattern and category."""
        try:
            # Try direct parsing
            if ' -> ' in feedback:
                pattern, category = feedback.split(' -> ')
                return pattern.strip(), category.strip()
            
            # Try AI-assisted parsing
            return self._parse_with_ai(feedback)
            
        except Exception as e:
            self.logger.exception(f"Failed to parse feedback '{feedback}': {str(e)}")
            raise ClassificationError(f"Failed to parse feedback: {str(e)}")

    def _parse_with_ai(self, feedback: str) -> Tuple[str, str]:
        """Use AI to parse ambiguous feedback."""
        try:
            # TODO: Implement AI parsing
            raise NotImplementedError("AI parsing not implemented yet")
        except Exception as e:
            self.logger.exception(f"AI parsing failed for '{feedback}': {str(e)}")
            raise ClassificationError(f"AI parsing failed: {str(e)}")

    def _save_overrides(self) -> None:
        """Save override rules to file."""
        try:
            overrides = {
                pattern: rule
                for pattern, rule in self.rules["patterns"].items()
                if rule.get("source") == "user_feedback"
            }
            
            with open("overrides.json", 'w') as f:
                json.dump(overrides, f, indent=2)
                
            self.logger.debug(f"Saved {len(overrides)} override rules")
            
        except Exception as e:
            self.logger.exception(f"Failed to save overrides: {str(e)}")
            raise ClassificationError(f"Failed to save overrides: {str(e)}")

    def _validate_category(self, category: str) -> None:
        """Validate a category string."""
        try:
            if category not in self._valid_categories:
                closest = fnmatch.filter(self._valid_categories, f"*{category}*")
                if closest:
                    suggestion = f"Did you mean one of these? {', '.join(closest)}"
                else:
                    suggestion = f"Valid categories: {', '.join(self._valid_categories)}"
                raise ClassificationError(f"Invalid category '{category}'. {suggestion}")
        except Exception as e:
            self.logger.exception(f"Category validation failed for '{category}': {str(e)}")
            raise ClassificationError(f"Category validation failed: {str(e)}")
