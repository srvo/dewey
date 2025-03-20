import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.sec_etl import SecEtl


class TestSecEtl:
    """Unit tests for the SecEtl class."""

    @pytest.fixture
    def sec_etl(self) -> SecEtl:
        """Fixture to create a SecEtl instance."""
        return SecEtl()

    def test_init(self, sec_etl: SecEtl) -> None:
        """Test the __init__ method."""
        assert sec_etl.name == "SecEtl"
        assert sec_etl.config_section == "sec_etl"
        assert sec_etl.logger is not None

    @patch("dewey.core.engines.sec_etl.SecEtl.get_config_value")
    def test_run(self, mock_get_config_value: pytest.fixture, sec_etl: SecEtl, caplog: pytest.fixture) -> None:
        """Test the run method."""
        mock_get_config_value.return_value = "test_value"
        caplog.set_level(logging.INFO)

        sec_etl.run()

        assert "Starting SEC ETL process." in caplog.text
        assert "Some config value: test_value" in caplog.text
        assert "SEC ETL process completed." in caplog.text
        mock_get_config_value.assert_called_with("some_config_key", "default_value")

    @patch("dewey.core.engines.sec_etl.SecEtl.get_config_value")
    def test_run_config_value_none(self, mock_get_config_value: pytest.fixture, sec_etl: SecEtl, caplog: pytest.fixture) -> None:
        """Test the run method when config value is None."""
        mock_get_config_value.return_value = None
        caplog.set_level(logging.INFO)

        sec_etl.run()

        assert "Starting SEC ETL process." in caplog.text
        assert "Some config value: None" in caplog.text
        assert "SEC ETL process completed." in caplog.text
        mock_get_config_value.assert_called_with("some_config_key", "default_value")
