#!/usr/bin/env python3

import json
import os
import re
from pathlib import Path
import shutil
import sys
from typing import Any
from dewey.utils import get_logger

def load_classification_rules(rules_file: str) -> dict[str, Any]:
    """Load classification rules from JSON file."""
    logger = get_logger('transaction_categorizer')
    logger.info(f"Loading classification rules from {rules_file}")
    
    try:
        with open(rules_file) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.exception(f"Classification rules file not found: {rules_file}")
        raise
    except json.JSONDecodeError as e:
        logger.exception(f"Failed to load classification rules: {str(e)}")
        raise


def create_backup(file_path: Path) -> str:
    """Create a backup of the file before processing."""
    logger = get_logger('transaction_categorizer')
    backup_path = str(file_path) + '.bak'
    
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup at {backup_path}")
        return backup_path
    except Exception as e:
        logger.exception(f"Failed to create backup: {str(e)}")
        raise


def classify_transaction(transaction: dict[str, Any], rules: dict[str, Any]) -> str:
    """Classify a transaction based on rules."""
    logger = get_logger('transaction_categorizer')
    
    description = transaction.get('description', '').lower()
    amount = transaction.get('amount', 0)
    
    for rule in rules.get('rules', []):
        pattern = rule.get('pattern', '').lower()
        if pattern in description:
            category = rule.get('category', '')
            logger.debug(f"Matched rule '{pattern}' for transaction '{description}'")
            return category
    
    logger.debug(f"No matching rule found for transaction '{description}'")
    return 'expenses:unclassified'


def process_journal_file(file_path: Path, rules: dict[str, Any]) -> bool:
    """Process a journal file and classify transactions."""
    logger = get_logger('transaction_categorizer')
    logger.info(f"Processing journal file: {file_path}")
    
    try:
        # Create backup
        backup_path = create_backup(file_path)
        
        # Read and process file
        with open(file_path) as f:
            content = f.read()
        
        # Split into transactions
        transactions = []
        current_transaction = {'lines': []}
        
        for line in content.split('\n'):
            if line.strip() and not line.startswith(' '):
                # Start of new transaction
                if current_transaction['lines']:
                    transactions.append(current_transaction)
                    current_transaction = {'lines': []}
                
                # Parse date and description
                match = re.match(r'(\d{4}-\d{2}-\d{2})\s+(.+)', line)
                if match:
                    current_transaction['date'] = match.group(1)
                    current_transaction['description'] = match.group(2)
                current_transaction['lines'].append(line)
            else:
                current_transaction['lines'].append(line)
        
        # Add final transaction
        if current_transaction['lines']:
            transactions.append(current_transaction)
        
        # Process transactions
        classified_content = []
        classified_count = 0
        
        for tx in transactions:
            if 'description' in tx:
                category = classify_transaction(tx, rules)
                if category != 'expenses:unclassified':
                    classified_count += 1
                
                # Update transaction lines
                new_lines = []
                for line in tx['lines']:
                    if line.strip().startswith('expenses:unclassified'):
                        line = line.replace('expenses:unclassified', category)
                    new_lines.append(line)
                classified_content.extend(new_lines)
            else:
                classified_content.extend(tx['lines'])
            classified_content.append('')  # Empty line between transactions
        
        # Write updated content
        with open(file_path, 'w') as f:
            f.write('\n'.join(classified_content))
        
        logger.info(f"Classified {classified_count} transactions in {file_path}")
        return True
        
    except Exception as e:
        logger.exception(f"Error processing file {file_path}: {str(e)}")
        # Restore from backup if exists
        if 'backup_path' in locals() and os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, file_path)
                logger.info(f"Restored from backup: {backup_path}")
            except Exception as restore_error:
                logger.exception(f"Failed to restore from backup: {str(restore_error)}")
        return False


def process_by_year_files(base_dir: Path, rules: dict[str, Any]) -> None:
    """Process all by-year journal files in a directory."""
    logger = get_logger('transaction_categorizer')
    logger.info(f"Processing by-year files in {base_dir}")
    
    try:
        for file_path in base_dir.glob('*.journal'):
            if re.match(r'\d{4}\.journal$', file_path.name):
                success = process_journal_file(file_path, rules)
                if not success:
                    logger.error(f"Failed to process {file_path}")
                    
    except Exception as e:
        logger.exception(f"Error processing by-year files: {str(e)}")
        sys.exit(1)


def main() -> int:
    """Main entry point."""
    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('transaction_categorizer', log_dir)
    
    try:
        # Load rules
        rules_file = os.path.expanduser('~/dewey/config/classification_rules.json')
        rules = load_classification_rules(rules_file)
        
        # Process journal files
        journal_dir = Path(os.path.expanduser('~/dewey/data/journals'))
        process_by_year_files(journal_dir, rules)
        
        return 0
        
    except Exception as e:
        logger.exception(f"Error in main: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
