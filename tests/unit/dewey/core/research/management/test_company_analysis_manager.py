import unittest
from unittest.mock import MagicMock, patch
from typing import Any, Dict
import pytest

from dewey.core.research.management.company_analysis_manager import CompanyAnalysisManager
from dewey.core.base_script import BaseScript

class TestCompanyAnalysisManager(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.manager = CompanyAnalysisManager()
        self.manager.logger = MagicMock()
        self.manager.db_conn = MagicMock()
        self.manager.llm_client = MagicMock()
        self.manager.config = {
            "company_analysis": {
                "company_ticker": "TEST"
            },
            "core": {
                "database": {}
            },
            "llm": {}
        }
        self.test_ticker = "TEST"
        self.test_analysis_results = {"llm_analysis": "Test analysis"}

    def test_init(self):
        """Test the initialization of CompanyAnalysisManager."""
        manager = CompanyAnalysisManager()
        self.assertEqual(manager.name, "CompanyAnalysisManager")
        self.assertEqual(manager.description, "Manages company data analysis.")
        self.assertEqual(manager.config_section, "company_analysis")
        self.assertTrue(manager.requires_db)
        self.assertTrue(manager.enable_llm)

    def test_run_success(self):
        """Test successful execution of the company analysis process."""
        self.manager._analyze_company = MagicMock(return_value=self.test_analysis_results)
        self.manager._store_analysis_results = MagicMock()
        self.manager.get_config_value = MagicMock(return_value=self.test_ticker)

        self.manager.run()

        self.manager.logger.info.assert_called()
        self.manager._analyze_company.assert_called_with(self.test_ticker)
        self.manager._store_analysis_results.assert_called_with(self.test_ticker, self.test_analysis_results)

    def test_run_no_ticker(self):
        """Test run method when company ticker is not found in configuration."""
        self.manager.get_config_value = MagicMock(return_value=None)

        with self.assertRaises(ValueError) as context:
            self.manager.run()

        self.assertEqual(str(context.exception), "Company ticker not found in configuration.")
        self.manager.logger.error.assert_called()

    def test_run_analysis_error(self):
        """Test run method when an error occurs during company analysis."""
        self.manager.get_config_value = MagicMock(return_value=self.test_ticker)
        self.manager._analyze_company = MagicMock(side_effect=Exception("Analysis error"))

        with self.assertRaises(Exception) as context:
            self.manager.run()

        self.assertEqual(str(context.exception), "Analysis error")
        self.manager.logger.error.assert_called()

    def test_analyze_company_success(self):
        """Test successful analysis of a company."""
        llm_response = "LLM response"
        self.manager.llm_client = MagicMock()
        self.manager.llm_client.generate.return_value = llm_response

        analysis_results = self.manager._analyze_company(self.test_ticker)

        self.assertEqual(analysis_results, {"llm_analysis": llm_response})
        self.manager.logger.info.assert_called()

    def test_analyze_company_llm_failure(self):
        """Test analyze_company method when LLM analysis fails to return a response."""
        self.manager.llm_client = MagicMock()
        self.manager.llm_client.generate.return_value = None

        with self.assertRaises(ValueError) as context:
            self.manager._analyze_company(self.test_ticker)

        self.assertEqual(str(context.exception), "LLM analysis failed to return a response.")
        self.manager.logger.error.assert_called()

    def test_analyze_company_error(self):
        """Test analyze_company method when an error occurs during the analysis process."""
        self.manager.llm_client = MagicMock()
        self.manager.llm_client.generate.side_effect = Exception("LLM error")

        with self.assertRaises(Exception) as context:
            self.manager._analyze_company(self.test_ticker)

        self.assertEqual(str(context.exception), "LLM error")
        self.manager.logger.error.assert_called()

    def test_store_analysis_results_success(self):
        """Test successful storage of analysis results in the database."""
        self.manager.db_conn = MagicMock()
        self.manager.db_conn.cursor = MagicMock()
        self.manager.db_conn.cursor().__enter__.return_value = MagicMock()
        self.manager.db_conn.commit = MagicMock()

        self.manager._store_analysis_results(self.test_ticker, self.test_analysis_results)

        self.manager.logger.info.assert_called()
        self.manager.db_conn.cursor().__enter__().execute.assert_called()
        self.manager.db_conn.commit.assert_called()

    def test_store_analysis_results_error(self):
        """Test store_analysis_results method when an error occurs storing results in the database."""
        self.manager.db_conn = MagicMock()
        self.manager.db_conn.cursor.side_effect = Exception("DB error")

        with self.assertRaises(Exception) as context:
            self.manager._store_analysis_results(self.test_ticker, self.test_analysis_results)

        self.assertEqual(str(context.exception), "DB error")
        self.manager.logger.error.assert_called()

    def test_get_config_value_success(self):
        """Test successful retrieval of a configuration value."""
        self.manager.config = {"llm": {"model": "test_model"}}
        value = self.manager.get_config_value("llm.model")
        self.assertEqual(value, "test_model")

    def test_get_config_value_default(self):
        """Test retrieval of a configuration value with a default value."""
        value = self.manager.get_config_value("nonexistent.key", "default_value")
        self.assertEqual(value, "default_value")

    def test_get_config_value_nested(self):
        """Test retrieval of a nested configuration value."""
        self.manager.config = {"nested": {"level1": {"level2": "nested_value"}}}
        value = self.manager.get_config_value("nested.level1.level2")
        self.assertEqual(value, "nested_value")

    def test_get_config_value_missing(self):
        """Test retrieval of a missing configuration value."""
        value = self.manager.get_config_value("missing.key")
        self.assertIsNone(value)

    @patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(log_level='DEBUG'))
    def test_parse_args_log_level(self, mock_parse_args):
        """Test parsing command line arguments and setting log level."""
        self.manager.parse_args()
        self.manager.logger.setLevel.assert_called_with(logging.DEBUG)

    @patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(config='test_config.yaml'))
    @patch('yaml.safe_load', return_value={'test': 'config'})
    @patch('pathlib.Path.exists', return_value=True)
    def test_parse_args_config(self, mock_exists, mock_safe_load, mock_parse_args):
        """Test parsing command line arguments and loading configuration file."""
        self.manager.parse_args()
        self.assertEqual(self.manager.config, {'test': 'config'})

    @patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(db_connection_string='test_db_string'))
    @patch('dewey.core.db.connection.get_connection', return_value='test_db_connection')
    def test_parse_args_db_connection(self, mock_get_connection, mock_parse_args):
        """Test parsing command line arguments and setting database connection string."""
        self.manager.requires_db = True
        self.manager.parse_args()
        self.assertEqual(self.manager.db_conn, 'test_db_connection')

    @patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(llm_model='test_llm_model'))
    @patch('dewey.llm.llm_utils.get_llm_client', return_value='test_llm_client')
    def test_parse_args_llm_model(self, mock_get_llm_client, mock_parse_args):
        """Test parsing command line arguments and setting LLM model."""
        self.manager.enable_llm = True
        self.manager.parse_args()
        self.assertEqual(self.manager.llm_client, 'test_llm_client')

    def test_cleanup(self):
        """Test the cleanup method."""
        self.manager.db_conn = MagicMock()
        self.manager._cleanup()
        self.manager.db_conn.close.assert_called()

    def test_cleanup_no_db(self):
        """Test the cleanup method when there is no database connection."""
        self.manager.db_conn = None
        self.manager._cleanup()

    def test_get_path_absolute(self):
        """Test getting an absolute path."""
        path = "/absolute/path"
        result = self.manager.get_path(path)
        self.assertEqual(str(result), path)

    def test_get_path_relative(self):
        """Test getting a relative path."""
        path = "relative/path"
        expected_path = self.manager.PROJECT_ROOT / path
        result = self.manager.get_path(path)
        self.assertEqual(result, expected_path)

if __name__ == '__main__':
    unittest.main()
