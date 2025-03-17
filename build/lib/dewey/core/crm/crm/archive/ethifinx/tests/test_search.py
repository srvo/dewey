import unittest
from unittest.mock import Mock, patch

import pytest

from ethifinx.research.search import AnalysisEngine, SearchEngine, SearchWorkflow


class TestSearchWorkflow(unittest.TestCase):
    """Test cases for SearchWorkflow."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.search_engine = Mock(spec=SearchEngine)
        self.analysis_engine = Mock(spec=AnalysisEngine)
        self.workflow = SearchWorkflow(
            search_engine=self.search_engine, analysis_engine=self.analysis_engine
        )

    def test_basic_search(self):
        """Test basic search functionality."""
        self.search_engine.search.return_value = ["result1", "result2"]
        results = self.workflow.search("test query")
        self.assertEqual(results, ["result1", "result2"])
        self.search_engine.search.assert_called_once_with("test query", filters=None)

    def test_search_with_analysis(self):
        """Test search with analysis."""
        self.search_engine.search.return_value = ["result1", "result2"]
        self.analysis_engine.analyze.return_value = {"analysis": "data"}

        results = self.workflow.search_and_analyze("test query")
        self.assertEqual(results, {"analysis": "data"})

        self.search_engine.search.assert_called_once_with("test query", filters=None)
        self.analysis_engine.analyze.assert_called_once_with(["result1", "result2"])

    def test_empty_search_results(self):
        """Test handling of empty search results."""
        self.search_engine.search.return_value = []
        results = self.workflow.search("test query")
        self.assertEqual(results, [])

    def test_analysis_error_handling(self):
        """Test error handling in analysis."""
        self.search_engine.search.return_value = ["result1"]
        self.analysis_engine.analyze.side_effect = Exception("Analysis failed")

        with self.assertRaises(Exception):
            self.workflow.search_and_analyze("test query")

    def test_search_with_filters(self):
        """Test search with filters."""
        filters = {"date": "2023", "category": "test"}
        self.search_engine.search.return_value = ["filtered_result"]

        results = self.workflow.search("test query", filters=filters)
        self.assertEqual(results, ["filtered_result"])
        self.search_engine.search.assert_called_once_with("test query", filters=filters)

    def test_batch_search(self):
        """Test batch search functionality."""
        queries = ["query1", "query2"]
        self.search_engine.batch_search.return_value = {
            "query1": ["result1"],
            "query2": ["result2"],
        }

        results = self.workflow.batch_search(queries)
        self.assertEqual(results, {"query1": ["result1"], "query2": ["result2"]})
        self.search_engine.batch_search.assert_called_once_with(queries)
