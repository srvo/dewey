"""Shared fixtures for bookkeeping tests."""

import json
import os
import pytest
from pathlib import Path
from typing import Any, Dict


@pytest.fixture
def sample_journal_entry() -> Dict[str, Any]:
    """Sample journal entry for testing."""
    return {
        "date": "2024-01-01",
        "description": "Test Transaction",
        "amount": 100.00,
        "account": "assets:checking:primary",
        "category": "expenses:test",
    }


@pytest.fixture
def sample_journal_file(tmp_path: Path, sample_journal_entry: Dict[str, Any]) -> Path:
    """Create a sample journal file for testing."""
    journal_data = {"transactions": [sample_journal_entry]}
    journal_file = tmp_path / "test.journal"
    journal_file.write_text(json.dumps(journal_data, indent=2))
    return journal_file


@pytest.fixture
def sample_rules_file(tmp_path: Path) -> Path:
    """Create a sample rules file for testing."""
    rules = {
        "patterns": [{"regex": "test", "category": "expenses:test"}],
        "default_category": "expenses:uncategorized",
    }
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps(rules, indent=2))
    return rules_file


@pytest.fixture
def sample_year_directory(tmp_path: Path, sample_journal_file: Path) -> Path:
    """Create a sample year directory with journal files."""
    year_dir = tmp_path / "2024"
    year_dir.mkdir()
    dest_file = year_dir / "transactions.json"
    dest_file.write_text(sample_journal_file.read_text())
    return year_dir


@pytest.fixture
def clean_env():
    """Clean environment variables that might affect tests."""
    # Save original environment
    original_env = {}
    vars_to_clean = ["JOURNAL_BASE_DIR", "CLASSIFICATION_RULES", "HLEDGER_FILE"]

    for var in vars_to_clean:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]

    yield

    # Restore original environment
    for var, value in original_env.items():
        os.environ[var] = value
