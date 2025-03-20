import pytest
from unittest.mock import MagicMock, patch
from dewey.core.research.companies.company_analysis_app import CompanyAnalysisApp
from dewey.core.base_script import BaseScript
import logging
from typing import Dict, Any


class TestCompanyAnalysisApp:
    """Tests for the CompanyAnalysisApp class."""

    @pytest.fixture
    def company_analysis_app(self) -> CompanyAnalysisApp:
        """Fixture for creating a CompanyAnalysisApp instance."""
        app = CompanyAnalysisApp()
        app.logger = MagicMock()  # Mock the logger
        return app

    def test_init(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the __init__ method."""
        assert company_analysis_app.name == "CompanyAnalysisApp"
        assert company_analysis_app.description == "Performs company analysis using various data sources and LLM techniques."
        assert company_analysis_app.config_section == "company_analysis"
        assert company_analysis_app.requires_db is True
        assert company_analysis_app.enable_llm is True

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.get_config_value")
    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._fetch_financial_data")
    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._analyze_company")
    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._store_analysis_results")
    def test_run_success(
        self,
        mock_store_analysis_results: MagicMock,
        mock_analyze_company: MagicMock,
        mock_fetch_financial_data: MagicMock,
        mock_get_config_value: MagicMock,
        company_analysis_app: CompanyAnalysisApp,
    ) -> None:
        """Test the run method with successful execution."""
        mock_get_config_value.return_value = "AAPL"
        mock_fetch_financial_data.return_value = {"revenue": 1000}
        mock_analyze_company.return_value = {"sentiment": "positive"}

        company_analysis_app.db_conn = MagicMock()
        company_analysis_app.db_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
        }

        company_analysis_app.run()

        mock_get_config_value.assert_called_once_with("company_ticker")
        mock_fetch_financial_data.assert_called_once_with("AAPL")
        mock_analyze_company.assert_called_once_with(
            {"ticker": "AAPL", "name": "Apple Inc."}, {"revenue": 1000}
        )
        mock_store_analysis_results.assert_called_once_with("AAPL", {"sentiment": "positive"})
        company_analysis_app.logger.info.assert_called_with("Company analysis process completed successfully.")

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.get_config_value")
    def test_run_missing_ticker(
        self,
        mock_get_config_value: MagicMock,
        company_analysis_app: CompanyAnalysisApp,
    ) -> None:
        """Test the run method when the company ticker is missing in the configuration."""
        mock_get_config_value.return_value = None

        with pytest.raises(ValueError, match="Company ticker not found in configuration."):
            company_analysis_app.run()

        mock_get_config_value.assert_called_once_with("company_ticker")
        company_analysis_app.logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.get_config_value")
    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._fetch_financial_data")
    def test_run_fetch_financial_data_error(
        self,
        mock_fetch_financial_data: MagicMock,
        mock_get_config_value: MagicMock,
        company_analysis_app: CompanyAnalysisApp,
    ) -> None:
        """Test the run method when _fetch_financial_data raises an exception."""
        mock_get_config_value.return_value = "AAPL"
        mock_fetch_financial_data.side_effect = Exception("Failed to fetch data")

        company_analysis_app.db_conn = MagicMock()
        company_analysis_app.db_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
        }

        with pytest.raises(Exception, match="Failed to fetch data"):
            company_analysis_app.run()

        mock_get_config_value.assert_called_once_with("company_ticker")
        mock_fetch_financial_data.assert_called_once_with("AAPL")
        company_analysis_app.logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.get_config_value")
    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._fetch_financial_data")
    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._analyze_company")
    def test_run_analyze_company_error(
        self,
        mock_analyze_company: MagicMock,
        mock_fetch_financial_data: MagicMock,
        mock_get_config_value: MagicMock,
        company_analysis_app: CompanyAnalysisApp,
    ) -> None:
        """Test the run method when _analyze_company raises an exception."""
        mock_get_config_value.return_value = "AAPL"
        mock_fetch_financial_data.return_value = {"revenue": 1000}
        mock_analyze_company.side_effect = Exception("Failed to analyze company")

        company_analysis_app.db_conn = MagicMock()
        company_analysis_app.db_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
        }

        with pytest.raises(Exception, match="Failed to analyze company"):
            company_analysis_app.run()

        mock_get_config_value.assert_called_once_with("company_ticker")
        mock_fetch_financial_data.assert_called_once_with("AAPL")
        mock_analyze_company.assert_called_once_with(
            {"ticker": "AAPL", "name": "Apple Inc."}, {"revenue": 1000}
        )
        company_analysis_app.logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.get_config_value")
    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._fetch_financial_data")
    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._analyze_company")
    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._store_analysis_results")
    def test_run_store_analysis_results_error(
        self,
        mock_store_analysis_results: MagicMock,
        mock_analyze_company: MagicMock,
        mock_fetch_financial_data: MagicMock,
        mock_get_config_value: MagicMock,
        company_analysis_app: CompanyAnalysisApp,
    ) -> None:
        """Test the run method when _store_analysis_results raises an exception."""
        mock_get_config_value.return_value = "AAPL"
        mock_fetch_financial_data.return_value = {"revenue": 1000}
        mock_analyze_company.return_value = {"sentiment": "positive"}
        mock_store_analysis_results.side_effect = Exception("Failed to store results")

        company_analysis_app.db_conn = MagicMock()
        company_analysis_app.db_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
        }

        with pytest.raises(Exception, match="Failed to store results"):
            company_analysis_app.run()

        mock_get_config_value.assert_called_once_with("company_ticker")
        mock_fetch_financial_data.assert_called_once_with("AAPL")
        mock_analyze_company.assert_called_once_with(
            {"ticker": "AAPL", "name": "Apple Inc."}, {"revenue": 1000}
        )
        mock_store_analysis_results.assert_called_once_with("AAPL", {"sentiment": "positive"})
        company_analysis_app.logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.logger")
    def test_fetch_financial_data_success(self, mock_logger: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the _fetch_financial_data method with successful execution."""
        ticker = "AAPL"
        # No actual API call is made, so we just check that the method runs and logs correctly
        financial_data = company_analysis_app._fetch_financial_data(ticker)
        assert financial_data == {}
        mock_logger.info.assert_any_call(f"Fetching financial data for {ticker}")
        mock_logger.info.assert_any_call(f"Successfully fetched financial data for {ticker}")

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.logger")
    def test_fetch_financial_data_error(self, mock_logger: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the _fetch_financial_data method when an exception occurs."""
        ticker = "AAPL"
        with pytest.raises(Exception):
            with patch(
                "dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._fetch_financial_data",
                side_effect=Exception("Failed to fetch data"),
            ):
                company_analysis_app._fetch_financial_data(ticker)
        mock_logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.logger")
    def test_analyze_company_success(self, mock_logger: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the _analyze_company method with successful execution."""
        company_data = {"name": "Apple Inc."}
        financial_data = {"revenue": 1000}
        # No actual LLM call is made, so we just check that the method runs and logs correctly
        analysis_results = company_analysis_app._analyze_company(company_data, financial_data)
        assert analysis_results == {}
        mock_logger.info.assert_any_call("Performing company analysis using LLM.")
        mock_logger.info.assert_any_call("Company analysis using LLM completed successfully.")

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.logger")
    def test_analyze_company_error(self, mock_logger: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the _analyze_company method when an exception occurs."""
        company_data = {"name": "Apple Inc."}
        financial_data = {"revenue": 1000}
        with pytest.raises(Exception):
            with patch(
                "dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._analyze_company",
                side_effect=Exception("Failed to analyze company"),
            ):
                company_analysis_app._analyze_company(company_data, financial_data)
        mock_logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.logger")
    def test_store_analysis_results_success(self, mock_logger: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the _store_analysis_results method with successful execution."""
        ticker = "AAPL"
        analysis_results = {"sentiment": "positive"}
        # No actual database insertion is made, so we just check that the method runs and logs correctly
        company_analysis_app._store_analysis_results(ticker, analysis_results)
        mock_logger.info.assert_any_call(f"Storing analysis results for {ticker} in the database.")
        mock_logger.info.assert_any_call(f"Successfully stored analysis results for {ticker} in the database.")

    @patch("dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp.logger")
    def test_store_analysis_results_error(self, mock_logger: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the _store_analysis_results method when an exception occurs."""
        ticker = "AAPL"
        analysis_results = {"sentiment": "positive"}
        with pytest.raises(Exception):
            with patch(
                "dewey.core.research.companies.company_analysis_app.CompanyAnalysisApp._store_analysis_results",
                side_effect=Exception("Failed to store results"),
            ):
                company_analysis_app._store_analysis_results(ticker, analysis_results)
        mock_logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.CONFIG_PATH", "nonexistent_config.yaml")
    def test_load_config_file_not_found(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test _load_config when the configuration file is not found."""
        with pytest.raises(FileNotFoundError):
            company_analysis_app._load_config()
        company_analysis_app.logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.CONFIG_PATH", "invalid_config.yaml")
    def test_load_config_invalid_yaml(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test _load_config when the configuration file contains invalid YAML."""
        # Create a dummy invalid_config.yaml file
        with open("invalid_config.yaml", "w") as f:
            f.write("invalid: yaml: content")

        with pytest.raises(Exception):
            company_analysis_app._load_config()

        company_analysis_app.logger.error.assert_called()
        # Clean up the dummy file
        import os
        os.remove("invalid_config.yaml")

    def test_load_config_section_not_found(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test _load_config when the specified config section is not found."""
        company_analysis_app.config_section = "nonexistent_section"
        config = company_analysis_app._load_config()
        assert isinstance(config, dict)
        company_analysis_app.logger.warning.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.get_connection")
    def test_initialize_db_connection_success(self, mock_get_connection: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test _initialize_db_connection when the database connection is successfully initialized."""
        company_analysis_app.config = {"core": {"database": {"connection_string": "test_db_url"}}}
        company_analysis_app._initialize_db_connection()
        assert company_analysis_app.db_conn is not None
        mock_get_connection.assert_called_once()
        company_analysis_app.logger.debug.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.get_connection")
    def test_initialize_db_connection_import_error(self, mock_get_connection: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test _initialize_db_connection when the database module cannot be imported."""
        with patch("dewey.core.research.companies.company_analysis_app.get_connection", side_effect=ImportError):
            with pytest.raises(ImportError):
                company_analysis_app._initialize_db_connection()
        company_analysis_app.logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.get_connection")
    def test_initialize_db_connection_exception(self, mock_get_connection: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test _initialize_db_connection when an exception occurs during database connection initialization."""
        mock_get_connection.side_effect = Exception("Failed to connect to database")
        company_analysis_app.config = {"core": {"database": {"connection_string": "test_db_url"}}}
        with pytest.raises(Exception, match="Failed to connect to database"):
            company_analysis_app._initialize_db_connection()
        company_analysis_app.logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.get_llm_client")
    def test_initialize_llm_client_success(self, mock_get_llm_client: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test _initialize_llm_client when the LLM client is successfully initialized."""
        company_analysis_app.config = {"llm": {"model": "test_llm_model"}}
        company_analysis_app._initialize_llm_client()
        assert company_analysis_app.llm_client is not None
        mock_get_llm_client.assert_called_once()
        company_analysis_app.logger.debug.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.get_llm_client")
    def test_initialize_llm_client_import_error(self, mock_get_llm_client: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test _initialize_llm_client when the LLM module cannot be imported."""
        with patch("dewey.core.research.companies.company_analysis_app.get_llm_client", side_effect=ImportError):
            with pytest.raises(ImportError):
                company_analysis_app._initialize_llm_client()
        company_analysis_app.logger.error.assert_called()

    @patch("dewey.core.research.companies.company_analysis_app.get_llm_client")
    def test_initialize_llm_client_exception(self, mock_get_llm_client: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test _initialize_llm_client when an exception occurs during LLM client initialization."""
        mock_get_llm_client.side_effect = Exception("Failed to initialize LLM client")
        company_analysis_app.config = {"llm": {"model": "test_llm_model"}}
        with pytest.raises(Exception, match="Failed to initialize LLM client"):
            company_analysis_app._initialize_llm_client()
        company_analysis_app.logger.error.assert_called()

    def test_setup_argparse(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the setup_argparse method."""
        parser = company_analysis_app.setup_argparse()
        assert parser.description == company_analysis_app.description
        assert parser._actions[1].dest == "config"
        assert parser._actions[2].dest == "log_level"
        assert parser._actions[3].dest == "db_connection_string"
        assert parser._actions[4].dest == "llm_model"

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_log_level(self, mock_parse_args: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test parse_args when a log level is specified."""
        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_args.config = None
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        args = company_analysis_app.parse_args()

        assert args == mock_args
        assert company_analysis_app.logger.level == logging.DEBUG
        company_analysis_app.logger.debug.assert_called_with("Log level set to DEBUG")

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config(self, mock_parse_args: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test parse_args when a config file is specified."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = "test_config.yaml"
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        # Create a dummy config file
        with open("test_config.yaml", "w") as f:
            f.write("test_key: test_value")

        args = company_analysis_app.parse_args()

        assert args == mock_args
        assert company_analysis_app.config == {"test_key": "test_value"}
        company_analysis_app.logger.info.assert_called_with("Loaded configuration from test_config.yaml")

        # Clean up the dummy file
        import os
        os.remove("test_config.yaml")

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config_not_found(self, mock_parse_args: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test parse_args when the specified config file is not found."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = "nonexistent_config.yaml"
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with pytest.raises(SystemExit) as excinfo:
            company_analysis_app.parse_args()
        assert excinfo.value.code == 1
        company_analysis_app.logger.error.assert_called_with("Configuration file not found: nonexistent_config.yaml")

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.core.research.companies.company_analysis_app.get_connection")
    def test_parse_args_db_connection_string(self, mock_get_connection: MagicMock, mock_parse_args: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test parse_args when a database connection string is specified."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.db_connection_string = "custom_db_url"
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args
        company_analysis_app.requires_db = True

        args = company_analysis_app.parse_args()

        assert args == mock_args
        mock_get_connection.assert_called_with({"connection_string": "custom_db_url"})
        assert company_analysis_app.db_conn is not None
        company_analysis_app.logger.info.assert_called_with("Using custom database connection")

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.core.research.companies.company_analysis_app.get_llm_client")
    def test_parse_args_llm_model(self, mock_get_llm_client: MagicMock, mock_parse_args: MagicMock, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test parse_args when an LLM model is specified."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.db_connection_string = None
        mock_args.llm_model = "custom_llm_model"
        mock_parse_args.return_value = mock_args
        company_analysis_app.enable_llm = True

        args = company_analysis_app.parse_args()

        assert args == mock_args
        mock_get_llm_client.assert_called_with({"model": "custom_llm_model"})
        assert company_analysis_app.llm_client is not None
        company_analysis_app.logger.info.assert_called_with("Using custom LLM model: custom_llm_model")

    def test_cleanup(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the _cleanup method."""
        company_analysis_app.db_conn = MagicMock()
        company_analysis_app._cleanup()
        company_analysis_app.db_conn.close.assert_called_once()
        company_analysis_app.logger.debug.assert_called_with("Closing database connection")

    def test_cleanup_no_db_conn(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the _cleanup method when there is no database connection."""
        company_analysis_app.db_conn = None
        company_analysis_app._cleanup()
        # Assert that no methods are called on a None object
        assert not hasattr(company_analysis_app.db_conn, "close")

    def test_cleanup_db_conn_error(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the _cleanup method when closing the database connection raises an exception."""
        company_analysis_app.db_conn = MagicMock()
        company_analysis_app.db_conn.close.side_effect = Exception("Failed to close connection")
        company_analysis_app._cleanup()
        company_analysis_app.logger.warning.assert_called()

    def test_get_path_absolute(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test get_path with an absolute path."""
        absolute_path = "/absolute/path/to/file.txt"
        resolved_path = company_analysis_app.get_path(absolute_path)
        assert resolved_path == Path(absolute_path)

    def test_get_path_relative(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test get_path with a relative path."""
        relative_path = "relative/path/to/file.txt"
        expected_path = company_analysis_app.PROJECT_ROOT / relative_path
        resolved_path = company_analysis_app.get_path(relative_path)
        assert resolved_path == expected_path

    def test_get_config_value_existing_key(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test get_config_value with an existing key."""
        company_analysis_app.config = {"level1": {"level2": {"key": "value"}}}
        value = company_analysis_app.get_config_value("level1.level2.key")
        assert value == "value"

    def test_get_config_value_missing_key(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test get_config_value with a missing key."""
        company_analysis_app.config = {"level1": {"level2": {"key": "value"}}}
        value = company_analysis_app.get_config_value("level1.level2.missing_key", "default_value")
        assert value == "default_value"

    def test_get_config_value_nested_missing_key(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test get_config_value with a missing nested key."""
        company_analysis_app.config = {"level1": {"level2": {"key": "value"}}}
        value = company_analysis_app.get_config_value("level1.missing_level2.key", "default_value")
        assert value == "default_value"

    def test_execute_success(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the execute method with successful execution."""
        with patch.object(company_analysis_app, "parse_args") as mock_parse_args, \
             patch.object(company_analysis_app, "run") as mock_run:

            mock_parse_args.return_value = MagicMock()
            company_analysis_app.execute()

            mock_parse_args.assert_called_once()
            mock_run.assert_called_once()
            company_analysis_app.logger.info.assert_any_call(f"Starting execution of {company_analysis_app.name}")
            company_analysis_app.logger.info.assert_any_call(f"Completed execution of {company_analysis_app.name}")

    def test_execute_keyboard_interrupt(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the execute method when a KeyboardInterrupt is raised."""
        with patch.object(company_analysis_app, "parse_args") as mock_parse_args, \
             patch.object(company_analysis_app, "run", side_effect=KeyboardInterrupt):

            mock_parse_args.return_value = MagicMock()
            with pytest.raises(SystemExit) as excinfo:
                company_analysis_app.execute()

            assert excinfo.value.code == 1
            company_analysis_app.logger.warning.assert_called_with("Script interrupted by user")

    def test_execute_exception(self, company_analysis_app: CompanyAnalysisApp) -> None:
        """Test the execute method when an exception is raised."""
        with patch.object(company_analysis_app, "parse_args") as mock_parse_args, \
             patch.object(company_analysis_app, "run", side_effect=Exception("Test exception")):

            mock_parse_args.return_value = MagicMock()
            with pytest.raises(SystemExit) as excinfo:
                company_analysis_app.execute()

            assert excinfo.value.code == 1
            company_analysis_app.logger.error.assert_called()
