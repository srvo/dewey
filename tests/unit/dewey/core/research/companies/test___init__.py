import logging
from unittest.mock import MagicMock, patch

import pytest
from dewey.core.base_script import BaseScript
from dewey.core.research.companies import CompanyResearch


class TestCompanyResearch:
    """Tests for the CompanyResearch class."""

    @pytest.fixture
    def company_research(self) -> CompanyResearch:
        """Fixture for creating a CompanyResearch instance."""
        return CompanyResearch()

    def test_initialization(self, company_research: CompanyResearch) -> None:
        """Test the initialization of the CompanyResearch class."""
        assert company_research.name == "CompanyResearch"
        assert company_research.description == "Base class for company research scripts."
        assert company_research.config_section == "company_research"
        assert company_research.requires_db is True
        assert company_research.enable_llm is True
        assert isinstance(company_research, BaseScript)
        assert company_research.logger is not None
        assert company_research.config is not None
        assert company_research.db_conn is None  # Not initialized yet
        assert company_research.llm_client is None  # Not initialized yet

    @patch("dewey.core.research.companies.CompanyResearch.get_config_value")
    def test_run_no_db_no_llm(
        self, mock_get_config_value: MagicMock, company_research: CompanyResearch
    ) -> None:
        """Test the run method without database and LLM connections."""
        company_research.db_conn = None
        company_research.llm_client = None
        mock_get_config_value.return_value = "test_value"

        company_research.run()

        mock_get_config_value.assert_called_with("example_config_key", "default_value")
        assert "Starting company research..." in company_research.logger.handlers[0].format % company_research.__dict__
        assert "Example config value: test_value" in company_research.logger.handlers[0].format % company_research.__dict__
        assert "Database connection is not available." in company_research.logger.handlers[0].format % company_research.__dict__
        assert "LLM client is not available." in company_research.logger.handlers[0].format % company_research.__dict__
        assert "Company research completed." in company_research.logger.handlers[0].format % company_research.__dict__

    @patch("dewey.core.research.companies.CompanyResearch.get_config_value")
    def test_run_with_db_and_llm(
        self, mock_get_config_value: MagicMock, company_research: CompanyResearch
    ) -> None:
        """Test the run method with database and LLM connections."""
        # Mock database connection and cursor
        mock_db_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = ["company1", "company2"]
        company_research.db_conn = mock_db_conn

        # Mock LLM client
        mock_llm_client = MagicMock()
        mock_llm_client.generate.return_value = "Apple is a great company."
        company_research.llm_client = mock_llm_client

        mock_get_config_value.return_value = "test_value"

        company_research.run()

        mock_get_config_value.assert_called_with("example_config_key", "default_value")
        mock_db_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_with("SELECT * FROM companies LIMIT 10;")
        mock_cursor.fetchall.assert_called_once()
        mock_llm_client.generate.assert_called_with(prompt="Tell me about the company Apple.")
        assert "Successfully connected to the database." in company_research.logger.handlers[0].format % company_research.__dict__
        assert "Example query results: ['company1', 'company2']" in company_research.logger.handlers[0].format % company_research.__dict__
        assert "Successfully initialized LLM client." in company_research.logger.handlers[0].format % company_research.__dict__
        assert "LLM response: Apple is a great company." in company_research.logger.handlers[0].format % company_research.__dict__
        assert "Company research completed." in company_research.logger.handlers[0].format % company_research.__dict__

    @patch("dewey.core.research.companies.CompanyResearch.get_config_value")
    def test_run_db_error(
        self, mock_get_config_value: MagicMock, company_research: CompanyResearch
    ) -> None:
        """Test the run method with a database error."""
        # Mock database connection and cursor
        mock_db_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        company_research.db_conn = mock_db_conn
        company_research.llm_client = MagicMock()  # Prevent LLM from running

        mock_get_config_value.return_value = "test_value"

        with pytest.raises(Exception) as exc_info:
            company_research.run()

        assert "Error executing database query: Database error" in company_research.logger.handlers[0].format % company_research.__dict__
        assert "An error occurred during company research: Database error" in company_research.logger.handlers[0].format % company_research.__dict__
        assert str(exc_info.value) == "Database error"

    @patch("dewey.core.research.companies.CompanyResearch.get_config_value")
    def test_run_llm_error(
        self, mock_get_config_value: MagicMock, company_research: CompanyResearch
    ) -> None:
        """Test the run method with an LLM error."""
        # Mock LLM client
        mock_llm_client = MagicMock()
        mock_llm_client.generate.side_effect = Exception("LLM error")
        company_research.llm_client = mock_llm_client
        company_research.db_conn = MagicMock()  # Prevent DB from running

        mock_get_config_value.return_value = "test_value"

        with pytest.raises(Exception) as exc_info:
            company_research.run()

        assert "Error calling LLM: LLM error" in company_research.logger.handlers[0].format % company_research.__dict__
        assert "An error occurred during company research: LLM error" in company_research.logger.handlers[0].format % company_research.__dict__
        assert str(exc_info.value) == "LLM error"

    @patch("dewey.core.research.companies.CONFIG_PATH", "nonexistent_config.yaml")
    def test_load_config_file_not_found(self, company_research: CompanyResearch) -> None:
        """Test loading configuration when the file is not found."""
        with pytest.raises(FileNotFoundError):
            company_research._load_config()

    @patch("dewey.core.research.companies.yaml.safe_load", side_effect=yaml.YAMLError)
    def test_load_config_yaml_error(self, mock_safe_load: MagicMock, company_research: CompanyResearch) -> None:
        """Test loading configuration when there is a YAML error."""
        with pytest.raises(yaml.YAMLError):
            company_research._load_config()

    @patch("dewey.core.research.companies.get_connection")
    def test_initialize_db_connection_import_error(self, mock_get_connection: MagicMock, company_research: CompanyResearch) -> None:
        """Test initializing database connection when the module cannot be imported."""
        with patch("dewey.core.research.companies.importlib.import_module") as mock_import_module:
            mock_import_module.side_effect = ImportError
            with pytest.raises(ImportError):
                company_research._initialize_db_connection()

    @patch("dewey.core.research.companies.get_llm_client")
    def test_initialize_llm_client_import_error(self, mock_get_llm_client: MagicMock, company_research: CompanyResearch) -> None:
        """Test initializing LLM client when the module cannot be imported."""
        with patch("dewey.core.research.companies.importlib.import_module") as mock_import_module:
            mock_import_module.side_effect = ImportError
            with pytest.raises(ImportError):
                company_research._initialize_llm_client()

    def test_get_path_absolute(self, company_research: CompanyResearch) -> None:
        """Test getting an absolute path."""
        absolute_path = "/absolute/path"
        assert company_research.get_path(absolute_path) == Path(absolute_path)

    def test_get_path_relative(self, company_research: CompanyResearch) -> None:
        """Test getting a relative path."""
        relative_path = "relative/path"
        expected_path = company_research.PROJECT_ROOT / relative_path
        assert company_research.get_path(relative_path) == expected_path

    def test_get_config_value_existing_key(self, company_research: CompanyResearch) -> None:
        """Test getting an existing configuration value."""
        company_research.config = {"section": {"key": "value"}}
        assert company_research.get_config_value("section.key") == "value"

    def test_get_config_value_missing_key(self, company_research: CompanyResearch) -> None:
        """Test getting a missing configuration value with a default."""
        company_research.config = {"section": {}}
        assert company_research.get_config_value("section.missing_key", "default") == "default"

    def test_get_config_value_nested_missing_key(self, company_research: CompanyResearch) -> None:
        """Test getting a value from a nested missing key."""
        company_research.config = {"section": {}}
        assert company_research.get_config_value("section.missing.key", "default") == "default"

    def test_get_config_value_no_default(self, company_research: CompanyResearch) -> None:
        """Test getting a missing configuration value without a default."""
        company_research.config = {"section": {}}
        assert company_research.get_config_value("section.missing_key") is None

    @patch("dewey.core.research.companies.logging.basicConfig")
    def test_setup_logging_from_config(self, mock_basicConfig: MagicMock, company_research: CompanyResearch) -> None:
        """Test setting up logging from the configuration file."""
        # Mock the configuration file
        mock_config = {
            'core': {
                'logging': {
                    'level': 'DEBUG',
                    'format': '%(levelname)s - %(message)s',
                    'date_format': '%Y-%m-%d',
                }
            }
        }
        with patch("dewey.core.research.companies.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            with patch("dewey.core.research.companies.yaml.safe_load", return_value=mock_config):
                company_research._setup_logging()

        mock_basicConfig.assert_called_once_with(
            level=logging.DEBUG,
            format='%(levelname)s - %(message)s',
            datefmt='%Y-%m-%d',
        )
        assert isinstance(company_research.logger, logging.Logger)

    @patch("dewey.core.research.companies.logging.basicConfig")
    def test_setup_logging_default_config(self, mock_basicConfig: MagicMock, company_research: CompanyResearch) -> None:
        """Test setting up logging with default configuration."""
        # Mock the configuration file to raise an exception
        with patch("dewey.core.research.companies.open", side_effect=FileNotFoundError):
            company_research._setup_logging()

        mock_basicConfig.assert_called_once_with(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        assert isinstance(company_research.logger, logging.Logger)

    def test_setup_argparse(self, company_research: CompanyResearch) -> None:
        """Test setting up the argument parser."""
        parser = company_research.setup_argparse()
        assert parser.description == company_research.description
        assert parser.arguments  # Check if arguments are added

    def test_parse_args_log_level(self, company_research: CompanyResearch, caplog: pytest.LogCaptureFixture) -> None:
        """Test parsing arguments and setting the log level."""
        parser = company_research.setup_argparse()
        args = parser.parse_args(["--log-level", "DEBUG"])
        with caplog.at_level(logging.DEBUG):
            company_research.parse_args()
            assert "Log level set to DEBUG" in caplog.text

    def test_parse_args_config(self, company_research: CompanyResearch, tmp_path: Path) -> None:
        """Test parsing arguments and loading a configuration file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test: value")
        parser = company_research.setup_argparse()
        args = parser.parse_args(["--config", str(config_file)])
        company_research.parse_args()
        assert company_research.config == {"test": "value"}

    def test_parse_args_config_not_found(self, company_research: CompanyResearch, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test parsing arguments and handling a missing configuration file."""
        config_file = tmp_path / "config.yaml"
        parser = company_research.setup_argparse()
        args = parser.parse_args(["--config", str(config_file)])
        with pytest.raises(SystemExit) as exc_info:
            company_research.parse_args()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert f"Configuration file not found: {config_file}" in captured.err

    @patch("dewey.core.research.companies.get_connection")
    def test_parse_args_db_connection_string(self, mock_get_connection: MagicMock, company_research: CompanyResearch) -> None:
        """Test parsing arguments and setting the database connection string."""
        company_research.requires_db = True
        parser = company_research.setup_argparse()
        args = parser.parse_args(["--db-connection-string", "test_connection_string"])
        company_research.parse_args()
        mock_get_connection.assert_called_with({"connection_string": "test_connection_string"})

    @patch("dewey.core.research.companies.get_llm_client")
    def test_parse_args_llm_model(self, mock_get_llm_client: MagicMock, company_research: CompanyResearch) -> None:
        """Test parsing arguments and setting the LLM model."""
        company_research.enable_llm = True
        parser = company_research.setup_argparse()
        args = parser.parse_args(["--llm-model", "test_llm_model"])
        company_research.parse_args()
        mock_get_llm_client.assert_called_with({"model": "test_llm_model"})

    def test_execute_keyboard_interrupt(self, company_research: CompanyResearch, capsys: pytest.CaptureFixture) -> None:
        """Test executing the script and handling a KeyboardInterrupt."""
        with patch.object(company_research, "parse_args", side_effect=KeyboardInterrupt):
            with pytest.raises(SystemExit) as exc_info:
                company_research.execute()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Script interrupted by user" in captured.err

    def test_execute_exception(self, company_research: CompanyResearch, capsys: pytest.CaptureFixture) -> None:
        """Test executing the script and handling an exception."""
        with patch.object(company_research, "run", side_effect=Exception("Test exception")):
            with pytest.raises(SystemExit) as exc_info:
                company_research.execute()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error executing script: Test exception" in captured.err

    def test_cleanup(self, company_research: CompanyResearch) -> None:
        """Test cleaning up resources."""
        mock_db_conn = MagicMock()
        company_research.db_conn = mock_db_conn
        company_research._cleanup()
        mock_db_conn.close.assert_called_once()

    def test_cleanup_no_db_conn(self, company_research: CompanyResearch) -> None:
        """Test cleaning up resources when there is no database connection."""
        company_research.db_conn = None
        company_research._cleanup()
        # Assert that no exception is raised

    def test_cleanup_db_conn_error(self, company_research: CompanyResearch, caplog: pytest.LogCaptureFixture) -> None:
        """Test cleaning up resources when there is an error closing the database connection."""
        mock_db_conn = MagicMock()
        mock_db_conn.close.side_effect = Exception("Close error")
        company_research.db_conn = mock_db_conn
        with caplog.at_level(logging.WARNING):
            company_research._cleanup()
            assert "Error closing database connection: Close error" in caplog.text
