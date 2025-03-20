import pytest
from unittest.mock import patch, MagicMock
from dewey.core.utils.format_and_lint import FormatAndLint
import logging
from typing import Any, Dict

class TestFormatAndLint:
    """
    Unit tests for the FormatAndLint class.
    """

    @pytest.fixture
    def format_and_lint(self) -> FormatAndLint:
        """
        Fixture to create an instance of FormatAndLint with a mock configuration.
        """
        with patch('dewey.core.utils.format_and_lint.FormatAndLint.get_config_value') as mock_get_config_value:
            mock_get_config_value.return_value = 'default_value'
            return FormatAndLint()

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """
        Fixture to create a mock logger.
        """
        return MagicMock(spec=logging.Logger)

    def test_init(self) -> None:
        """
        Test the __init__ method of FormatAndLint.
        """
        format_and_lint = FormatAndLint()
        assert format_and_lint.config_section == 'format_and_lint'

    def test_run(self, format_and_lint: FormatAndLint, mock_logger: MagicMock) -> None:
        """
        Test the run method of FormatAndLint.
        """
        format_and_lint.logger = mock_logger
        with patch.object(format_and_lint, 'get_config_value', return_value='test_value') as mock_get_config_value:
            format_and_lint.run()

            mock_logger.info.assert_called()
            calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert "Starting formatting and linting process." in calls
            assert "Example config value: test_value" in calls
            assert "Formatting and linting process completed." in calls
            mock_get_config_value.assert_called_with('some_config_key', 'default_value')

    def test_get_config_value(self, format_and_lint: FormatAndLint) -> None:
        """
        Test the get_config_value method of BaseScript.
        """
        # Mock the config attribute
        format_and_lint.config = {"level1": {"level2": "value"}}

        # Test existing key
        value = format_and_lint.get_config_value("level1.level2")
        assert value == "value"

        # Test non-existing key with default value
        value = format_and_lint.get_config_value("level1.level3", "default")
        assert value == "default"

        # Test non-existing key without default value
        value = format_and_lint.get_config_value("level1.level3")
        assert value is None

        # Test accessing a non-dict level
        format_and_lint.config = {"level1": "not_a_dict"}
        value = format_and_lint.get_config_value("level1.level2", "default")
        assert value == "default"

        # Test accessing a non-dict level without default
        format_and_lint.config = {"level1": "not_a_dict"}
        value = format_and_lint.get_config_value("level1.level2")
        assert value is None

        # Test empty key
        format_and_lint.config = {"level1": "value"}
        value = format_and_lint.get_config_value("")
        assert value is None

        # Test key with empty part
        format_and_lint.config = {"level1": {"": "value"}}
        value = format_and_lint.get_config_value("level1.")
        assert value is None

        # Test key with multiple parts
        format_and_lint.config = {"level1": {"level2": {"level3": "value"}}}
        value = format_and_lint.get_config_value("level1.level2.level3")
        assert value == "value"

        # Test default value when config is empty
        format_and_lint.config = {}
        value = format_and_lint.get_config_value("level1.level2", "default")
        assert value == "default"
