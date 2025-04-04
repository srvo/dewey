"""Unit tests for the ToolFactory class."""

from unittest.mock import MagicMock, patch

import pytest

from dewey.llm.tools.tool_factory import ToolFactory


class TestToolFactory:
    """Test suite for the ToolFactory class."""

    @pytest.fixture()
    def mock_config(self) -> dict:
        """Fixture for a mock configuration."""
        return {
            "tool_name": "TestTool",
            "description": "A test tool",
            "parameters": {"param1": "value1", "param2": "value2"},
        }

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_initialization(self, mock_init, mock_config) -> None:
        """Test that ToolFactory initializes correctly."""
        # Arrange
        factory = ToolFactory(config=mock_config)

        # Assert
        mock_init.assert_called_once()
        assert isinstance(factory, ToolFactory)

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_run_method(self, mock_init, mock_config) -> None:
        """Test that the run method executes without errors."""
        # Arrange
        factory = ToolFactory(config=mock_config)
        factory.logger = MagicMock()
        factory.get_config_value = MagicMock(return_value="TestTool")

        # Act
        factory.run()

        # Assert
        factory.logger.info.assert_called()
        factory.get_config_value.assert_called_with("tool_name", default="DefaultTool")
