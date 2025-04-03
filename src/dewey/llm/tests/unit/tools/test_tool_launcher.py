"""Unit tests for the ToolLauncher class."""

from unittest.mock import MagicMock, patch

import pytest

from dewey.llm.tools.tool_launcher import ToolLauncher


class TestToolLauncher:
    """Test suite for the ToolLauncher class."""

    @pytest.fixture
    def launcher(self) -> ToolLauncher:
        """Fixture for a pre-configured ToolLauncher instance."""
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            launcher = ToolLauncher(config_section="test_launcher")
            # Mock the logger and get_config_value to avoid actual functionality
            launcher.logger = MagicMock()
            launcher.get_config_value = MagicMock(return_value="test_value")
            launcher._execute_tool = MagicMock(return_value={"status": "success"})
            return launcher

    def test_run_successful(self, launcher) -> None:
        """Test successful tool execution."""
        # Arrange
        tool_name = "test_tool"
        input_data = {"param1": "value1"}

        # Act
        result = launcher.run(tool_name, input_data)

        # Assert
        assert result == {"status": "success"}
        launcher.logger.info.assert_called()
        launcher._execute_tool.assert_called_once_with(tool_name, input_data)

    def test_run_with_value_error(self, launcher) -> None:
        """Test handling of ValueError during tool execution."""
        # Arrange
        tool_name = "invalid_tool"
        input_data = {"param1": "value1"}
        launcher._execute_tool.side_effect = ValueError("Invalid tool")

        # Act/Assert
        with pytest.raises(ValueError) as exc_info:
            launcher.run(tool_name, input_data)

        assert "Invalid tool" in str(exc_info.value)
        launcher.logger.error.assert_called()

    def test_run_with_exception(self, launcher) -> None:
        """Test handling of generic exceptions during tool execution."""
        # Arrange
        tool_name = "error_tool"
        input_data = {"param1": "value1"}
        launcher._execute_tool.side_effect = Exception("Tool execution failed")

        # Act/Assert
        with pytest.raises(Exception) as exc_info:
            launcher.run(tool_name, input_data)

        assert "Tool execution failed" in str(exc_info.value)
        launcher.logger.exception.assert_called()
