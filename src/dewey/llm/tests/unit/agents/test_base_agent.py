"""Unit tests for the BaseAgent class."""

from unittest.mock import MagicMock, patch

import pytest

from dewey.llm.agents.base_agent import BaseAgent


class TestBaseAgent:
    """Tests for the BaseAgent class."""

    @pytest.fixture
    def mock_base_agent(self) -> BaseAgent:
        """Create a BaseAgent instance with mocked BaseScript initialization."""
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            agent = BaseAgent(
                name="TestAgent",
                description="A test agent",
                config_section="test_agent",
                requires_db=False,
                enable_llm=True,
            )
            agent.logger = MagicMock()
            agent.get_config_value = MagicMock(return_value="test_value")
            return agent

    def test_initialization(self) -> None:
        """Test that BaseAgent initializes correctly."""
        # Arrange & Act
        with patch(
            "dewey.core.base_script.BaseScript.__init__", return_value=None
        ) as mock_init:
            agent = BaseAgent(
                name="TestAgent",
                description="A test agent",
                config_section="test_agent",
                requires_db=True,
                enable_llm=True,
            )

            # Assert
            mock_init.assert_called_once()
            assert isinstance(agent, BaseAgent)
            assert agent.authorized_imports == []

    def test_with_custom_attributes(self) -> None:
        """Test that BaseAgent can be initialized with custom attributes."""
        # Arrange & Act
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            agent = BaseAgent(
                name="CustomAgent",
                description="A custom agent",
                config_section="custom_agent",
                requires_db=True,
                enable_llm=True,
                disable_rate_limit=True,
                custom_attr="custom_value",
            )

            # Assert
            assert isinstance(agent, BaseAgent)

    def test_logger_access(self, mock_base_agent) -> None:
        """Test accessing the logger from BaseScript."""
        # Act
        mock_base_agent.logger.info("Test message")

        # Assert
        mock_base_agent.logger.info.assert_called_once_with("Test message")

    def test_get_config_value_access(self, mock_base_agent) -> None:
        """Test accessing config values from BaseScript."""
        # Act
        result = mock_base_agent.get_config_value("test_key")

        # Assert
        assert result == "test_value"
        mock_base_agent.get_config_value.assert_called_once_with("test_key")
