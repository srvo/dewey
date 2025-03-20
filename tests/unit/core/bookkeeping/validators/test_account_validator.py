"""Tests for account validator."""

import pytest
from dewey.core.bookkeeping.account_validator import (
    AccountValidator,
    ValidationError,
    AccountValidationResult,
)


class TestAccountValidator:
    """Test suite for account validator."""

    @pytest.fixture
    def validator(self, sample_journal_dir):
        """Create an AccountValidator instance."""
        return AccountValidator(journal_dir=sample_journal_dir)

    def test_validate_account_structure(self, validator):
        """Test account structure validation."""
        valid_accounts = [
            "Assets:Checking",
            "Expenses:Office:Supplies",
            "Income:Consulting:Training",
        ]
        for account in valid_accounts:
            result = validator.validate_account_structure(account)
            assert result.is_valid
            assert not result.errors

        invalid_accounts = [
            "assets:checking",  # lowercase
            "Expenses:",  # ends with colon
            "Income/Consulting",  # invalid character
            "A",  # too short
        ]
        for account in invalid_accounts:
            result = validator.validate_account_structure(account)
            assert not result.is_valid
            assert len(result.errors) > 0

    def test_validate_account_balance(self, validator, mock_subprocess_run):
        """Test account balance validation."""
        mock_subprocess_run.return_value.stdout = """
Assets:Checking  $1000.00
"""
        result = validator.validate_account_balance("Assets:Checking")
        assert result.is_valid
        assert result.balance == 1000.00

    def test_validate_account_transactions(self, validator, mock_subprocess_run):
        """Test account transactions validation."""
        mock_subprocess_run.return_value.stdout = """
2024-01-01 Opening Balance
    Assets:Checking          $1000.00
    Equity:Opening Balance  $-1000.00
"""
        result = validator.validate_account_transactions("Assets:Checking")
        assert result.is_valid
        assert len(result.transactions) == 1

    def test_validate_account_hierarchy(self, validator):
        """Test account hierarchy validation."""
        hierarchy = {
            "Assets": ["Checking", "Savings"],
            "Expenses": ["Office", "Travel"],
            "Income": ["Salary", "Consulting"],
        }

        # Valid accounts
        for parent, children in hierarchy.items():
            for child in children:
                account = f"{parent}:{child}"
                result = validator.validate_account_hierarchy(account)
                assert result.is_valid
                assert result.parent == parent
                assert result.level == 2

        # Invalid hierarchy
        result = validator.validate_account_hierarchy("Invalid:Account:Structure")
        assert not result.is_valid
        assert "Invalid account hierarchy" in result.errors[0]

    def test_validate_account_type(self, validator):
        """Test account type validation."""
        type_tests = [
            ("Assets:Checking", "Assets"),
            ("Liabilities:CreditCard", "Liabilities"),
            ("Expenses:Office", "Expenses"),
            ("Income:Salary", "Income"),
            ("Equity:Opening", "Equity"),
        ]

        for account, expected_type in type_tests:
            result = validator.validate_account_type(account)
            assert result.is_valid
            assert result.account_type == expected_type

    def test_validate_account_exists(self, validator, mock_subprocess_run):
        """Test account existence validation."""
        mock_subprocess_run.return_value.stdout = """
Assets:Checking
Expenses:Office
Income:Salary
"""
        # Existing accounts
        for account in ["Assets:Checking", "Expenses:Office", "Income:Salary"]:
            result = validator.validate_account_exists(account)
            assert result.is_valid
            assert not result.errors

        # Non-existing account
        result = validator.validate_account_exists("NonExistent:Account")
        assert not result.is_valid
        assert "Account does not exist" in result.errors[0]

    def test_validate_account_permissions(self, validator):
        """Test account permissions validation."""
        # Read-only accounts
        readonly_accounts = ["Equity:OpeningBalance", "Assets:FixedAssets"]
        for account in readonly_accounts:
            result = validator.validate_account_permissions(account)
            assert not result.can_modify
            assert "Read-only account" in result.notes

        # Modifiable accounts
        modifiable_accounts = ["Assets:Checking", "Expenses:Office"]
        for account in modifiable_accounts:
            result = validator.validate_account_permissions(account)
            assert result.can_modify
            assert not result.notes

    def test_full_account_validation(self, validator, mock_subprocess_run):
        """Test full account validation process."""
        account = "Assets:Checking"
        result = validator.validate_account(account)

        assert result.is_valid
        assert result.account == account
        assert result.account_type == "Assets"
        assert result.balance is not None
        assert len(result.transactions) > 0
        assert not result.errors

    def test_validation_error_handling(self, validator):
        """Test validation error handling."""
        with pytest.raises(ValidationError) as exc:
            validator.validate_account("")
        assert "Empty account name" in str(exc.value)

    @pytest.mark.integration
    def test_batch_account_validation(self, validator, mock_subprocess_run):
        """Integration test for batch account validation."""
        accounts = [
            "Assets:Checking",
            "Expenses:Office",
            "Income:Salary",
            "Invalid:Account",  # Should fail
        ]

        results = validator.validate_accounts(accounts)

        assert len(results) == len(accounts)
        assert sum(1 for r in results if r.is_valid) == 3  # 3 valid accounts
        assert sum(1 for r in results if not r.is_valid) == 1  # 1 invalid account

        # Check specific results
        for result in results:
            if result.account == "Invalid:Account":
                assert not result.is_valid
                assert len(result.errors) > 0
            else:
                assert result.is_valid
                assert not result.errors
