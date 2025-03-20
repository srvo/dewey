"""Common test fixtures for bookkeeping tests."""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime, date
import pandas as pd

@pytest.fixture
def sample_journal_dir(tmp_path):
    """Create a temporary directory with sample journal files."""
    journal_dir = tmp_path / "journals"
    journal_dir.mkdir()
    
    # Create sample journal files
    sample_content = """
2024-01-01 Opening Balance
    Assets:Checking          $1000.00
    Equity:Opening Balance  $-1000.00

2024-01-15 Sample Transaction
    Expenses:Office         $50.00
    Assets:Checking       $-50.00
"""
    (journal_dir / "2024.journal").write_text(sample_content)
    return journal_dir

@pytest.fixture
def sample_rules_file(tmp_path):
    """Create a sample classification rules file."""
    rules = {
        "rules": [
            {
                "pattern": "AMAZON",
                "category": "Expenses:Office:Supplies",
                "description": "Amazon purchases"
            },
            {
                "pattern": "SALARY",
                "category": "Income:Salary",
                "description": "Salary deposits"
            }
        ]
    }
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(str(rules))
    return rules_file

@pytest.fixture
def sample_transactions_df():
    """Create a sample transactions DataFrame."""
    return pd.DataFrame({
        "date": [date(2024, 1, 15), date(2024, 1, 16)],
        "description": ["AMAZON.COM", "SALARY DEPOSIT"],
        "amount": [-50.00, 1000.00],
        "account": ["Assets:Checking", "Assets:Checking"],
        "category": ["Expenses:Office:Supplies", "Income:Salary"]
    })

@pytest.fixture
def sample_mercury_data(tmp_path):
    """Create sample Mercury bank data files."""
    data_dir = tmp_path / "mercury"
    data_dir.mkdir()
    
    csv_content = """Date,Description,Amount,Type,Category
2024-01-15,AMAZON.COM,-50.00,debit,Office Supplies
2024-01-16,SALARY DEPOSIT,1000.00,credit,Income"""
    
    (data_dir / "mercury_export.csv").write_text(csv_content)
    return data_dir

@pytest.fixture
def mock_hledger_output():
    """Mock hledger command output."""
    return """
2024-01-01 Opening Balance
    Assets:Checking          $1000.00
    Equity:Opening Balance  $-1000.00

2024-01-15 Sample Transaction
    Expenses:Office         $50.00
    Assets:Checking       $-50.00
"""

@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run for hledger commands."""
    mock = MagicMock()
    mock.return_value.returncode = 0
    mock.return_value.stdout = mock_hledger_output()
    monkeypatch.setattr("subprocess.run", mock)
    return mock

@pytest.fixture
def mock_llm_handler():
    """Mock LLM handler for auto-categorization."""
    mock = MagicMock()
    mock.generate_response.return_value = {
        "category": "Expenses:Office:Supplies",
        "confidence": 0.95,
        "explanation": "This appears to be an office supply purchase."
    }
    return mock

@pytest.fixture
def sample_forecast_data():
    """Create sample forecast data."""
    return pd.DataFrame({
        "date": pd.date_range(start="2024-01-01", periods=12, freq="M"),
        "category": ["Income:Salary"] * 12,
        "amount": [5000.00] * 12,
        "probability": [1.0] * 12
    })

@pytest.fixture
def sample_deferred_revenue_data():
    """Create sample deferred revenue data."""
    return pd.DataFrame({
        "date": pd.date_range(start="2024-01-01", periods=12, freq="M"),
        "contract_id": ["C001"] * 12,
        "amount": [1000.00] * 12,
        "recognition_date": pd.date_range(start="2024-02-01", periods=12, freq="M")
    }) 