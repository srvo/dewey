import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.research.companies.populate_stocks import PopulateStocks


class TestPopulateStocks:
    """Tests for the PopulateStocks class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Mocks the BaseScript class."""
        with patch("dewey.core.research.companies.populate_stocks.BaseScript", autospec=True) as mock:
            yield mock

    @pytest.fixture
    def populate_stocks(self, mock_base_script: MagicMock) -> PopulateStocks:
        """Creates an instance of PopulateStocks with mocked dependencies."""
        return PopulateStocks()

    def test_init(self, mock_base_script: MagicMock) -> None:
        """Tests the __init__ method."""
        PopulateStocks(
            name="TestScript", description="Test Description", config_section="test_config", requires_db=False, enable_llm=False, )
        mock_base_script.assert_called_once_with(
            name="TestScript", description="Test Description", config_section="test_config", requires_db=False, enable_llm=False, )

    def test_run_success(self, populate_stocks: PopulateStocks) -> None:
        """Tests the run method with successful API key retrieval."""
        mock_api_key = "test_api_key"
        populate_stocks.get_config_value = MagicMock(return_value=mock_api_key)
        populate_stocks.logger = MagicMock()

        populate_stocks.run()

        populate_stocks.get_config_value.assert_called_once_with("api_key")
        populate_stocks.logger.info.assert_any_call(f"Using API key: {mock_api_key}")
        populate_stocks.logger.info.assert_called_with("Stock population process completed.")

    def test_run_no_api_key(self, populate_stocks: PopulateStocks) -> None:
        """Tests the run method when no API key is found in the configuration."""
        populate_stocks.get_config_value = MagicMock(return_value=None)
        populate_stocks.logger = MagicMock()

        populate_stocks.run()

        populate_stocks.get_config_value.assert_called_once_with("api_key")
        populate_stocks.logger.info.assert_called_with("Using API key: None")
        populate_stocks.logger.info.assert_called_with("Stock population process completed.")

    def test_get_config_value_existing_key(self, populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when the key exists in the configuration."""
        populate_stocks.config = {"section": {"key": "value"}}
        value = populate_stocks.get_config_value("section.key")
        assert value == "value"

    def test_get_config_value_missing_key(self, populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when the key does not exist in the configuration."""
        populate_stocks.config=None, "default_value")
        assert value == "default_value"

    def test_get_config_value_nested_missing_key(self, populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when a nested key does not exist."""
        populate_stocks.config=None, "default_value")
        assert value == "default_value"

    def test_get_config_value_default_none(self, populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when the key is missing and the default value is None."""
        populate_stocks.config=None, populate_stocks: PopulateStocks) -> None:
        """Tests the execute method with a successful run."""
        populate_stocks.parse_args = MagicMock()
        populate_stocks.run = MagicMock()
        populate_stocks.logger = MagicMock()
        populate_stocks._cleanup = MagicMock()

        populate_stocks.execute()

        populate_stocks.parse_args.assert_called_once()
        populate_stocks.run.assert_called_once()
        populate_stocks.logger.info.assert_any_call(f"Starting execution of {populate_stocks.name}")
        populate_stocks.logger.info.assert_any_call(f"Completed execution of {populate_stocks.name}")
        populate_stocks._cleanup.assert_called_once()

    def test_execute_keyboard_interrupt(self, populate_stocks: PopulateStocks) -> None:
        """Tests the execute method when a KeyboardInterrupt is raised."""
        populate_stocks.parse_args = MagicMock()
        populate_stocks.run = MagicMock(side_effect=KeyboardInterrupt)
        populate_stocks.logger = MagicMock()
        populate_stocks._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            populate_stocks.execute()

        assert exc_info.value.code == 1
        populate_stocks.logger.warning.assert_called_once_with("Script interrupted by user")
        populate_stocks._cleanup.assert_called_once()

    def test_execute_exception(self, populate_stocks: PopulateStocks) -> None:
        """Tests the execute method when an exception is raised."""
        populate_stocks.parse_args = MagicMock()
        populate_stocks.run = MagicMock(side_effect=ValueError("Test Exception"))
        populate_stocks.logger = MagicMock()
        populate_stocks._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            populate_stocks.execute()

        assert exc_info.value.code == 1
        populate_stocks.logger.error.assert_called_once()
        populate_stocks._cleanup.assert_called_once()

    def test_cleanup_db_connection(self, populate_stocks: PopulateStocks) -> None:
        """Tests the _cleanup method when a database connection exists."""
        populate_stocks.db_conn = MagicMock()
        populate_stocks.logger = MagicMock()

        populate_stocks._cleanup()

        populate_stocks.logger.debug.assert_called_once_with("Closing database connection")
        populate_stocks.db_conn.close.assert_called_once()

    def test_cleanup_no_db_connection(self, populate_stocks: PopulateStocks) -> None:
        """Tests the _cleanup method when no database connection exists."""
        populate_stocks.db_conn = None
        populate_stocks.logger = MagicMock()

        populate_stocks._cleanup()

        populate_stocks.logger.debug.assert_not_called()

    def test_cleanup_db_connection_error(self, populate_stocks: PopulateStocks) -> None:
        """Tests the _cleanup method when closing the database connection raises an exception."""
        populate_stocks.db_conn = MagicMock()
        populate_stocks.db_conn.close.side_effect = ValueError("Test Exception")
        populate_stocks.logger = MagicMock()

        populate_stocks._cleanup()

        populate_stocks.logger.warning.assert_called_once()

    def test_get_path_absolute(self, populate_stocks: PopulateStocks) -> None:
        """Tests get_path with an absolute path."""
        absolute_path = "/absolute/path"
        path = populate_stocks.get_path(absolute_path)
        assert str(path) == absolute_path

    def test_get_path_relative(self, populate_stocks: PopulateStocks) -> None:
        """Tests get_path with a relative path."""
        relative_path = "relative/path"
        expected_path = populate_stocks.PROJECT_ROOT / relative_path
        path = populate_stocks.get_path(relative_path)
        assert path == expected_path

    def test_setup_logging_from_config(self, populate_stocks: PopulateStocks) -> None:
        """Tests _setup_logging when log configuration is available in dewey.yaml."""
        mock_config = {
            'core': {
                'logging': {
                    'level': 'DEBUG', 'format': '%(levelname)s - %(message)s', 'date_format': '%Y-%m-%d', }
            }
        }
        with patch("builtins.open", MagicMock()) as mock_open, \
             patch("yaml.safe_load", MagicMock(return_value=mock_config)), \
             patch("logging.basicConfig") as mock_basic_config, \
             patch("logging.getLogger") as mock_get_logger:
            mock_open.return_value.__enter__.return_value = mock_open.return_value
            populate_stocks._setup_logging()

            mock_basic_config.assert_called_once()
            kwargs = mock_basic_config.call_args[1]
            assert kwargs['level'] == logging.DEBUG
            assert kwargs['format'] == '%(levelname)s - %(message)s'
            assert kwargs['datefmt'] == '%Y-%m-%d'
            mock_get_logger.assert_called_once_with(populate_stocks.name)

    def test_setup_logging_default_config(self, populate_stocks: PopulateStocks) -> None:
        """Tests _setup_logging when dewey.yaml is not found or cannot be parsed."""
        with patch("builtins.open", MagicMock(side_effect=FileNotFoundError)), \
             patch("logging.basicConfig") as mock_basic_config, \
             patch("logging.getLogger") as mock_get_logger:
            populate_stocks._setup_logging()

            mock_basic_config.assert_called_once()
            kwargs = mock_basic_config.call_args[1]
            assert kwargs['level'] == logging.INFO
            assert kwargs['format'] == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            assert kwargs['datefmt'] == '%Y-%m-%d %H:%M:%S'
            mock_get_logger.assert_called_once_with(populate_stocks.name)

    def test_setup_logging_invalid_yaml(self, populate_stocks: PopulateStocks) -> None:
        """Tests _setup_logging when dewey.yaml contains invalid YAML."""
        with patch("builtins.open", MagicMock()) as mock_open, \
             patch("yaml.safe_load", MagicMock(side_effect=yaml.YAMLError)), \
             patch("logging.basicConfig") as mock_basic_config, \
             patch("logging.getLogger") as mock_get_logger:
            mock_open.return_value.__enter__.return_value = mock_open.return_value
            populate_stocks._setup_logging()

            mock_basic_config.assert_called_once()
            kwargs = mock_basic_config.call_args[1]
            assert kwargs['level'] == logging.INFO
            assert kwargs['format'] == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            assert kwargs['datefmt'] == '%Y-%m-%d %H:%M:%S'
            mock_get_logger.assert_called_once_with(populate_stocks.name)

    def test_load_config_success(self, populate_stocks: PopulateStocks) -> None:
        """Tests _load_config when the configuration file is successfully loaded."""
        mock_config = {"key": "value"}
        with patch("builtins.open", MagicMock()) as mock_open, \
             patch("yaml.safe_load", MagicMock(return_value=mock_config)):
            if populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when the key does not exist in the configuration."""
        populate_stocks.config is None:
                populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when the key does not exist in the configuration."""
        populate_stocks.config = {"section": {}}
        value = populate_stocks.get_config_value("section.missing_key"
            if populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when a nested key does not exist."""
        populate_stocks.config is None:
                populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when a nested key does not exist."""
        populate_stocks.config = {"section": {}}
        value = populate_stocks.get_config_value("section.nested.missing_key"
            if populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when the key is missing and the default value is None."""
        populate_stocks.config is None:
                populate_stocks: PopulateStocks) -> None:
        """Tests get_config_value when the key is missing and the default value is None."""
        populate_stocks.config = {"section": {}}
        value = populate_stocks.get_config_value("section.missing_key")
        assert value is None

    def test_execute_success(self
            mock_open.return_value.__enter__.return_value = mock_open.return_value
            config = populate_stocks._load_config()
            assert config == mock_config

    def test_load_config_section_success(self, populate_stocks: PopulateStocks) -> None:
        """Tests _load_config when a specific configuration section is loaded."""
        populate_stocks.config_section = "test_section"
        mock_config = {"test_section": {"key": "value"}}
        with patch("builtins.open", MagicMock()) as mock_open, \
             patch("yaml.safe_load", MagicMock(return_value=mock_config)):
            mock_open.return_value.__enter__.return_value = mock_open.return_value
            config = populate_stocks._load_config()
            assert config == {"key": "value"}

    def test_load_config_section_missing(self, populate_stocks: PopulateStocks) -> None:
        """Tests _load_config when the specified configuration section is missing."""
        populate_stocks.config_section = "missing_section"
        mock_config = {"test_section": {"key": "value"}}
        populate_stocks.logger = MagicMock()
        with patch("builtins.open", MagicMock()) as mock_open, \
             patch("yaml.safe_load", MagicMock(return_value=mock_config)):
            mock_open.return_value.__enter__.return_value = mock_open.return_value
            config = populate_stocks._load_config()
            assert config == mock_config
        populate_stocks.logger.warning.assert_called_once()

    def test_load_config_file_not_found(self, populate_stocks: PopulateStocks) -> None:
        """Tests _load_config when the configuration file is not found."""
        with pytest.raises(FileNotFoundError), \
             patch("builtins.open", MagicMock(side_effect=FileNotFoundError)):
            populate_stocks._load_config()

    def test_load_config_invalid_yaml(self, populate_stocks: PopulateStocks) -> None:
        """Tests _load_config when the configuration file contains invalid YAML."""
        with pytest.raises(yaml.YAMLError), \
             patch("builtins.open", MagicMock()) as mock_open, \
             patch("yaml.safe_load", MagicMock(side_effect=yaml.YAMLError)):
            mock_open.return_value.__enter__.return_value = mock_open.return_value
            populate_stocks._load_config()

    def test_initialize_db_connection_success(self, populate_stocks: PopulateStocks) -> None:
        """Tests _initialize_db_connection when the database connection is successfully initialized."""
        mock_db_conn = MagicMock()
        mock_get_connection = MagicMock(return_value=mock_db_conn)
        populate_stocks.config = {'core': {'database': {'test': 'config'}}}
        populate_stocks.logger = MagicMock()
        with patch("dewey.core.research.companies.populate_stocks.get_connection", mock_get_connection):
            populate_stocks._initialize_db_connection()
            assert populate_stocks.db_conn == mock_db_conn
            mock_get_connection.assert_called_once_with({'test': 'config'})
        populate_stocks.logger.debug.assert_called()

    def test_initialize_db_connection_import_error(self, populate_stocks: PopulateStocks) -> None:
        """Tests _initialize_db_connection when the database module cannot be imported."""
        with pytest.raises(ImportError), \
             patch("dewey.core.research.companies.populate_stocks.get_connection", side_effect=ImportError):
            populate_stocks._initialize_db_connection()

    def test_initialize_db_connection_exception(self, populate_stocks: PopulateStocks) -> None:
        """Tests _initialize_db_connection when an exception occurs during database connection initialization."""
        with pytest.raises(Exception), \
             patch("dewey.core.research.companies.populate_stocks.get_connection", side_effect=Exception("Test Exception")):
            populate_stocks._initialize_db_connection()

    def test_initialize_llm_client_success(self, populate_stocks: PopulateStocks) -> None:
        """Tests _initialize_llm_client when the LLM client is successfully initialized."""
        mock_llm_client = MagicMock()
        mock_get_llm_client = MagicMock(return_value=mock_llm_client)
        populate_stocks.config = {'llm': {'test': 'config'}}
        populate_stocks.logger = MagicMock()
        with patch("dewey.core.research.companies.populate_stocks.get_llm_client", mock_get_llm_client):
            populate_stocks._initialize_llm_client()
            assert populate_stocks.llm_client == mock_llm_client
            mock_get_llm_client.assert_called_once_with({'test': 'config'})
        populate_stocks.logger.debug.assert_called()

    def test_initialize_llm_client_import_error(self, populate_stocks: PopulateStocks) -> None:
        """Tests _initialize_llm_client when the LLM module cannot be imported."""
        with pytest.raises(ImportError), \
             patch("dewey.core.research.companies.populate_stocks.get_llm_client", side_effect=ImportError):
            populate_stocks._initialize_llm_client()

    def test_initialize_llm_client_exception(self, populate_stocks: PopulateStocks) -> None:
        """Tests _initialize_llm_client when an exception occurs during LLM client initialization."""
        with pytest.raises(Exception), \
             patch("dewey.core.research.companies.populate_stocks.get_llm_client", side_effect=Exception("Test Exception")):
            populate_stocks._initialize_llm_client()

    def test_setup_argparse(self, populate_stocks: PopulateStocks) -> None:
        """Tests the setup_argparse method."""
        parser = populate_stocks.setup_argparse()
        assert parser.description == populate_stocks.description
        assert parser.arguments[0].dest == "config"
        assert parser.arguments[1].dest == "log_level"

    def test_setup_argparse_db(self) -> None:
        """Tests the setup_argparse method with database enabled."""
        populate_stocks = PopulateStocks(requires_db=True)
        parser = populate_stocks.setup_argparse()
        assert parser.arguments[2].dest == "db_connection_string"

    def test_setup_argparse_llm(self) -> None:
        """Tests the setup_argparse method with LLM enabled."""
        populate_stocks = PopulateStocks(enable_llm=True)
        parser = populate_stocks.setup_argparse()
        assert parser.arguments[2].dest == "llm_model"

    def test_parse_args_log_level(self, populate_stocks: PopulateStocks) -> None:
        """Tests parse_args when a log level is specified."""
        mock_args = MagicMock(log_level="DEBUG", config=None)
        populate_stocks.setup_argparse = MagicMock(return_value=MagicMock())
        populate_stocks.setup_argparse.return_value.parse_args = MagicMock(return_value=mock_args)
        populate_stocks.logger = MagicMock()

        args = populate_stocks.parse_args()

        assert args == mock_args
        populate_stocks.logger.setLevel.assert_called_once_with(logging.DEBUG)
        populate_stocks.logger.debug.assert_called_once()

    def test_parse_args_config(self, populate_stocks: PopulateStocks) -> None:
        """Tests parse_args when a config file is specified."""
        mock_args = MagicMock(log_level=None, config="test_config.yaml")
        mock_config = {"test": "config"}
        populate_stocks.setup_argparse = MagicMock(return_value=MagicMock())
        populate_stocks.setup_argparse.return_value.parse_args = MagicMock(return_value=mock_args)
        populate_stocks.logger = MagicMock()

        with patch("builtins.open", MagicMock()) as mock_open, \
             patch("yaml.safe_load", MagicMock(return_value=mock_config)):
            mock_open.return_value.__enter__.return_value = mock_open.return_value
            args = populate_stocks.parse_args()

        assert args == mock_args
        assert populate_stocks.config == mock_config
        populate_stocks.logger.info.assert_called_once()

    def test_parse_args_config_not_found(self, populate_stocks: PopulateStocks) -> None:
        """Tests parse_args when the config file is not found."""
        mock_args = MagicMock(log_level=None, config="test_config.yaml")
        populate_stocks.setup_argparse = MagicMock(return_value=MagicMock())
        populate_stocks.setup_argparse.return_value.parse_args = MagicMock(return_value=mock_args)
        populate_stocks.logger = MagicMock()

        with patch("builtins.open", MagicMock(side_effect=FileNotFoundError)), \
             pytest.raises(SystemExit) as exc_info:
            populate_stocks.parse_args()

        assert exc_info.value.code == 1
        populate_stocks.logger.error.assert_called_once()

    def test_parse_args_db_connection_string(self) -> None:
        """Tests parse_args when a database connection string is specified."""
        populate_stocks = PopulateStocks(requires_db=True)
        mock_args = MagicMock(log_level=None, config=None, db_connection_string="test_connection_string")
        mock_db_conn = MagicMock()
        mock_get_connection = MagicMock(return_value=mock_db_conn)
        populate_stocks.setup_argparse = MagicMock(return_value=MagicMock())
        populate_stocks.setup_argparse.return_value.parse_args = MagicMock(return_value=mock_args)
        populate_stocks.logger = MagicMock()

        with patch("dewey.core.research.companies.populate_stocks.get_connection", mock_get_connection):
            args = populate_stocks.parse_args()

        assert args == mock_args
        assert populate_stocks.db_conn == mock_db_conn
        mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})
        populate_stocks.logger.info.assert_called_once()

    def test_parse_args_llm_model(self) -> None:
        """Tests parse_args when an LLM model is specified."""
        populate_stocks = PopulateStocks(enable_llm=True)
        mock_args = MagicMock(log_level=None, config=None, llm_model="test_llm_model")
        mock_llm_client = MagicMock()
        mock_get_llm_client = MagicMock(return_value=mock_llm_client)
        populate_stocks.setup_argparse = MagicMock(return_value=MagicMock())
        populate_stocks.setup_argparse.return_value.parse_args = MagicMock(return_value=mock_args)
        populate_stocks.logger = MagicMock()

        with patch("dewey.core.research.companies.populate_stocks.get_llm_client", mock_get_llm_client):
            args = populate_stocks.parse_args()

        assert args == mock_args
        assert populate_stocks.llm_client == mock_llm_client
        mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})
        populate_stocks.logger.info.assert_called_once()
