"""Tests for tax reporting processor."""

import pytest
import pandas as pd
from datetime import date
from dewey.core.bookkeeping.tax_reporting import (
    TaxReportingProcessor,
    TaxCategory,
    TaxReport,
    ReportingPeriod,
)


class TestTaxReportingProcessor:
    """Test suite for tax reporting processor."""

    @pytest.fixture
    def processor(self, sample_journal_dir, mock_db_connection):
        """Create a TaxReportingProcessor instance."""
        return TaxReportingProcessor(
            journal_dir=sample_journal_dir,
            db_connection=mock_db_connection,
            tax_year=2024,
        )

    @pytest.fixture
    def sample_transactions(self):
        """Create sample transactions for tax reporting."""
        return [
            {
                "date": date(2024, 1, 15),
                "amount": 5000.00,
                "description": "Consulting Income",
                "account": "Income:Consulting",
                "tax_category": TaxCategory.BUSINESS_INCOME,
            },
            {
                "date": date(2024, 1, 20),
                "amount": 1000.00,
                "description": "Office Supplies",
                "account": "Expenses:Office",
                "tax_category": TaxCategory.BUSINESS_EXPENSE,
            },
            {
                "date": date(2024, 2, 1),
                "amount": 2000.00,
                "description": "Equipment Purchase",
                "account": "Assets:Equipment",
                "tax_category": TaxCategory.CAPITAL_EXPENSE,
            },
        ]

    def test_categorize_transactions(self, processor, sample_transactions):
        """Test categorization of transactions for tax purposes."""
        categorized = processor.categorize_transactions(sample_transactions)

        assert len(categorized) == len(sample_transactions)
        assert all(t["tax_category"] is not None for t in categorized)

        # Verify specific categories
        income_items = [
            t for t in categorized if t["tax_category"] == TaxCategory.BUSINESS_INCOME
        ]
        expense_items = [
            t for t in categorized if t["tax_category"] == TaxCategory.BUSINESS_EXPENSE
        ]
        capital_items = [
            t for t in categorized if t["tax_category"] == TaxCategory.CAPITAL_EXPENSE
        ]

        assert len(income_items) > 0
        assert len(expense_items) > 0
        assert len(capital_items) > 0

    def test_calculate_period_totals(self, processor, sample_transactions):
        """Test calculation of period totals."""
        period = ReportingPeriod(
            start_date=date(2024, 1, 1), end_date=date(2024, 3, 31)
        )

        totals = processor.calculate_period_totals(sample_transactions, period)

        assert "income" in totals
        assert "expenses" in totals
        assert "capital_expenses" in totals
        assert totals["income"] > 0
        assert totals["expenses"] > 0
        assert totals["capital_expenses"] > 0

    def test_generate_tax_report(self, processor, sample_transactions):
        """Test generation of tax report."""
        report = processor.generate_tax_report(sample_transactions)

        assert isinstance(report, TaxReport)
        assert report.year == 2024
        assert report.total_income > 0
        assert report.total_expenses > 0
        assert report.net_income > 0
        assert len(report.categories) > 0

    def test_validate_tax_categories(self, processor):
        """Test validation of tax categories."""
        valid_categories = [
            TaxCategory.BUSINESS_INCOME,
            TaxCategory.BUSINESS_EXPENSE,
            TaxCategory.CAPITAL_EXPENSE,
        ]
        for category in valid_categories:
            assert processor.validate_tax_category(category) is True

        # Test invalid category
        with pytest.raises(ValueError):
            processor.validate_tax_category("INVALID_CATEGORY")

    def test_calculate_quarterly_estimates(self, processor, sample_transactions):
        """Test calculation of quarterly tax estimates."""
        estimates = processor.calculate_quarterly_estimates(sample_transactions)

        assert len(estimates) == 4  # Four quarters
        assert all(e > 0 for e in estimates.values())
        assert sum(estimates.values()) > 0

    def test_generate_schedule_c(self, processor, sample_transactions):
        """Test generation of Schedule C data."""
        schedule_c = processor.generate_schedule_c(sample_transactions)

        assert "gross_income" in schedule_c
        assert "total_expenses" in schedule_c
        assert "net_profit" in schedule_c
        assert (
            schedule_c["net_profit"]
            == schedule_c["gross_income"] - schedule_c["total_expenses"]
        )

    def test_calculate_depreciation(self, processor):
        """Test calculation of depreciation for capital expenses."""
        asset = {
            "description": "Office Equipment",
            "purchase_date": date(2024, 1, 1),
            "cost": 2000.00,
            "useful_life": 5,  # years
        }

        depreciation = processor.calculate_depreciation(asset)
        assert depreciation == 400.00  # Straight line depreciation

    def test_validate_reporting_period(self, processor):
        """Test validation of reporting period."""
        valid_period = ReportingPeriod(
            start_date=date(2024, 1, 1), end_date=date(2024, 12, 31)
        )
        assert processor.validate_reporting_period(valid_period) is True

        invalid_periods = [
            ReportingPeriod(
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),  # End before start
            ),
            ReportingPeriod(
                start_date=date(2023, 1, 1), end_date=date(2023, 12, 31)  # Wrong year
            ),
        ]
        for period in invalid_periods:
            assert processor.validate_reporting_period(period) is False

    def test_error_handling(self, processor):
        """Test error handling."""
        # Invalid transaction data
        with pytest.raises(ValueError):
            processor.categorize_transactions(None)

        # Invalid reporting period
        with pytest.raises(ValueError):
            processor.calculate_period_totals([], None)

    @pytest.mark.integration
    def test_full_tax_reporting_workflow(self, processor, sample_transactions):
        """Integration test for full tax reporting workflow."""
        # Generate full tax report
        report = processor.generate_tax_report(sample_transactions)

        # Verify report contents
        assert report.year == 2024
        assert report.total_income > 0
        assert report.total_expenses > 0
        assert report.net_income > 0

        # Check quarterly estimates
        estimates = processor.calculate_quarterly_estimates(sample_transactions)
        assert len(estimates) == 4
        assert all(e > 0 for e in estimates.values())

        # Generate Schedule C
        schedule_c = processor.generate_schedule_c(sample_transactions)
        assert schedule_c["net_profit"] > 0

        # Verify category totals
        for category in report.categories:
            assert category.total > 0
            assert processor.validate_tax_category(category.name)

        # Check depreciation calculations
        capital_items = [
            t
            for t in sample_transactions
            if t["tax_category"] == TaxCategory.CAPITAL_EXPENSE
        ]
        for item in capital_items:
            asset = {
                "description": item["description"],
                "purchase_date": item["date"],
                "cost": item["amount"],
                "useful_life": 5,
            }
            depreciation = processor.calculate_depreciation(asset)
            assert depreciation > 0
