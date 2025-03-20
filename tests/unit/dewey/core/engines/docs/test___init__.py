import logging
from typing import Any
from unittest.mock import patch

import pytest

from dewey.core.engines.docs import DocsEngine


class TestDocsEngine:
    """Tests for the DocsEngine class."""

    @pytest.fixture
    def docs_engine(self) -> DocsEngine:
        """Fixture for creating a DocsEngine instance."""
        return DocsEngine()

    def test_init(self, docs_engine: DocsEngine) -> None:
        """Tests the __init__ method of DocsEngine."""
        assert docs_engine.name == "DocsEngine"
        assert docs_engine.config_section == "docs_engine"
        assert docs_engine.logger is not None

    @patch("dewey.core.engines.docs.DocsEngine.get_config_value")
    def test_run(
        self,
        mock_get_config_value: Any,
        docs_engine: DocsEngine,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the run method of DocsEngine."""
        mock_get_config_value.return_value = "test_value"
        with caplog.at_level(logging.DEBUG):
            docs_engine.run()
        assert "Running DocsEngine module." in caplog.text
        assert "Example config value: test_value" in caplog.text
        mock_get_config_value.assert_called_once_with(
            "example_config_key", "default_value"
        )

    def test_get_config_value(self, docs_engine: DocsEngine) -> None:
        """Tests the get_config_value method of DocsEngine."""
        # Mock the config attribute to avoid loading the actual config file
        docs_engine.config = {"test_key": "test_value"}
        value = docs_engine.get_config_value("test_key")
        assert value == "test_value"

        # Test with a default value
        value = docs_engine.get_config_value("nonexistent_key", "default_value")
        assert value == "default_value"

        # Test when the key is not found and no default is provided
        value = docs_engine.get_config_value("nonexistent_key")
        assert value is None

        # Test nested key
        docs_engine.config = {"nested": {"test_key": "nested_value"}}
        value = docs_engine.get_config_value("nested.test_key")
        assert value == "nested_value"

        # Test nested key with default
        value = docs_engine.get_config_value("nested.nonexistent_key", "default_value")
        assert value == "default_value"

    def test_get_config_value_empty_config(self, docs_engine: DocsEngine) -> None:
        """Tests get_config_value when the config is empty."""
        docs_engine.config = {}
        value = docs_engine.get_config_value("test_key", "default_value")
        assert value == "default_value"

        value = docs_engine.get_config_value("test_key")
        assert value is None

    def test_get_config_value_invalid_key(self, docs_engine: DocsEngine) -> None:
        """Tests get_config_value with an invalid key."""
        docs_engine.config = {"test_key": "test_value"}
        value = docs_engine.get_config_value(123, "default_value")  # type: ignore[arg-type]
        assert value == "default_value"
