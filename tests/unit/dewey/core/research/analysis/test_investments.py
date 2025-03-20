import logging
from unittest.mock import MagicMock

import pytest

from dewey.core.research.analysis.investments import Investments


class TestInvestments:
    """
    Tests for the Investments class.
    """

    @pytest.fixture
    def investments(self) -> Investments:
        """
        Fixture to create an Investments instance.

        Returns:
            An instance of the Investments class.
        """
        return Investments()

    def test_init(self, investments: Investments) -> None:
        """
        Test the __init__ method of the Investments class.

        Checks that the config_section is set correctly.
        """
        assert investments.config_section == "investments"

    def test_run_no_db_no_llm(
        self, investments: Investments, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Test the run method with no database connection and no LLM client.

        Mocks the get_config_value method and checks that the log messages are correct.
        """
        caplog.set_level(logging.INFO)
        investments.get_config_value = MagicMock(return_value="test_api_key")
        investments.run()

        assert "Starting investment analysis..." in caplog.text
        assert "API Key: test_api_key" in caplog.text
        assert "Investment analysis completed." in caplog.text
        assert "Query Result:" not in caplog.text
        assert "LLM Response:" not in caplog.text

    def test_run_with_db_and_llm(
        self, investments: Investments, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Test the run method with a database connection and an LLM client.

        Mocks the get_config_value method, db_conn, and llm_client.
        Checks that the log messages are correct.
        """
        caplog.set_level(logging.INFO)
        investments.get_config_value = MagicMock(return_value="test_api_key")

        # Mock database connection
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value = "test_query_result"
        investments.db_conn = mock_db_conn

        # Mock LLM client
        mock_llm_client = MagicMock()
        mock_llm_client.generate.return_value = "test_llm_response"
        investments.llm_client = mock_llm_client

        investments.run()

        assert "Starting investment analysis..." in caplog.text
        assert "API Key: test_api_key" in caplog.text
        assert "Query Result: test_query_result" in caplog.text
        assert "LLM Response: test_llm_response" in caplog.text
        assert "Investment analysis completed." in caplog.text
        mock_db_conn.execute.assert_called_once()
        mock_llm_client.generate.assert_called_once()

    def test_run_db_error(
        self, investments: Investments, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Test the run method with a database error.

        Mocks the get_config_value method and db_conn to raise an exception.
        Checks that the error is logged correctly.
        """
        caplog.set_level(logging.ERROR)
        investments.get_config_value = MagicMock(return_value="test_api_key")

        # Mock database connection to raise an exception
        mock_db_conn = MagicMock()
        mock_db_conn.execute.side_effect = Exception("test_db_error")
        investments.db_conn = mock_db_conn

        # Mock LLM client
        mock_llm_client = MagicMock()
        investments.llm_client = mock_llm_client

        investments.run()

        assert "Error executing database query: test_db_error" in caplog.text
        mock_db_conn.execute.assert_called_once()
        mock_llm_client.generate.assert_not_called()

    def test_run_llm_error(
        self, investments: Investments, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Test the run method with an LLM error.

        Mocks the get_config_value method and llm_client to raise an exception.
        Checks that the error is logged correctly.
        """
        caplog.set_level(logging.ERROR)
        investments.get_config_value = MagicMock(return_value="test_api_key")

        # Mock database connection
        mock_db_conn = MagicMock()
        investments.db_conn = mock_db_conn

        # Mock LLM client to raise an exception
        mock_llm_client = MagicMock()
        mock_llm_client.generate.side_effect = Exception("test_llm_error")
        investments.llm_client = mock_llm_client

        investments.run()

        assert "Error calling LLM: test_llm_error" in caplog.text
        mock_db_conn.execute.assert_called_once()
        mock_llm_client.generate.assert_called_once()
