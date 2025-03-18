#!/usr/bin/env python3

import json
import subprocess
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set

from dewey.utils import get_logger

class AccountValidationError(Exception):
    """Exception for account validation failures."""


def load_rules(rules_file: Path) -> Dict:
    """Load classification rules from a JSON file."""
    logger = get_logger('account_validator')
    
    try:
        with open(rules_file) as f:
            rules = json.load(f)
        logger.debug(f"Loaded {len(rules)} rules from {rules_file}")
        return rules
    except Exception as e:
        logger.exception(f"Failed to load rules: {str(e)}")
        raise AccountValidationError(f"Failed to load rules: {str(e)}")


def get_journal_accounts(journal_file: Path) -> Set[str]:
    """Get all accounts from the journal file."""
    logger = get_logger('account_validator')
    
    try:
        result = subprocess.run(
            ["hledger", "accounts", "-f", str(journal_file), "--declared", "--used"],
            capture_output=True,
            text=True,
            check=True
        )
        accounts = set(result.stdout.splitlines())
        logger.debug(f"Found {len(accounts)} accounts in journal")
        return accounts
    except subprocess.CalledProcessError as e:
        logger.exception(f"hledger command failed: {e.stderr}")
        raise AccountValidationError(f"hledger command failed: {e.stderr}")
    except Exception as e:
        logger.exception(f"Failed to get journal accounts: {str(e)}")
        raise AccountValidationError(f"Failed to get journal accounts: {str(e)}")


def validate_accounts(journal_file: Path, rules: Dict) -> bool:
    """Verify that all accounts in the rules exist in the journal file."""
    logger = get_logger('account_validator')
    
    try:
        # Get accounts from journal
        journal_accounts = get_journal_accounts(journal_file)
        
        # Extract accounts from rules
        rule_accounts = set()
        for rule in rules.values():
            if isinstance(rule, dict) and 'account' in rule:
                rule_accounts.add(rule['account'])
        
        # Find missing accounts
        missing_accounts = rule_accounts - journal_accounts
        
        if missing_accounts:
            logger.error(f"Found {len(missing_accounts)} missing accounts:")
            for account in sorted(missing_accounts):
                logger.error(f"  - {account}")
            return False
        
        logger.info("All rule accounts exist in journal")
        return True
        
    except Exception as e:
        logger.exception(f"Account validation failed: {str(e)}")
        return False


def main() -> None:
    """Main entry point for account validation."""
    logger = get_logger('account_validator')
    
    parser = argparse.ArgumentParser(description="Validate accounts in hledger journal")
    parser.add_argument("journal_file", type=Path, help="Path to the journal file")
    parser.add_argument("rules_file", type=Path, help="Path to the rules file")
    args = parser.parse_args()
    
    try:
        rules = load_rules(args.rules_file)
        if not validate_accounts(args.journal_file, rules):
            logger.error("Account validation failed")
            sys.exit(1)
        logger.info("Account validation successful")
        
    except AccountValidationError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
import json
import subprocess
from pathlib import Path
from typing import Dict, Set

import pytest
from account_validator import (
    AccountValidationError,
    load_rules,
    get_journal_accounts,
    validate_accounts,
)

@pytest.fixture
def temp_rules_file(tmp_path: Path) -> Path:
    """Create a temporary rules file with sample data."""
    rules = {
        "expense_rule": {"account": "Expenses:Rent"},
        "asset_rule": {"account": "Assets:Bank"}
    }
    rules_file = tmp_path / "test_rules.json"
    rules_file.write_text(json.dumps(rules))
    return rules_file

@pytest.fixture
def valid_journal(tmp_path: Path) -> Path:
    """Create a valid hledger journal file."""
    journal = """
2023-01-01 Opening balances
    Assets:Bank       1000
    Equity:Opening

2023-01-15 Rent payment
    Expenses:Rent    -1200
    Assets:Bank
"""
    journal_file = tmp_path / "valid.journal"
    journal_file.write_text(journal)
    return journal_file

@pytest.fixture
def invalid_journal(tmp_path: Path) -> Path:
    """Create an invalid journal file with syntax error."""
    journal_file = tmp_path / "invalid.journal"
    journal_file.write_text("invalid syntax")
    return journal_file

def test_load_rules_valid(temp_rules_file: Path):
    """Test loading valid rules file."""
    rules = load_rules(temp_rules_file)
    assert "expense_rule" in rules
    assert "asset_rule" in rules
    assert rules["expense_rule"]["account"] == "Expenses:Rent"

def test_load_rules_missing_file(tmp_path: Path):
    """Test handling missing rules file."""
    with pytest.raises(AccountValidationError):
        load_rules(tmp_path / "missing.json")

def test_load_rules_invalid_json(tmp_path: Path):
    """Test invalid JSON format in rules file."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{ invalid: data }")
    with pytest.raises(AccountValidationError):
        load_rules(invalid_file)

def test_get_journal_accounts_valid(valid_journal: Path):
    """Test getting accounts from valid journal."""
    accounts = get_journal_accounts(valid_journal)
    expected = {"Assets:Bank", "Equity:Opening", "Expenses:Rent"}
    assert accounts == expected

def test_get_journal_accounts_invalid(invalid_journal: Path):
    """Test invalid journal file raises error."""
    with pytest.raises(AccountValidationError):
        get_journal_accounts(invalid_journal)

def test_validate_all_accounts_present(valid_journal: Path, temp_rules_file: Path):
    """Test when all rule accounts exist."""
    rules = load_rules(temp_rules_file)
    assert validate_accounts(valid_journal, rules) is True

def test_validate_missing_accounts(tmp_path: Path):
    """Test when some rule accounts are missing."""
    rules = {
        "missing": {"account": "Missing:Account"},
        "existing": {"account": "Assets:Bank"}
    }
    journal = tmp_path / "partial.journal"
    journal.write_text("2023-01-01 Assets:Bank 100\n    Equity")
    assert validate_accounts(journal, rules) is False

def test_main_valid(capsys, valid_journal, temp_rules_file):
    """Test successful CLI execution."""
    import account_validator
    account_validator.main([str(valid_journal), str(temp_rules_file)])
    captured = capsys.readouterr()
    assert "Account validation successful" in captured.out

def test_main_missing_account(capsys, tmp_path):
    """Test CLI with missing account."""
    journal = tmp_path / "missing.journal"
    journal.write_text("2023-01-01 Assets:Bank 100\n    Equity")
    rules = tmp_path / "rules.json"
    rules.write_text('{"test":{"account":"Missing:Account"}}')
    try:
        import account_validator
        account_validator.main([str(journal), str(rules)])
    except SystemExit as e:
        assert e.code == 1

def test_main_invalid_args():
    """Test invalid CLI arguments."""
    import account_validator
    with pytest.raises(SystemExit):
        account_validator.main([])
