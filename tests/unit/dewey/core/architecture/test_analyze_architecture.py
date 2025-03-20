import logging
from unittest.mock import patch

import pytest

from dewey.core.architecture.analyze_architecture import AnalyzeArchitecture


class TestAnalyzeArchitecture:
    """Unit tests for the AnalyzeArchitecture class."""

    @pytest.fixture
    def analyzer(self) -> AnalyzeArchitecture:
        """Fixture to create an instance of AnalyzeArchitecture."""
        return AnalyzeArchitecture()

    def test_init(self, analyzer: AnalyzeArchitecture) -> None:
        """Test the initialization of the AnalyzeArchitecture class."""
        assert analyzer.name == "AnalyzeArchitecture"
        assert analyzer.description is None
        assert analyzer.config_section == "analyze_architecture"
        assert analyzer.logger is not None

    @patch("dewey.core.architecture.analyze_architecture.AnalyzeArchitecture.get_config_value")
    @patch("dewey.core.architecture.analyze_architecture.AnalyzeArchitecture.logger")
    def test_run(
        self, mock_logger: logging.Logger, mock_get_config_value: Any, analyzer: AnalyzeArchitecture
    ) -> None:
        """Test the run method of the AnalyzeArchitecture class."""
        mock_get_config_value.return_value = "test_value"
        analyzer.run()

        mock_logger.info.assert_called()
        assert "Starting architecture analysis..." in str(mock_logger.info.call_args_list[0])
        assert "Example config value: test_value" in str(mock_logger.info.call_args_list[1])
        assert "Architecture analysis completed." in str(mock_logger.info.call_args_list[2])
        mock_get_config_value.assert_called_with("example_config", default="default_value")

    @patch("dewey.core.architecture.analyze_architecture.AnalyzeArchitecture.execute")
    def test_main(self, mock_execute: Any) -> None:
        """Test the main execution block of the AnalyzeArchitecture class."""
        with patch(
            "dewey.core.architecture.analyze_architecture.AnalyzeArchitecture", autospec=True
        ) as MockAnalyzer:
            # Simulate running the script directly
import dewey.core.architecture.analyze_architecture

            dewey.core.architecture.analyze_architecture.main()  # type: ignore

            # Assert that AnalyzeArchitecture was instantiated and execute was called
            MockAnalyzer.assert_called_once()
            mock_execute.assert_called_once()
