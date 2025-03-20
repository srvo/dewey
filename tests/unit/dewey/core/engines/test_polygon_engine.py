import pytest
from unittest.mock import patch, MagicMock
from dewey.core.engines.polygon_engine import PolygonEngine
import logging


class TestPolygonEngine:
    """
    Unit tests for the PolygonEngine class.
    """

    @pytest.fixture
    def polygon_engine(self) -> PolygonEngine:
        """
        Pytest fixture to create an instance of PolygonEngine with a mock config section.
        """
        with patch(
            "dewey.core.engines.polygon_engine.BaseScript.__init__", return_value=None
        ):
            engine = PolygonEngine(config_section="test_polygon_engine")
            engine.logger = MagicMock(spec=logging.Logger)  # Mock the logger
            engine.config = {
                "api_key": "test_api_key",
                "core": {"database": {}},
                "llm": {},
            }  # Mock the config
            return engine

    @patch("dewey.core.engines.polygon_engine.get_motherduck_connection")
    @patch("dewey.core.engines.polygon_engine.create_table")
    @patch("dewey.core.engines.polygon_engine.execute_query")
    @patch("dewey.core.engines.polygon_engine.call_llm")
    def test_run_success(
        self,
        mock_call_llm: MagicMock,
        mock_execute_query: MagicMock,
        mock_create_table: MagicMock,
        mock_get_motherduck_connection: MagicMock,
        polygon_engine: PolygonEngine,
    ) -> None:
        """
        Test the successful execution of the run method.
        """
        mock_conn = MagicMock()
        mock_get_motherduck_connection.return_value.__enter__.return_value = mock_conn
        mock_call_llm.return_value = "AAPL market summary"

        polygon_engine.run()

        polygon_engine.logger.info.assert_called()
        mock_get_motherduck_connection.assert_called_once()
        mock_create_table.assert_called_once()
        mock_execute_query.assert_called_once()
        mock_call_llm.assert_called_once()

    @patch("dewey.core.engines.polygon_engine.get_motherduck_connection")
    def test_run_db_error(
        self, mock_get_motherduck_connection: MagicMock, polygon_engine: PolygonEngine
    ) -> None:
        """
        Test the run method handles database connection errors.
        """
        mock_get_motherduck_connection.side_effect = Exception(
            "Database connection failed"
        )

        polygon_engine.run()

        polygon_engine.logger.error.assert_called()
        assert "Error interacting with the database" in str(
            polygon_engine.logger.error.call_args
        )

    @patch("dewey.core.engines.polygon_engine.call_llm")
    @patch("dewey.core.engines.polygon_engine.get_motherduck_connection")
    def test_run_llm_error(
        self,
        mock_get_motherduck_connection: MagicMock,
        mock_call_llm: MagicMock,
        polygon_engine: PolygonEngine,
    ) -> None:
        """
        Test the run method handles LLM interaction errors.
        """
        mock_conn = MagicMock()
        mock_get_motherduck_connection.return_value.__enter__.return_value = mock_conn
        mock_call_llm.side_effect = Exception("LLM call failed")

        polygon_engine.run()

        polygon_engine.logger.error.assert_called()
        assert "Error interacting with the LLM" in str(
            polygon_engine.logger.error.call_args
        )

    def test_init(self) -> None:
        """
        Test the initialization of the PolygonEngine class.
        """
        with patch(
            "dewey.core.engines.polygon_engine.BaseScript.__init__"
        ) as mock_base_init:
            engine = PolygonEngine(config_section="test_polygon_engine")
            mock_base_init.assert_called_once_with(config_section="test_polygon_engine")

    def test_run_no_api_key(self, polygon_engine: PolygonEngine) -> None:
        """
        Test the run method handles missing API key.
        """
        polygon_engine.config["api_key"] = None

        polygon_engine.run()

        polygon_engine.logger.error.assert_called_with(
            "Polygon API key not found in configuration."
        )

    @patch("dewey.core.engines.polygon_engine.get_motherduck_connection")
    @patch("dewey.core.engines.polygon_engine.create_table")
    @patch("dewey.core.engines.polygon_engine.execute_query")
    @patch("dewey.core.engines.polygon_engine.call_llm")
    def test_run_empty_data(
        self,
        mock_call_llm: MagicMock,
        mock_execute_query: MagicMock,
        mock_create_table: MagicMock,
        mock_get_motherduck_connection: MagicMock,
        polygon_engine: PolygonEngine,
    ) -> None:
        """
        Test the successful execution of the run method with empty data.
        """
        mock_conn = MagicMock()
        mock_get_motherduck_connection.return_value.__enter__.return_value = mock_conn
        mock_call_llm.return_value = ""

        polygon_engine.run()

        polygon_engine.logger.info.assert_called()
        mock_get_motherduck_connection.assert_called_once()
        mock_create_table.assert_called_once()
        mock_execute_query.assert_called_once()
        mock_call_llm.assert_called_once()
