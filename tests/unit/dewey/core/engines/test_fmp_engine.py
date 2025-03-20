from unittest.mock import MagicMock, patch
from typing import Any, Dict, Optional

import pytest

from dewey.core.engines.fmp_engine import FMPEngine
from dewey.core.base_script import BaseScript


class TestFMPEngine:
    """Tests for the FMPEngine class."""

    @pytest.fixture
    def fmp_engine(self) -> FMPEngine:
        """Fixture for creating an FMPEngine instance."""
        with patch('dewey.core.engines.fmp_engine.FMPEngine.get_config_value') as mock_get_config_value:
            mock_get_config_value.return_value = "test_api_key"
            engine = FMPEngine()
        return engine

    def test_init(self, fmp_engine: FMPEngine) -> None:
        """Test the __init__ method."""
        assert isinstance(fmp_engine, FMPEngine)
        assert isinstance(fmp_engine, BaseScript)
        assert fmp_engine.config_section == 'fmp_engine'

    def test_run_success(self, fmp_engine: FMPEngine, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method with a valid API key."""
        fmp_engine.run()
        assert "Starting FMP Engine..." in caplog.text
        assert "FMP API Key: test_api_key" in caplog.text
        assert "FMP Engine Finished." in caplog.text

    def test_run_no_api_key(self, fmp_engine: FMPEngine, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when the API key is missing."""
        with patch.object(fmp_engine, 'get_config_value', return_value=None):
            fmp_engine.run()
        assert "FMP API key not found in configuration." in caplog.text

    def test_get_data_success(self, fmp_engine: FMPEngine) -> None:
        """Test the get_data method with a successful API call."""
        mock_response = {"status": "success", "endpoint": "income-statement"}
        with patch.object(fmp_engine, 'get_config_value', return_value="test_api_key"):
            data = fmp_engine.get_data("income-statement")
        assert data == mock_response

    def test_get_data_no_api_key(self, fmp_engine: FMPEngine, caplog: pytest.LogCaptureFixture) -> None:
        """Test the get_data method when the API key is missing."""
        with patch.object(fmp_engine, 'get_config_value', return_value=None):
            data = fmp_engine.get_data("income-statement")
        assert "FMP API key not found in configuration." in caplog.text
        assert data is None

    def test_get_data_with_params(self, fmp_engine: FMPEngine) -> None:
        """Test the get_data method with parameters."""
        mock_response = {"status": "success", "endpoint": "balance-sheet"}
        with patch.object(fmp_engine, 'get_config_value', return_value="test_api_key"):
            data = fmp_engine.get_data("balance-sheet", params={"period": "annual"})
        assert data == mock_response

    def test_get_data_logs_endpoint(self, fmp_engine: FMPEngine, caplog: pytest.LogCaptureFixture) -> None:
        """Test that get_data logs the endpoint."""
        with patch.object(fmp_engine, 'get_config_value', return_value="test_api_key"):
            fmp_engine.get_data("cash-flow-statement")
        assert "Fetching data from FMP endpoint: cash-flow-statement" in caplog.text
