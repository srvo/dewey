"""Unit tests for the opportunity_detection module."""

import logging
import re
import sqlite3
from typing import Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dewey.core.crm.enrichment.opportunity_detection import OpportunityDetector


class TestOpportunityDetector:
    """Tests for the OpportunityDetector class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Mocks the BaseScript class."""
        mock = MagicMock()
        mock.get_config_value.return_value = {
            "demo": r"\bdemo\b",
            "cancellation": r"\bcancel\b",
            "speaking": r"\bspeaking\b",
            "publicity": r"\bpublicity\b",
            "submission": r"\bsubmission\b",
        }
        mock.logger = MagicMock()
        return mock

    @pytest.fixture
    def opportunity_detector(self, mock_base_script: MagicMock) -> OpportunityDetector:
        """Returns an instance of OpportunityDetector with mocked dependencies."""
        with patch(
            "dewey.core.crm.enrichment.opportunity_detection.BaseScript",
            return_value=mock_base_script,
        ):
            detector = OpportunityDetector()
        return detector

    def test_extract_opportunities(
        self, opportunity_detector: OpportunityDetector
    ) -> None:
        """Tests the extract_opportunities method."""
        email_text = "This is an email about a demo and a cancellation."
        opportunities = opportunity_detector.extract_opportunities(email_text)
        assert isinstance(opportunities, Dict)
        assert opportunities["demo"] is True
        assert opportunities["cancellation"] is True
        assert opportunities["speaking"] is False
        assert opportunities["publicity"] is False
        assert opportunities["submission"] is False

    def test_extract_opportunities_empty_email(
        self, opportunity_detector: OpportunityDetector
    ) -> None:
        """Tests extract_opportunities with an empty email."""
        email_text = ""
        opportunities = opportunity_detector.extract_opportunities(email_text)
        assert all(value is False for value in opportunities.values())

    def test_extract_opportunities_no_match(
        self, opportunity_detector: OpportunityDetector
    ) -> None:
        """Tests extract_opportunities when no patterns match."""
        email_text = "This is a regular email."
        opportunities = opportunity_detector.extract_opportunities(email_text)
        assert all(value is False for value in opportunities.values())

    def test_extract_opportunities_case_insensitive(
        self, opportunity_detector: OpportunityDetector
    ) -> None:
        """Tests that extract_opportunities is case-insensitive."""
        email_text = "This email mentions a DEMO."
        opportunities = opportunity_detector.extract_opportunities(email_text)
        assert opportunities["demo"] is True

    def test_update_contacts_db(
        self, opportunity_detector: OpportunityDetector
    ) -> None:
        """Tests the update_contacts_db method."""
        conn = MagicMock()
        opportunities_data = {
            "from_email": ["test@example.com", "test2@example.com"],
            "demo": [True, False],
            "cancellation": [False, True],
            "speaking": [True, False],
            "publicity": [False, True],
            "submission": [True, False],
        }
        opportunities_df = pd.DataFrame(opportunities_data)

        opportunity_detector.update_contacts_db(opportunities_df, conn)

        assert conn.execute.call_count == 2
        conn.execute.assert_called_with(
            """
                UPDATE contacts
                SET
                    demo_opportunity = ?,
                    cancellation_request = ?,
                    speaking_opportunity = ?,
                    publicity_opportunity = ?,
                    paper_submission_opportunity = ?
                WHERE email = ?
                """,
            (
                opportunities_data["demo"][1],
                opportunities_data["cancellation"][1],
                opportunities_data["speaking"][1],
                opportunities_data["publicity"][1],
                opportunities_data["submission"][1],
                opportunities_data["from_email"][1],
            ),
        )

    def test_update_contacts_db_error_handling(
        self, opportunity_detector: OpportunityDetector
    ) -> None:
        """Tests error handling in update_contacts_db."""
        conn = MagicMock()
        conn.execute.side_effect = Exception("Database error")
        opportunities_data = {
            "from_email": ["test@example.com"],
            "demo": [True],
            "cancellation": [False],
            "speaking": [True],
            "publicity": [False],
            "submission": [True],
        }
        opportunities_df = pd.DataFrame(opportunities_data)

        opportunity_detector.update_contacts_db(opportunities_df, conn)

        opportunity_detector.logger.error.assert_called_once()

    def test_detect_opportunities(
        self, opportunity_detector: OpportunityDetector
    ) -> None:
        """Tests the detect_opportunities method."""
        conn = MagicMock()
        query_result = [
            (
                "1",
                "test@example.com",
                "Subject",
                "This is an email about a demo.",
            ),
            (
                "2",
                "test2@example.com",
                "Subject",
                "This is an email about a cancellation.",
            ),
        ]
        df = pd.DataFrame(
            query_result,
            columns=["message_id", "from_email", "subject", "full_message"],
        )
        with patch("pandas.read_sql_query", return_value=df):
            opportunity_detector.update_contacts_db = MagicMock()
            opportunity_detector.detect_opportunities(conn)
            opportunity_detector.update_contacts_db.assert_called()

    def test_detect_opportunities_empty_df(
        self, opportunity_detector: OpportunityDetector
    ) -> None:
        """Tests detect_opportunities with an empty DataFrame."""
        conn = MagicMock()
        df = pd.DataFrame()
        with patch("pandas.read_sql_query", return_value=df):
            opportunity_detector.update_contacts_db = MagicMock()
            opportunity_detector.detect_opportunities(conn)
            opportunity_detector.update_contacts_db.assert_not_called()

    def test_run(self, opportunity_detector: OpportunityDetector) -> None:
        """Tests the run method."""
        with patch(
            "dewey.core.crm.enrichment.opportunity_detection.get_db_connection"
        ) as mock_get_db_connection:
            mock_conn = MagicMock()
            mock_get_db_connection.return_value.__enter__.return_value = mock_conn
            opportunity_detector.detect_opportunities = MagicMock()
            opportunity_detector.run()
            opportunity_detector.detect_opportunities.assert_called_once_with(mock_conn)
        opportunity_detector.logger.info.assert_called()
