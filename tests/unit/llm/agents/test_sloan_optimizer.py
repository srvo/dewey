import pytest
from unittest.mock import MagicMock
from dewey.llm.agents.sloane_optimizer import SloanOptimizer


class TestSloanOptimizer:
    """Class TestSloanOptimizer."""

    @pytest.fixture
    def optimizer(self):
        """Fixture providing an initialized SloanOptimizer instance."""
        return SloanOptimizer()

    def test_analyze_current_state_happy_path(self, optimizer, monkeypatch):
        """Test analyze_current_state returns expected string when run succeeds."""
        mock_response = "Sample analysis and recommendations."
        mock_run = MagicMock(return_value=mock_response)
        monkeypatch.setattr(optimizer, "run", mock_run)

        result = optimizer.analyze_current_state()

        assert isinstance(result, str)
        assert result == mock_response
        mock_run.assert_called_once_with(
            "Analyze current state and provide optimization recommendations"
        )

    def test_analyze_current_state_error(self, optimizer, monkeypatch):
        """Test analyze_current_state raises exception when run fails."""
        mock_run = MagicMock(side_effect=Exception("API error"))
        monkeypatch.setattr(optimizer, "run", mock_run)

        with pytest.raises(Exception, match="API error"):
            optimizer.analyze_current_state()

    def test_optimize_tasks_happy_path(self, optimizer, monkeypatch):
        """Test optimize_tasks returns list of dicts with valid inputs."""
        tasks = [{"task": "Test task"}]
        priorities = [{"priority": "High"}]
        mock_response = [{"optimized": True}]
        mock_run = MagicMock(return_value=mock_response)
        monkeypatch.setattr(optimizer, "run", mock_run)

        result = optimizer.optimize_tasks(tasks, priorities)

        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)
        mock_run.assert_called_once_with(
            f"Optimize these tasks based on strategic priorities:\nTasks: {tasks}\nPriorities: {priorities}"
        )

    def test_optimize_tasks_empty_inputs(self, optimizer, monkeypatch):
        """Test optimize_tasks handles empty tasks/priorities."""
        tasks = []
        priorities = []
        mock_response = []
        mock_run = MagicMock(return_value=mock_response)
        monkeypatch.setattr(optimizer, "run", mock_run)

        result = optimizer.optimize_tasks(tasks, priorities)

        assert isinstance(result, list)
        assert len(result) == 0
        mock_run.assert_called_once_with(
            f"Optimize these tasks based on strategic priorities:\nTasks: {tasks}\nPriorities: {priorities}"
        )

    def test_suggest_breaks_happy_path(self, optimizer, monkeypatch):
        """Test suggest_breaks returns list of strings."""
        mock_response = ["Take a 10-minute walk", "Stretch for 5 minutes"]
        mock_run = MagicMock(return_value=mock_response)
        monkeypatch.setattr(optimizer, "run", mock_run)

        result = optimizer.suggest_breaks()

        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)
        mock_run.assert_called_once_with("Suggest optimal break times and activities")

    def test_check_work_life_balance_happy_path(self, optimizer, monkeypatch):
        """Test check_work_life_balance returns dict with analysis."""
        mock_response = {"balance_score": 85, "recommendations": ["Take weekends off"]}
        mock_run = MagicMock(return_value=mock_response)
        monkeypatch.setattr(optimizer, "run", mock_run)

        result = optimizer.check_work_life_balance()

        assert isinstance(result, dict)
        assert "balance_score" in result
        mock_run.assert_called_once_with(
            "Analyze work-life balance and provide recommendations"
        )

    def test_check_work_life_balance_error(self, optimizer, monkeypatch):
        """Test check_work_life_balance raises exception on run failure."""
        mock_run = MagicMock(side_effect=Exception("API timeout"))
        monkeypatch.setattr(optimizer, "run", mock_run)

        with pytest.raises(Exception, match="API timeout"):
            optimizer.check_work_life_balance()
