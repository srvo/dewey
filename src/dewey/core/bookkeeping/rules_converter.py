#!/usr/bin/env python3

import json
import re
import argparse
from pathlib import Path
from typing import Any, Dict, List

from dewey.utils import get_logger

class RuleConversionError(Exception):
    """Exception for rule conversion failures."""


def clean_category(category: str) -> str:
    """Cleans and standardizes the category string."""
    category_map = {
        "expenses:draw:all": "expenses:draw",
        "expenses:tech:all": "expenses:software:subscription",
        "expenses:food:all": "expenses:food:meals",
        "expenses:debt:all": "expenses:financial:debt",
        "expenses:fees:all": "expenses:financial:fees",
        "expenses:compliance:all": "expenses:professional:compliance",
        "expenses:taxes:all": "expenses:taxes",
        "expenses:insurance:all": "expenses:insurance",
        "expenses:travel:all": "expenses:travel"
    }
    
    for prefix, replacement in category_map.items():
        if category.startswith(prefix):
            return replacement
    return category


def parse_rules_file(rules_file: Path) -> Dict[str, Dict[str, Any]]:
    """Parse the legacy rules file format."""
    logger = get_logger('rules_converter')
    classifications = {}
    
    try:
        with open(rules_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    pattern, category = line.split(' -> ')
                    pattern = pattern.strip()
                    category = clean_category(category.strip())
                    
                    classifications[pattern] = {
                        'category': category,
                        'pattern': pattern,
                        'transactions': 0,
                        'total_amount': 0.0
                    }
                except ValueError:
                    logger.warning(f"Skipping invalid rule: {line}")
                    continue
        
        logger.info(f"Parsed {len(classifications)} rules from {rules_file}")
        return classifications
        
    except Exception as e:
        logger.exception(f"Failed to parse rules file: {str(e)}")
        raise RuleConversionError(f"Failed to parse rules file: {str(e)}")


def analyze_transactions(
    journal_dir: Path,
    classifications: Dict[str, Dict[str, Any]]
) -> None:
    """Analyze transactions to gather statistics for each rule."""
    logger = get_logger('rules_converter')
    
    try:
        total_transactions = 0
        matched_transactions = 0
        
        for journal_file in journal_dir.glob('*.journal'):
            with open(journal_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(';'):
                        continue
                        
                    total_transactions += 1
                    for pattern, rule in classifications.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            rule['transactions'] += 1
                            matched_transactions += 1
                            # TODO: Extract and sum transaction amounts
                            break
        
        logger.info(f"Analyzed {total_transactions} transactions")
        logger.info(f"Matched {matched_transactions} transactions ({matched_transactions/total_transactions*100:.1f}%)")
        
    except Exception as e:
        logger.exception(f"Failed to analyze transactions: {str(e)}")
        raise RuleConversionError(f"Failed to analyze transactions: {str(e)}")


def generate_rules_json(
    classifications: Dict[str, Dict[str, Any]],
    output_file: Path
) -> None:
    """Generate the JSON rules file."""
    logger = get_logger('rules_converter')
    
    try:
        # Sort rules by number of transactions (most used first)
        sorted_rules = dict(
            sorted(
                classifications.items(),
                key=lambda x: x[1]['transactions'],
                reverse=True
            )
        )
        
        # Write JSON file
        with open(output_file, 'w') as f:
            json.dump(
                sorted_rules,
                f,
                indent=2,
                sort_keys=True
            )
        
        logger.info(f"Generated rules JSON file: {output_file}")
        
        # Log statistics
        total_rules = len(sorted_rules)
        active_rules = sum(1 for rule in sorted_rules.values() if rule['transactions'] > 0)
        logger.info(f"Total rules: {total_rules}")
        logger.info(f"Active rules: {active_rules} ({active_rules/total_rules*100:.1f}%)")
        
    except Exception as e:
        logger.exception(f"Failed to generate rules JSON: {str(e)}")
        raise RuleConversionError(f"Failed to generate rules JSON: {str(e)}")


def main() -> None:
    """Main entry point for rules conversion."""
    logger = get_logger('rules_converter')
    
    parser = argparse.ArgumentParser(description="Convert legacy rules to JSON format")
    parser.add_argument("rules_file", type=Path, help="Path to the legacy rules file")
    parser.add_argument("journal_dir", type=Path, help="Path to the journal directory")
    parser.add_argument("output_file", type=Path, help="Path for the output JSON file")
    args = parser.parse_args()
    
    try:
        # Parse legacy rules
        classifications = parse_rules_file(args.rules_file)
        
        # Analyze transactions
        analyze_transactions(args.journal_dir, classifications)
        
        # Generate JSON output
        generate_rules_json(classifications, args.output_file)
        
        logger.info("Rules conversion completed successfully")
        
    except RuleConversionError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
