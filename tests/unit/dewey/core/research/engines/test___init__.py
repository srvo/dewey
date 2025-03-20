import logging
from unittest.mock import patch

import pytest
from dewey.core.research.engines import ResearchEngines


class TestResearchEngines:
    """Tests for the ResearchEngines class."""

    @pytest.fixture
    def research_engines(self) -> ResearchEngines:
        """Fixture for creating a ResearchEngines instance."""
        return ResearchEngines()

    def test_init_default(self, research_engines: ResearchEngines) -> None:
        """Test the __init__ method with default values."""
        assert research_engines.name == "ResearchEngines"
        assert research_engines.description is None
        assert research_engines.config_section is None
        assert not research_engines.requires_db
        assert not research_engines.enable_llm
        assert research_engines.logger is not None
        assert research_engines.config is not None
        assert research_engines.db_conn is None
        assert research_engines.llm_client is None

    def test_init_custom(self) -> None:
        """Test the __init__ method with custom values."""
        engine = ResearchEngines(
            name="CustomEngine",
            description="A custom engine",
            config_section="custom_section",
            requires_db=True,
            enable_llm=True,
        )
        assert engine.name == "CustomEngine"
        assert engine.description == "A custom engine"
        assert engine.config_section == "custom_section"
        assert engine.requires_db
        assert engine.enable_llm
        assert engine.logger is not None
        assert engine.config is not None
        assert engine.db_conn is None  # Will be initialized later
        assert engine.llm_client is None  # Will be initialized later

    @patch("dewey.core.research.engines.ResearchEngines.get_config_value")
    def test_run_success(
        self, mock_get_config_value: pytest.fixture, research_engines: ResearchEngines
    ) -> None:
        """Test the run method with successful execution."""
        mock_get_config_value.return_value = "TestEngine"
        with patch.object(research_engines.logger, "info") as mock_logger_info:
            research_engines.run()
            mock_logger_info.assert_called_with("Engine name: TestEngine")
        mock_get_config_value.assert_called_with("engine_name", "DefaultEngine")

    @patch("dewey.core.research.engines.ResearchEngines.get_config_value")
    def test_run_config_error(
        self, mock_get_config_value: pytest.fixture, research_engines: ResearchEngines
    ) -> None:
        """Test the run method when there's an error retrieving config value."""
        mock_get_config_value.side_effect = ValueError("Config error")
        with pytest.raises(ValueError, match="Config error"):
            with patch.object(research_engines.logger, "error") as mock_logger_error:
                research_engines.run()
                mock_logger_error.assert_called()
        mock_get_config_value.assert_called_with("engine_name", "DefaultEngine")

    @patch("dewey.core.research.engines.ResearchEngines.get_config_value")
    def test_run_exception_handling(
        self, mock_get_config_value: pytest.fixture, research_engines: ResearchEngines
    ) -> None:
        """Test that exceptions during run are caught and re-raised."""
        mock_get_config_value.side_effect = Exception("Something went wrong")

        with pytest.raises(Exception, match="Something went wrong"):
            research_engines.run()

    def test_logging_setup(self, research_engines: ResearchEngines, caplog: pytest.LogCaptureFixture) -> None:
        """Test that logging is set up correctly."""
        with caplog.at_level(logging.INFO):
            research_engines.logger.info("Test log message")
            assert "Test log message" in caplog.text
