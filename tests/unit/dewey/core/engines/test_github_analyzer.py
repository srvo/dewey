import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.github_analyzer import GithubAnalyzer


class TestGithubAnalyzer:
    """Tests for the GithubAnalyzer class."""

    @pytest.fixture
    def github_analyzer(self):
        """Fixture for creating a GithubAnalyzer instance."""
        return GithubAnalyzer()

    def test_initialization(self, github_analyzer: GithubAnalyzer):
        """Test that the GithubAnalyzer is initialized correctly."""
        assert github_analyzer.name == "GithubAnalyzer"
        assert github_analyzer.config_section == "github_analyzer"
        assert github_analyzer.logger is not None

    @patch("dewey.core.engines.github_analyzer.GithubAnalyzer.get_config_value")
    def test_run_success(
        self, mock_get_config_value, github_analyzer: GithubAnalyzer, caplog
    ):
        """Test the run method with a successful API key retrieval."""
        mock_get_config_value.return_value = "test_api_key"
        with caplog.record_tuples():
            caplog.set_level(logging.INFO)
            github_analyzer.run()
        assert (
            "GithubAnalyzer",
            logging.INFO,
            "Starting GitHub analysis...",
        ) in caplog.record_tuples()
        assert (
            "GithubAnalyzer",
            logging.INFO,
            "Retrieved API key: test_api_key",
        ) in caplog.record_tuples()
        assert (
            "GithubAnalyzer",
            logging.INFO,
            "GitHub analysis completed.",
        ) in caplog.record_tuples()
        mock_get_config_value.assert_called_once_with("github_api_key")

    @patch("dewey.core.engines.github_analyzer.GithubAnalyzer.get_config_value")
    def test_run_no_api_key(
        self, mock_get_config_value, github_analyzer: GithubAnalyzer, caplog
    ):
        """Test the run method when no API key is found in the config."""
        mock_get_config_value.return_value = None
        with caplog.record_tuples():
            caplog.set_level(logging.INFO)
            github_analyzer.run()
        assert (
            "GithubAnalyzer",
            logging.INFO,
            "Starting GitHub analysis...",
        ) in caplog.record_tuples()
        assert (
            "GithubAnalyzer",
            logging.INFO,
            "Retrieved API key: None",
        ) in caplog.record_tuples()
        assert (
            "GithubAnalyzer",
            logging.INFO,
            "GitHub analysis completed.",
        ) in caplog.record_tuples()
        mock_get_config_value.assert_called_once_with("github_api_key")

    # Add more tests here to cover other aspects of the GithubAnalyzer class
    # such as error handling, different configuration scenarios, etc.
