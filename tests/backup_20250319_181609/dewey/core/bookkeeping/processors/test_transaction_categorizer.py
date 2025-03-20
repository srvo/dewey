"""Tests for transaction categorizer."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
from dewey.core.bookkeeping.transaction_categorizer import (
    TransactionCategorizer,
    CategorizationRule,
    CategoryMatch
)

class TestTransactionCategorizer:
    """Test suite for transaction categorizer."""

    @pytest.fixture
    def categorizer(self, sample_rules_file, mock_llm_handler):
        """Create a TransactionCategorizer instance."""
        return TransactionCategorizer(
            rules_file=sample_rules_file,
            llm_handler=mock_llm_handler
        )

    def test_load_rules(self, categorizer):
        """Test loading categorization rules."""
        rules = categorizer.load_rules()
        assert len(rules) > 0
        assert all(isinstance(rule, CategorizationRule) for rule in rules)
        
        # Check specific rules
        amazon_rule = next(r for r in rules if r.pattern == "AMAZON")
        assert amazon_rule.category == "Expenses:Office:Supplies"
        assert amazon_rule.description == "Amazon purchases"

    def test_match_rule(self, categorizer):
        """Test rule matching."""
        transactions = [
            {"description": "AMAZON.COM", "amount": -50.00},
            {"description": "SALARY DEPOSIT", "amount": 1000.00},
            {"description": "UNKNOWN VENDOR", "amount": -25.00}
        ]
        
        for transaction in transactions:
            match = categorizer.match_rule(transaction)
            if "AMAZON" in transaction["description"]:
                assert match.category == "Expenses:Office:Supplies"
                assert match.confidence > 0.9
            elif "SALARY" in transaction["description"]:
                assert match.category == "Income:Salary"
                assert match.confidence > 0.9
            else:
                assert match is None

    def test_categorize_transaction(self, categorizer):
        """Test transaction categorization."""
        # Test with rule match
        amazon_tx = {"description": "AMAZON.COM", "amount": -50.00}
        result = categorizer.categorize_transaction(amazon_tx)
        assert result.category == "Expenses:Office:Supplies"
        assert result.confidence > 0.9
        assert result.method == "rule"

        # Test with LLM fallback
        unknown_tx = {"description": "UNKNOWN VENDOR", "amount": -25.00}
        result = categorizer.categorize_transaction(unknown_tx)
        assert result.category == "Expenses:Office:Supplies"  # From mock LLM response
        assert result.confidence > 0.9
        assert result.method == "llm"

    def test_categorize_transactions(self, categorizer, sample_transactions_df):
        """Test batch transaction categorization."""
        results = categorizer.categorize_transactions(sample_transactions_df)
        
        assert len(results) == len(sample_transactions_df)
        assert all(isinstance(r, CategoryMatch) for r in results)
        
        # Check specific categorizations
        amazon_result = next(r for r in results 
                           if "AMAZON" in r.transaction["description"])
        assert amazon_result.category == "Expenses:Office:Supplies"
        assert amazon_result.method == "rule"

    def test_update_rules(self, categorizer, tmp_path):
        """Test rules updating."""
        new_rule = CategorizationRule(
            pattern="NETFLIX",
            category="Expenses:Entertainment:Streaming",
            description="Netflix subscription"
        )
        
        categorizer.update_rules([new_rule])
        updated_rules = categorizer.load_rules()
        
        assert any(r.pattern == "NETFLIX" for r in updated_rules)
        assert any(r.category == "Expenses:Entertainment:Streaming" 
                  for r in updated_rules)

    def test_validate_category(self, categorizer):
        """Test category validation."""
        valid_categories = [
            "Assets:Checking",
            "Expenses:Office:Supplies",
            "Income:Salary",
            "Liabilities:CreditCard"
        ]
        for category in valid_categories:
            assert categorizer.validate_category(category) is True

        invalid_categories = [
            "assets:checking",  # lowercase
            "Expenses:",  # ends with colon
            "Income/Salary",  # invalid character
            ""  # empty string
        ]
        for category in invalid_categories:
            assert categorizer.validate_category(category) is False

    def test_confidence_threshold(self, categorizer):
        """Test confidence threshold handling."""
        # Test with high confidence rule match
        high_conf_tx = {"description": "AMAZON.COM", "amount": -50.00}
        result = categorizer.categorize_transaction(
            high_conf_tx, confidence_threshold=0.8
        )
        assert result.category == "Expenses:Office:Supplies"
        assert result.confidence > 0.8

        # Test with low confidence match
        low_conf_tx = {"description": "AMZ", "amount": -50.00}  # Partial match
        result = categorizer.categorize_transaction(
            low_conf_tx, confidence_threshold=0.9
        )
        assert result.method == "llm"  # Falls back to LLM due to low confidence

    def test_error_handling(self, categorizer):
        """Test error handling."""
        # Invalid transaction format
        with pytest.raises(ValueError):
            categorizer.categorize_transaction({})  # Empty transaction

        # Invalid rules file
        with pytest.raises(Exception):
            TransactionCategorizer(rules_file=Path("nonexistent.json"))

    @pytest.mark.integration
    def test_full_categorization_workflow(self, categorizer, sample_transactions_df):
        """Integration test for full categorization workflow."""
        # Load rules
        rules = categorizer.load_rules()
        assert len(rules) > 0

        # Categorize transactions
        results = categorizer.categorize_transactions(sample_transactions_df)
        assert len(results) == len(sample_transactions_df)

        # Verify all transactions are categorized
        assert all(r.category is not None for r in results)
        assert all(r.confidence > 0 for r in results)

        # Check categorization methods distribution
        rule_matches = sum(1 for r in results if r.method == "rule")
        llm_matches = sum(1 for r in results if r.method == "llm")
        assert rule_matches + llm_matches == len(results)

        # Verify categories are valid
        assert all(categorizer.validate_category(r.category) for r in results) 