import pytest
from unittest.mock import patch, MagicMock
from dewey.core.data_upload.check_data import CheckData
from dewey.core.base_script import BaseScript
import ibis.expr.types as ir
import logging
from typing import Any, Dict

# Mock the BaseScript class to avoid actual config loading and logging setup
class MockBaseScript(BaseScript):
    """Class MockBaseScript."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Function __init__."""
        super().__init__(*args, **kwargs)
        self.config: Dict[str, Any]=None, Any]:
        """Override to prevent actual config loading."""
        return {}

    def _initialize_db_connection(self) -> None:
        """Override to prevent actual DB connection."""
        pass

    def _initialize_llm_client(self) -> None:
        """Override to prevent actual LLM client initialization."""
        pass

    def run(self) -> None:
        """Override the abstract method."""
        pass

@pytest.fixture
def check_data_instance() -> CheckData:
    """
    Fixture to create an instance of CheckData with mocked dependencies.
    """
    with patch('dewey.core.data_upload.check_data.BaseScript', new=MockBaseScript):
        if Any] is None:
            Any] = {}  # Initialize config
        self.logger = logging.getLogger(__name__)  # Initialize logger

    def _setup_logging(self) -> None:
        """Override to prevent actual logging setup."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)  # Set a default level for testing

    def _load_config(self) -> Dict[str
        check_data = CheckData()
        check_data.logger = MagicMock()  # Mock the logger
        check_data.config = {
            'check_data': {
                'data_path': 'test_data.csv',
                'table_name': 'test_table'
            },
            'llm': {}
        }  # Mock the config
        return check_data

@pytest.fixture
def mock_ibis_table() -> MagicMock:
    """
    Fixture to create a mock Ibis table expression.
    """
    return MagicMock(spec=ir.Table)

def test_check_data_initialization(check_data_instance: CheckData) -> None:
    """
    Test that CheckData instance is initialized correctly.
    """
    assert isinstance(check_data_instance, CheckData)
    assert isinstance(check_data_instance, BaseScript)
    assert check_data_instance.config_section == 'check_data'
    assert check_data_instance.requires_db == True
    assert check_data_instance.enable_llm == True

def test_run_success(check_data_instance: CheckData, mock_ibis_table: MagicMock) -> None:
    """
    Test the run method with successful data loading, analysis, and table creation.
    """
    # Mock internal methods
    check_data_instance._load_data = MagicMock(return_value=mock_ibis_table)
    check_data_instance._analyze_data = MagicMock(return_value="Analysis Result")
    check_data_instance._create_and_insert_table = MagicMock()
    check_data_instance.get_config_value = MagicMock(side_effect=lambda key, default=None: check_data_instance.config['check_data'][key] if key in check_data_instance.config['check_data'] else default)

    # Call the run method
    check_data_instance.run()

    # Assertions
    check_data_instance.logger.info.assert_any_call("Starting data check...")
    check_data_instance.logger.info.assert_any_call("Data check complete.")
    check_data_instance._load_data.assert_called_once_with('test_data.csv')
    check_data_instance._analyze_data.assert_called_once_with(mock_ibis_table)
    check_data_instance._create_and_insert_table.assert_called_once_with('test_table', mock_ibis_table)

def test_run_exception(check_data_instance: CheckData, mock_ibis_table: MagicMock) -> None:
    """
    Test the run method when an exception occurs during data checking.
    """
    # Mock internal methods to raise an exception
    check_data_instance._load_data = MagicMock(side_effect=Exception("Test Exception"))
    check_data_instance.get_config_value = MagicMock(side_effect=lambda key, default=None: check_data_instance.config['check_data'][key] if key in check_data_instance.config['check_data'] else default)

    # Call the run method and assert that it raises an exception
    with pytest.raises(Exception, match="Test Exception"):
        check_data_instance.run()

    # Assertions
    check_data_instance.logger.info.assert_any_call("Starting data check...")
    check_data_instance.logger.error.assert_called()

def test_load_data_success(check_data_instance: CheckData, mock_ibis_table: MagicMock) -> None:
    """
    Test the _load_data method with successful data loading.
    """
    # Mock the get_motherduck_connection and read_csv methods
    mock_connection = MagicMock()
    mock_connection.read_csv.return_value = mock_ibis_table
    with patch('dewey.core.data_upload.check_data.get_motherduck_connection', return_value=mock_connection):
        # Call the _load_data method
        data = check_data_instance._load_data('test_data.csv')

        # Assertions
        check_data_instance.logger.info.assert_called_with("Loading data from test_data.csv")
        mock_connection.read_csv.assert_called_once_with('test_data.csv')
        assert data == mock_ibis_table

def test_load_data_file_not_found(check_data_instance: CheckData) -> None:
    """
    Test the _load_data method when the data file is not found.
    """
    # Mock the get_motherduck_connection and read_csv methods to raise a FileNotFoundError
    mock_connection = MagicMock()
    mock_connection.read_csv.side_effect = FileNotFoundError("File not found")
    with patch('dewey.core.data_upload.check_data.get_motherduck_connection', return_value=mock_connection):
        # Call the _load_data method and assert that it raises a FileNotFoundError
        with pytest.raises(FileNotFoundError, match="File not found"):
            check_data_instance._load_data('test_data.csv')

        # Assertions
        check_data_instance.logger.info.assert_called_with("Loading data from test_data.csv")
        check_data_instance.logger.error.assert_called()

def test_load_data_exception(check_data_instance: CheckData) -> None:
    """
    Test the _load_data method when an exception occurs during data loading.
    """
    # Mock the get_motherduck_connection and read_csv methods to raise an exception
    mock_connection = MagicMock()
    mock_connection.read_csv.side_effect = Exception("Test Exception")
    with patch('dewey.core.data_upload.check_data.get_motherduck_connection', return_value=mock_connection):
        # Call the _load_data method and assert that it raises an exception
        with pytest.raises(Exception, match="Test Exception"):
            check_data_instance._load_data('test_data.csv')

        # Assertions
        check_data_instance.logger.info.assert_called_with("Loading data from test_data.csv")
        check_data_instance.logger.error.assert_called()

def test_analyze_data_success(check_data_instance: CheckData, mock_ibis_table: MagicMock) -> None:
    """
    Test the _analyze_data method with successful LLM call.
    """
    # Mock the call_llm method
    mock_response = "LLM Analysis Result"
    with patch('dewey.core.data_upload.check_data.call_llm', return_value=mock_response) as mock_call_llm:
        # Call the _analyze_data method
        result = check_data_instance._analyze_data(mock_ibis_table)

        # Assertions
        check_data_instance.logger.info.assert_called_with("Analyzing data using LLM...")
        mock_call_llm.assert_called_once()
        assert result == mock_response

def test_analyze_data_exception(check_data_instance: CheckData, mock_ibis_table: MagicMock) -> None:
    """
    Test the _analyze_data method when an exception occurs during LLM call.
    """
    # Mock the call_llm method to raise an exception
    with patch('dewey.core.data_upload.check_data.call_llm', side_effect=Exception("LLM Test Exception")):
        # Call the _analyze_data method and assert that it raises an exception
        with pytest.raises(Exception, match="LLM Test Exception"):
            check_data_instance._analyze_data(mock_ibis_table)

        # Assertions
        check_data_instance.logger.info.assert_called_with("Analyzing data using LLM...")
        check_data_instance.logger.error.assert_called()

def test_create_and_insert_table_success(check_data_instance: CheckData, mock_ibis_table: MagicMock) -> None:
    """
    Test the _create_and_insert_table method with successful table creation and data insertion.
    """
    # Mock the get_motherduck_connection and create_table methods
    mock_connection = MagicMock()
    with patch('dewey.core.data_upload.check_data.get_motherduck_connection', return_value=mock_connection):
        # Call the _create_and_insert_table method
        check_data_instance._create_and_insert_table('test_table', mock_ibis_table)

        # Assertions
        check_data_instance.logger.info.assert_called_with("Creating table test_table and inserting data...")
        mock_connection.create_table.assert_called_once_with('test_table', data=mock_ibis_table)

def test_create_and_insert_table_exception(check_data_instance: CheckData, mock_ibis_table: MagicMock) -> None:
    """
    Test the _create_and_insert_table method when an exception occurs during table creation or data insertion.
    """
    # Mock the get_motherduck_connection and create_table methods to raise an exception
    mock_connection = MagicMock()
    mock_connection.create_table.side_effect = Exception("Table Creation Test Exception")
    with patch('dewey.core.data_upload.check_data.get_motherduck_connection', return_value=mock_connection):
        # Call the _create_and_insert_table method and assert that it raises an exception
        with pytest.raises(Exception, match="Table Creation Test Exception"):
            check_data_instance._create_and_insert_table('test_table', mock_ibis_table)

        # Assertions
        check_data_instance.logger.info.assert_called_with("Creating table test_table and inserting data...")
        check_data_instance.logger.error.assert_called()
