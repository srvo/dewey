import pytest
from dewey.core.utils import MyUtils
from unittest.mock import patch

@pytest.fixture
def utils():
    # Initialize MyUtils with the 'test_config' configuration section
    return MyUtils(config_section="test_config")

def test_myutils_initialization(utils):
    """Test that MyUtils can be initialized without errors."""
    assert utils is not None

@patch("dewey.core.utils.MyUtils.db_conn")  # Mock the db_conn attribute
def test_example_utility_function(mock_db_conn, utils):
    """Test the example_utility_function."""
    mock_db_conn.return_value = None  # Ensure db_conn is None for the test
    input_data = "test input"
    result = utils.example_utility_function(input_data)
    assert "Processed:" in result
    assert input_data in result

