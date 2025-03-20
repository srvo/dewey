import logging
from unittest.mock import patch

import pytest

from dewey.core.maintenance.precommit_analyzer import PrecommitAnalyzer


class TestPrecommitAnalyzer:
    """Unit tests for the PrecommitAnalyzer class."""

    @pytest.fixture
    def precommit_analyzer(self) -> PrecommitAnalyzer:
        """Fixture to create a PrecommitAnalyzer instance."""
        return PrecommitAnalyzer()

    def test_init(self, precommit_analyzer: PrecommitAnalyzer) -> None:
        """Test the initialization of the PrecommitAnalyzer."""
        assert precommit_analyzer.name == "PrecommitAnalyzer"
        assert precommit_analyzer.config_section == "precommit_analyzer"
        assert precommit_analyzer.logger is not None

    @patch(
        "dewey.core.maintenance.precommit_analyzer.PrecommitAnalyzer.get_config_value"
    )
    def test_run(
        self, mock_get_config_value, precommit_analyzer: PrecommitAnalyzer, caplog
    ) -> None:
        """Test the run method of the PrecommitAnalyzer."""
        mock_get_config_value.return_value = "test_value"
        with caplog.at_level(logging.INFO):
            precommit_analyzer.run()
        assert "Starting pre-commit analysis..." in caplog.text
        assert "Config value: test_value" in caplog.text
        assert "Pre-commit analysis completed." in caplog.text
        mock_get_config_value.assert_called_with("some_config_key", "default_value")

    @patch(
        "dewey.core.maintenance.precommit_analyzer.PrecommitAnalyzer.get_config_value"
    )
    def test_run_config_value_override(
        self, mock_get_config_value, precommit_analyzer: PrecommitAnalyzer, caplog
    ) -> None:
        """Test that the config value is correctly retrieved and logged."""
        mock_get_config_value.return_value = "override_value"
        with caplog.at_level(logging.INFO):
            precommit_analyzer.run()
        assert "Config value: override_value" in caplog.text

    def test_get_config_value_existing_key(
        self, precommit_analyzer: PrecommitAnalyzer
    ) -> None:
        """Test getting an existing config value."""
        precommit_analyzer.config = {"section": {"key": "value"}}
        value = precommit_analyzer.get_config_value("section.key")
        assert value == "value"

    def test_get_config_value_default_value(
        self, precommit_analyzer: PrecommitAnalyzer
    ) -> None:
        """Test getting a non-existing config value with a default."""
        precommit_analyzer.config = {"section": {}}
        value = precommit_analyzer.get_config_value(
            "section.non_existent_key", "default"
        )
        assert value == "default"

    def test_get_config_value_nested_key(
        self, precommit_analyzer: PrecommitAnalyzer
    ) -> None:
        """Test getting a nested config value."""
        precommit_analyzer.config = {"level1": {"level2": {"level3": "nested_value"}}}
        value = precommit_analyzer.get_config_value("level1.level2.level3")
        assert value == "nested_value"

    def test_get_config_value_missing_section(
        self, precommit_analyzer: PrecommitAnalyzer
    ) -> None:
        """Test getting a config value from a missing section."""
        precommit_analyzer.config = {"existing_section": {"key": "value"}}
        value = precommit_analyzer.get_config_value("missing_section.key", "default")
        assert value == "default"

    def test_get_config_value_no_default(
        self, precommit_analyzer: PrecommitAnalyzer
    ) -> None:
        """Test getting a non-existing config value without a default."""
        precommit_analyzer.config = {"section": {}}
        value = precommit_analyzer.get_config_value("section.non_existent_key")
        assert value is None
