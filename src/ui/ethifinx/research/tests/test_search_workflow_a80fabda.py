from typing import Any
from unittest.mock import Mock

from ethifinx.research.search import AnalysisEngine, SearchEngine, SearchWorkflow


class TestSearchWorkflow(BaseScriptunittest.TestCase):
    """Test cases for SearchWorkflow."""

    def setUp(self) -> None:
        """Set up test environment."""
        super().setUp()
        self.search_engine: Mock = Mock(spec=SearchEngine)
        self.analysis_engine: Mock = Mock(spec=AnalysisEngine)
        self.workflow: SearchWorkflow = SearchWorkflow(
            search_engine=self.search_engine, analysis_engine=self.analysis_engine
        )

    def test_basic_search(self) -> None:
        """Test basic search functionality."""
        self.search_engine.search.return_value = ["result1", "result2"]
        results: list[str] = self.workflow.search("test query")
        self.assertEqual(results, ["result1", "result2"])
        self.search_engine.search.assert_called_once_with("test query", filters=None)

    def test_search_with_analysis(self) -> None:
        """Test search with analysis."""
        self.search_engine.search.return_value = ["result1", "result2"]
        self.analysis_engine.analyze.return_value = {"analysis": "data"}

        results: dict[str, str] = self.workflow.search_and_analyze("test query")
        self.assertEqual(results, {"analysis": "data"})

        self.search_engine.search.assert_called_once_with("test query", filters=None)
        self.analysis_engine.analyze.assert_called_once_with(["result1", "result2"])

    def test_empty_search_results(self) -> None:
        """Test handling of empty search results."""
        self.search_engine.search.return_value = []
        results: list[Any] = self.workflow.search("test query")
        self.assertEqual(results, [])

    def test_analysis_error_handling(self) -> None:
        """Test error handling in analysis."""
        self.search_engine.search.return_value = ["result1"]
        self.analysis_engine.analyze.side_effect = Exception("Analysis failed")

        with self.assertRaises(Exception):
            self.workflow.search_and_analyze("test query")

    def test_search_with_filters(self) -> None:
        """Test search with filters."""
        filters: dict[str, str] = {"date": "2023", "category": "test"}
        self.search_engine.search.return_value = ["filtered_result"]

        results: list[str] = self.workflow.search("test query", filters=filters)
        self.assertEqual(results, ["filtered_result"])
        self.search_engine.search.assert_called_once_with("test query", filters=filters)

    def test_batch_search(self) -> None:
        """Test batch search functionality."""
        queries: list[str] = ["query1", "query2"]
        self.search_engine.batch_search.return_value = {
            "query1": ["result1"],
            "query2": ["result2"],
        }

        results: dict[str, list[str]] = self.workflow.batch_search(queries)
        self.assertEqual(results, {"query1": ["result1"], "query2": ["result2"]})
        self.search_engine.batch_search.assert_called_once_with(queries)
