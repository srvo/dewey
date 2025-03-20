from typing import Any
from unittest.mock import MagicMock

import pytest

from dewey.core.crm.enrichment.prioritization import Prioritization
from dewey.core.base_script import BaseScript


class TestPrioritization:
    """Unit tests for the Prioritization class."""

    @pytest.fixture
    def prioritization(self) -> Prioritization:
        """Fixture to create a Prioritization instance with mocked dependencies."""
        prioritization = Prioritization()
        prioritization.logger = MagicMock()
        prioritization.config = {"some_config_key": "test_value"}
        return prioritization

    def test_init(self, prioritization: Prioritization) -> None:
        """Test the __init__ method of Prioritization."""
        assert prioritization.name == "Prioritization"
        assert prioritization.description == "Handles prioritization of CRM enrichment tasks."
        assert prioritization.config_section == "prioritization"

    def test_run_success(self, prioritization: Prioritization) -> None:
        """Test the run method with successful execution."""
        prioritization.get_config_value = MagicMock(return_value="test_value")
        prioritization.run()

        prioritization.logger.info.assert_called_with("Prioritization process completed.")
        prioritization.logger.debug.assert_called_with("Some config value: test_value")

    def test_run_exception(self, prioritization: Prioritization) -> None:
        """Test the run method when an exception occurs."""
        prioritization.get_config_value = MagicMock(side_effect=Exception("Test exception"))

        with pytest.raises(Exception, match="Test exception"):
            prioritization.run()

        prioritization.logger.error.assert_called_once()

    def test_get_config_value_exists(self, prioritization: Prioritization) -> None:
        """Test get_config_value when the key exists in the config."""
        value = prioritization.get_config_value("some_config_key")
        assert value == "test_value"

    def test_get_config_value_default(self, prioritization: Prioritization) -> None:
        """Test get_config_value when the key does not exist and a default is provided."""
        value = prioritization.get_config_value("non_existent_key", "default_value")
        assert value == "default_value"

    def test_get_config_value_none_default(self, prioritization: Prioritization) -> None:
        """Test get_config_value when the key does not exist and no default is provided."""
        prioritization.config = {}
        value = prioritization.get_config_value("non_existent_key")
        assert value is None

    def test_inheritance_from_basescript(self, prioritization: Prioritization) -> None:
        """Test that Prioritization inherits from BaseScript."""
        assert isinstance(prioritization, BaseScript)

    def test_config_section_default(self) -> None:
        """Test that the default config section is 'prioritization'."""
        prioritization = Prioritization()
        assert prioritization.config_section == "prioritization"

    def test_logger_usage(self, prioritization: Prioritization) -> None:
        """Test that the logger is used correctly."""
        prioritization.run()
        assert prioritization.logger.info.call_count > 0
        assert prioritization.logger.debug.call_count > 0
