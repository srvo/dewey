#!/usr/bin/env python3
import fnmatch
import json
import re
import shutil
import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Any
from dewey.utils import get_logger

# Rule sources in priority order (lower numbers = higher priority)
RULE_SOURCES = [
    ("overrides.json", 0),  # Highest priority
    ("manual_rules.json", 1),
    ("base_rules.json", 2)  # Lowest priority
]

# TODO: Fix search/replace block

# Use absolute path for classification rules file
CLASSIFICATION_FILE = Path.home() / "books/import/mercury/classification_rules.json"
LEDGER_FILE = Path.home() / ".hledger.journal"
BACKUP_EXT = ".bak"

def load_classification_rules() -> Dict:
    """Load classification rules from JSON files."""
    logger = get_logger('auto_categorize')
    logger.info("Loading classification rules")
    return {}  # Placeholder


def process_transactions(transactions: List[Dict], rules: Dict) -> List[Dict]:
    """Process transactions and categorize them based on rules."""
    logger = get_logger('auto_categorize')
    logger.info("Processing transactions")
    return transactions  # Placeholder


def parse_journal_entries(file_path: Path) -> List[Dict]:
    """Parse journal entries from file."""
    logger = get_logger('auto_categorize')
    logger.info(f"Parsing journal entries from {file_path}")
    return []  # Placeholder


def serialize_transactions(transactions: List[Dict]) -> str:
    """Serialize transactions back to journal format."""
    logger = get_logger('auto_categorize')
    logger.info("Serializing transactions")
    return ""  # Placeholder


def write_journal_file(content: str, file_path: Path) -> None:
    """Write content to journal file with backup."""
    logger = get_logger('auto_categorize')
    
    try:
        # Create backup
        backup_path = file_path.with_suffix(BACKUP_EXT)
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup at {backup_path}")
        
        # Write new content
        with open(file_path, 'w') as f:
            f.write(content)
        logger.info(f"Successfully wrote updated journal to {file_path}")
        
    except Exception as e:
        logger.error(f"Failed to write journal file: {str(e)}", exc_info=True)
        raise


def load_rules(rules_file: str) -> List[Dict[str, Any]]:
    """Load categorization rules from a JSON file."""
    logger = get_logger('auto_categorize')
    
    try:
        with open(rules_file) as f:
            rules = json.load(f)
            
        if not isinstance(rules, list):
            logger.error("Rules file must contain a list of rules")
            sys.exit(1)
            
        logger.info(f"Loaded {len(rules)} rules")
        return rules
        
    except Exception as e:
        logger.error(f"Error loading rules: {str(e)}", exc_info=True)
        sys.exit(1)


def categorize_transaction(transaction: List[str], rules: List[Dict[str, Any]]) -> List[str]:
    """Apply categorization rules to a transaction."""
    logger = get_logger('auto_categorize')
    
    # Get description from first line
    if not transaction or not transaction[0].strip():
        return transaction
        
    description = transaction[0].strip().split(maxsplit=1)[1] if len(transaction[0].strip().split(maxsplit=1)) > 1 else ''
    
    # Try to match rules
    for rule in rules:
        if 'pattern' in rule and 'account' in rule:
            if rule['pattern'].lower() in description.lower():
                # Found a match, update the account posting
                new_transaction = [transaction[0]]  # Keep date line
                
                # Update account line
                for line in transaction[1:]:
                    if line.strip() and line.strip().startswith('expenses:unknown'):
                        new_line = line.replace('expenses:unknown', rule['account'])
                        logger.debug(f"Applied rule: {description} -> {rule['account']}")
                        new_transaction.append(new_line)
                    else:
                        new_transaction.append(line)
                        
                return new_transaction
    
    return transaction


def auto_categorize(input_file: str, rules_file: str, output_file: str = None) -> None:
    """Auto-categorize transactions in a journal file."""
    logger = get_logger('auto_categorize')
    
    try:
        input_path = Path(input_file)
        rules_path = Path(rules_file)
        
        if not input_path.exists():
            logger.error(f"Input file does not exist: {input_path}")
            sys.exit(1)
            
        if not rules_path.exists():
            logger.error(f"Rules file does not exist: {rules_path}")
            sys.exit(1)
        
        # If no output file specified, create one with '_categorized' suffix
        if output_file is None:
            output_file = str(input_path.with_suffix('')) + '_categorized.journal'
        output_path = Path(output_file)
        
        logger.info(f"Auto-categorizing journal file: {input_path}")
        logger.info(f"Using rules from: {rules_path}")
        logger.info(f"Output file: {output_path}")
        
        # Load rules
        rules = load_rules(rules_file)
        
        # Process file
        current_transaction = []
        categorized_transactions = []
        uncategorized_count = 0
        categorized_count = 0
        
        with open(input_path) as f:
            for line in f:
                # Start of new transaction
                if line.strip() and not line.startswith(' ') and not line.startswith(';'):
                    # Categorize previous transaction if exists
                    if current_transaction:
                        # Check if transaction needs categorization
                        needs_categorization = any(
                            l.strip().startswith('expenses:unknown') 
                            for l in current_transaction
                        )
                        
                        if needs_categorization:
                            new_transaction = categorize_transaction(current_transaction, rules)
                            if new_transaction != current_transaction:
                                categorized_count += 1
                            else:
                                uncategorized_count += 1
                        else:
                            new_transaction = current_transaction
                            
                        categorized_transactions.extend(new_transaction)
                        categorized_transactions.append('\n')  # Add blank line between transactions
                    
                    # Start new transaction
                    current_transaction = [line]
                else:
                    current_transaction.append(line)
        
        # Categorize final transaction
        if current_transaction:
            needs_categorization = any(
                l.strip().startswith('expenses:unknown') 
                for l in current_transaction
            )
            
            if needs_categorization:
                new_transaction = categorize_transaction(current_transaction, rules)
                if new_transaction != current_transaction:
                    categorized_count += 1
                else:
                    uncategorized_count += 1
            else:
                new_transaction = current_transaction
                
            categorized_transactions.extend(new_transaction)
        
        # Write categorized journal
        with open(output_path, 'w') as f:
            f.writelines(categorized_transactions)
        
        logger.info("\nCategorization completed:")
        logger.info(f"Successfully categorized: {categorized_count}")
        logger.info(f"Remaining uncategorized: {uncategorized_count}")
        
    except Exception as e:
        logger.error(f"Error auto-categorizing journal: {str(e)}", exc_info=True)
        sys.exit(1)


def main():
    """Main processing workflow."""
    parser = argparse.ArgumentParser(description='Auto-categorize transactions in a journal file')
    parser.add_argument('--input-file', default=str(LEDGER_FILE), help='Input journal file')
    parser.add_argument('--rules-file', default=str(CLASSIFICATION_FILE), help='JSON file containing classification rules')
    args = parser.parse_args()
    
    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('auto_categorize', log_dir)
    
    try:
        # Load configuration
        rules = load_classification_rules()
        
        # Process journal entries
        transactions = parse_journal_entries(Path(args.input_file))
        updated_transactions = process_transactions(transactions, rules)
        new_content = serialize_transactions(updated_transactions)
        
        # Write results
        write_journal_file(new_content, Path(args.input_file))
        logger.info("Successfully updated journal entries")
        
    except Exception as e:
        logger.error(f"Failed to process journal: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
