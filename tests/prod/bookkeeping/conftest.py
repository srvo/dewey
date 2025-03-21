"""Common fixtures for bookkeeping module tests."""

import json
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_base_script():
    """Fixture to mock BaseScript initialization."""
    with patch("dewey.core.base_script.BaseScript.__init__", return_value=None) as mock_init:
        yield mock_init


@pytest.fixture
def mock_logger():
    """Fixture to provide a mock logger."""
    logger = MagicMock()
    yield logger


@pytest.fixture
def mock_config():
    """Fixture to provide a mock configuration."""
    config: Dict[str, Dict[str, str]] = {
        "bookkeeping": {
            "ledger_dir": "data/bookkeeping/ledger",
            "start_year": "2022",
            "journal_base_dir": "data/bookkeeping/journals",
            "classification_rules": "data/bookkeeping/rules/classification_rules.json"
        }
    }
    yield config


@pytest.fixture
def mock_db_connection():
    """Fixture to provide a mock database connection."""
    conn = MagicMock()
    yield conn


@pytest.fixture
def sample_transaction_data():
    """Fixture to provide sample transaction data."""
    return [
        {
            "date": "2023-01-01",
            "description": "Client payment",
            "amount": 1000,
            "account": "Income:Payment"
        },
        {
            "date": "2023-01-05",
            "description": "Grocery shopping",
            "amount": -50,
            "account": "Expenses:Groceries"
        },
        {
            "date": "2023-01-10",
            "description": "Coffee shop",
            "amount": -5,
            "account": "Expenses:Uncategorized"
        }
    ]


@pytest.fixture
def sample_classification_rules():
    """Fixture to provide sample classification rules."""
    return {
        "patterns": [
            {"regex": "payment", "category": "Income:Payment"},
            {"regex": "grocery", "category": "Expenses:Groceries"},
            {"regex": "coffee", "category": "Expenses:Food:Coffee"}
        ],
        "default_category": "Expenses:Uncategorized"
    }


@pytest.fixture
def sample_account_rules():
    """Fixture to provide sample account rules."""
    return {
        "categories": [
            "Assets:Checking",
            "Income:Salary",
            "Expenses:Food",
            "Expenses:Utilities"
        ]
    }


@pytest.fixture
def sample_journal_content():
    """Fixture to provide sample journal content."""
    return """
2023-01-01 Opening Balances
    assets:checking:mercury8542    = $9,500.00
    assets:checking:mercury9281    = $4,500.00
    equity:opening balances
""" 