import logging
from unittest.mock import patch

import pytest

from dewey.core.bookkeeping.mercury_importer import MercuryImporter


class TestMercuryImporter:
    """Test suite for the MercuryImporter class."""

    @pytest.fixture
    def mercury_importer(self) -> MercuryImporter:
        """Fixture to create a MercuryImporter instance."""
        return MercuryImporter()

    def test_initialization(self, mercury_importer: MercuryImporter) -> None:
        """Test that the MercuryImporter is initialized correctly."""
        assert mercury_importer.name == "MercuryImporter"
        assert mercury_importer.config_section == "mercury"
        assert mercury_importer.logger is not None

    @patch("dewey.core.bookkeeping.mercury_importer.MercuryImporter.get_config_value")
    def test_run_api_key_found(
        self,
        mock_get_config_value: pytest.fixture,
        mercury_importer: MercuryImporter,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method when the Mercury API key is found in the configuration."""
        mock_get_config_value.return_value = "test_api_key"
        with caplog.at_level(logging.INFO):
            mercury_importer.run()
        assert "Running Mercury importer" in caplog.text
        assert "Mercury API key found." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")

    @patch("dewey.core.bookkeeping.mercury_importer.MercuryImporter.get_config_value")
    def test_run_api_key_not_found(
        self,
        mock_get_config_value: pytest.fixture,
        mercury_importer: MercuryImporter,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method when the Mercury API key is not found in the configuration."""
        mock_get_config_value.return_value = None
        with caplog.at_level(logging.WARNING):
            mercury_importer.run()
        assert "Running Mercury importer" in caplog.text
        assert "Mercury API key not found in configuration." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")

    def test_get_config_value_existing_key(
        self, mercury_importer: MercuryImporter
    ) -> None:
        """Test that get_config_value returns the correct value for an existing key."""
        mercury_importer.config = {"test_key": "test_value"}
        assert mercury_importer.get_config_value("test_key") == "test_value"

    def test_get_config_value_nested_key(
        self, mercury_importer: MercuryImporter
    ) -> None:
        """Test that get_config_value returns the correct value for a nested key."""
        mercury_importer.config = {"nested": {"test_key": "test_value"}}
        assert mercury_importer.get_config_value("nested.test_key") == "test_value"

    def test_get_config_value_default_value(
        self, mercury_importer: MercuryImporter
    ) -> None:
        """Test that get_config_value returns the default value for a non-existing key."""
        mercury_importer.config = {}
        assert (
            mercury_importer.get_config_value("non_existing_key", "default_value")
            == "default_value"
        )

    def test_get_config_value_non_existing_key(
        self, mercury_importer: MercuryImporter
    ) -> None:
        """Test that get_config_value returns None for a non-existing key when no default is provided."""
        mercury_importer.config = {}
        assert mercury_importer.get_config_value("non_existing_key") is None
