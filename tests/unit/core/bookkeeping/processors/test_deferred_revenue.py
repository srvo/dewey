"""Tests for deferred revenue processor."""

import pytest
import pandas as pd
from datetime import date
from dewey.core.bookkeeping.deferred_revenue import (
    DeferredRevenueProcessor,
    RevenueRecognition,
    RecognitionSchedule,
)


class TestDeferredRevenueProcessor:
    """Test suite for deferred revenue processor."""

    @pytest.fixture
    def processor(self, sample_journal_dir, mock_db_connection):
        """Create a DeferredRevenueProcessor instance."""
        return DeferredRevenueProcessor(
            journal_dir=sample_journal_dir, db_connection=mock_db_connection
        )

    def test_create_recognition_schedule(self, processor):
        """Test creation of revenue recognition schedule."""
        contract = {
            "contract_id": "C001",
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "total_amount": 12000.00,
            "recognition_method": "straight_line",
        }

        schedule = processor.create_recognition_schedule(contract)

        assert isinstance(schedule, RecognitionSchedule)
        assert len(schedule.entries) == 12  # Monthly recognition
        assert sum(e.amount for e in schedule.entries) == contract["total_amount"]
        assert all(
            e.amount == 1000.00 for e in schedule.entries
        )  # Equal monthly amounts

    def test_process_recognition_entry(self, processor):
        """Test processing of individual recognition entry."""
        entry = RevenueRecognition(
            contract_id="C001",
            recognition_date=date(2024, 1, 31),
            amount=1000.00,
            description="January 2024 revenue recognition",
        )

        result = processor.process_recognition_entry(entry)
        assert result.success
        assert result.journal_entry is not None
        assert "Assets:DeferredRevenue" in result.journal_entry
        assert "Income:Revenue" in result.journal_entry

    def test_calculate_monthly_recognition(self, processor):
        """Test calculation of monthly recognition amounts."""
        test_cases = [
            {"total": 12000.00, "months": 12, "expected": 1000.00},
            {"total": 5000.00, "months": 5, "expected": 1000.00},
            {"total": 1500.00, "months": 3, "expected": 500.00},
        ]

        for case in test_cases:
            amount = processor.calculate_monthly_recognition(
                case["total"], case["months"]
            )
            assert amount == case["expected"]

    def test_validate_contract_dates(self, processor):
        """Test contract date validation."""
        valid_dates = {"start_date": date(2024, 1, 1), "end_date": date(2024, 12, 31)}
        assert processor.validate_contract_dates(valid_dates) is True

        invalid_dates = [
            {
                "start_date": date(2024, 12, 31),
                "end_date": date(2024, 1, 1),  # End before start
            },
            {
                "start_date": date(2024, 1, 1),
                "end_date": date(2023, 12, 31),  # End in past
            },
        ]
        for dates in invalid_dates:
            assert processor.validate_contract_dates(dates) is False

    def test_process_deferred_revenue(self, processor, sample_deferred_revenue_data):
        """Test processing of deferred revenue data."""
        results = processor.process_deferred_revenue(sample_deferred_revenue_data)

        assert len(results) == len(sample_deferred_revenue_data)
        assert all(r.success for r in results)
        assert all(r.journal_entry is not None for r in results)

    def test_generate_journal_entries(self, processor):
        """Test journal entry generation."""
        recognition = RevenueRecognition(
            contract_id="C001",
            recognition_date=date(2024, 1, 31),
            amount=1000.00,
            description="January 2024 revenue recognition",
        )

        entry = processor.generate_journal_entry(recognition)
        assert "date" in entry
        assert "description" in entry
        assert "postings" in entry
        assert len(entry["postings"]) == 2  # Debit and credit entries

    def test_validate_recognition_amount(self, processor):
        """Test validation of recognition amounts."""
        valid_cases = [
            (1000.00, 12000.00),  # Monthly recognition of annual contract
            (500.00, 1500.00),  # Monthly recognition of quarterly contract
        ]
        for amount, total in valid_cases:
            assert processor.validate_recognition_amount(amount, total) is True

        invalid_cases = [
            (-1000.00, 12000.00),  # Negative amount
            (2000.00, 1000.00),  # Amount larger than total
            (0.00, 1000.00),  # Zero amount
        ]
        for amount, total in invalid_cases:
            assert processor.validate_recognition_amount(amount, total) is False

    def test_error_handling(self, processor):
        """Test error handling."""
        # Invalid contract data
        with pytest.raises(ValueError):
            processor.create_recognition_schedule({})

        # Invalid recognition entry
        with pytest.raises(ValueError):
            processor.process_recognition_entry(None)

    @pytest.mark.integration
    def test_full_revenue_recognition_workflow(
        self, processor, sample_deferred_revenue_data
    ):
        """Integration test for full revenue recognition workflow."""
        # Process all contracts
        results = processor.process_deferred_revenue(sample_deferred_revenue_data)
        assert len(results) > 0

        # Verify results
        total_recognized = sum(r.recognition.amount for r in results if r.success)
        total_expected = sample_deferred_revenue_data["amount"].sum()
        assert total_recognized == total_expected

        # Check journal entries
        journal_entries = [r.journal_entry for r in results if r.success]
        assert all("Assets:DeferredRevenue" in entry for entry in journal_entries)
        assert all("Income:Revenue" in entry for entry in journal_entries)

        # Verify amounts balance
        for entry in journal_entries:
            debits = sum(p["amount"] for p in entry["postings"] if p["amount"] > 0)
            credits = sum(p["amount"] for p in entry["postings"] if p["amount"] < 0)
            assert abs(debits + credits) < 0.01  # Account for floating point
