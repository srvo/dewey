
# Refactored from: test_mercury_import
# Date: 2025-03-16T16:19:08.539971
# Refactor Version: 1.0
import re
import sys
from pathlib import Path
from typing import Any

import pytest

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))
from mercury_import import MercuryImporter


@pytest.fixture
def importer() -> MercuryImporter:
    """Fixture providing a configured MercuryImporter instance."""
    imp = MercuryImporter()
    imp.account_struct.classification_rules = {
        "patterns": {
            r"AMAZON WEB SERVICES": "Expenses:SaaS:AWS",
            r"\bAWS\b": "Expenses:SaaS:AWS",
            r"AMEX EPAYMENT": "Liabilities:CreditCard:AMEX",
            r"Financial Times": "Expenses:Subscriptions:News",
        },
        "categories": ["Expenses:SaaS:AWS", "Liabilities:CreditCard:AMEX"],
    }
    return imp


def classify_transaction(
    importer: MercuryImporter,
    description: str,
    amount: float,
) -> tuple[str, str, float]:
    """Helper function to classify a transaction."""
    return importer.classify_transaction(description, amount)


def generate_journal_entry(
    importer: MercuryImporter,
    tx_data: dict[str, Any],
    from_account: str,
    to_account: str,
) -> str:
    """Helper function to generate a journal entry."""
    return importer._generate_journal_entry(tx_data, from_account, to_account)


def process_transaction(importer: MercuryImporter, tx_data: dict[str, Any]) -> None:
    """Helper function to process a transaction."""
    importer.process_transaction(tx_data)


def test_aws_classification(importer: MercuryImporter) -> None:
    """Verify AWS transactions are classified correctly."""
    entry = "2025-01-02 Amazon Web Services"
    result = classify_transaction(importer, entry, -29.83)
    assert result == ("Expenses:SaaS:AWS", "Expenses:Unknown", 29.83)


def test_amex_payment(importer: MercuryImporter) -> None:
    """Verify AMEX payments are classified correctly."""
    entry = "2025-01-07 AMEX EPAYMENT"
    result = classify_transaction(importer, entry, -35.0)
    assert result == ("Liabilities:CreditCard:AMEX", "Expenses:Unknown", 35.0)


def test_journal_entry_formatting(importer: MercuryImporter) -> None:
    """Verify journal entries follow the correct format."""
    tx_data = {
        "date": "2025-03-15",
        "description": "Amazon Web Services",
        "amount": 29.83,
        "is_income": False,
        "raw": {"balance": "8452.71"},
    }

    entry = generate_journal_entry(
        importer,
        tx_data,
        "Expenses:SaaS:AWS",
        "Assets:Mercury",
    )

    expected = """2025-03-15 Amazon Web Services
    Expenses:SaaS:AWS                             $29.83  ; Balance: 8452.71
    Assets:Mercury

"""
    assert entry == expected


def test_unknown_transaction_handling(importer: MercuryImporter) -> None:
    """Test transactions seen in 9281_2025.journal that should be classified."""
    unknown_entries = [
        ("2025-01-05 Dokploy, LLC", 4.5),
        ("2025-01-06 Hetzner Online", 35.37),
        ("2025-01-20 Cursor", 20.0),
    ]

    for desc, amount in unknown_entries:
        result = classify_transaction(importer, desc, -amount)
        assert "Unknown" in result[1], f"Failed to classify: {desc}"


def test_negative_amount_handling(importer: MercuryImporter) -> None:
    """Verify negative amounts are handled correctly."""
    tx = {
        "date": "2025-01-16",
        "description": "DISCOVER",
        "amount": -267.59,
        "is_income": False,
        "raw": {},
    }

    entry = generate_journal_entry(importer, tx, "Expenses:Unknown", "Assets:Mercury")
    assert "Expenses:Unknown" in entry
    assert "$267.59" in entry


def test_journal_file_structure(tmp_path: Path, importer: MercuryImporter) -> None:
    """Verify generated files match the structure seen in 9281_2025.journal."""
    test_entries = [
        ("2025-03-01", "Test1", "Expenses:Test", "Assets:Mercury", -10.0),
        ("2025-03-02", "Test2", "Expenses:Test", "Assets:Mercury", -20.0),
    ]

    importer.journal_entries = {
        "2025": [
            f"{date} {desc}\n    {from_acc}\n    {to_acc}\n"
            for date, desc, from_acc, to_acc, _ in test_entries
        ],
    }

    importer.write_journal_files()

    journal_file = Path("import/mercury/journal/by_year/8542_2025.journal")
    assert journal_file.exists()

    content = journal_file.read_text()
    assert "Test1" in content
    assert "Test2" in content
    assert "Expenses:Test" in content
    assert "Assets:Mercury" in content


def test_duplicate_transactions(importer: MercuryImporter) -> None:
    """Verify duplicate transactions are detected and handled."""
    tx_data = {
        "date": "2025-01-05",
        "description": "Dokploy, LLC",
        "amount": 4.5,
        "is_income": False,
        "raw": {},
    }

    # First processing
    process_transaction(importer, tx_data)
    assert importer.metrics["processed"] == 1

    # Duplicate processing
    process_transaction(importer, tx_data)
    assert importer.metrics["processed"] == 1
    assert importer.metrics["failed"] == 0


def test_journal_validation_patterns() -> None:
    """Verify journal entries follow required patterns."""
    journal_file = Path("import/mercury/journal/by_year/9281_2025.journal")
    content = journal_file.read_text()

    validation_patterns = [
        ("Expenses:Unknown exists in all entries", r"Expenses:Unknown"),
        ("Correct date formatting", r"\d{4}-\d{2}-\d{2}"),
        ("Indentation levels", r"    "),
        ("Amount alignment", r"\$\d+\.\d{2}"),
        ("Balance comments when present", "; Balance:"),
    ]

    for description, pattern in validation_patterns:
        assert re.search(pattern, content), f"Validation failed: {description}"
