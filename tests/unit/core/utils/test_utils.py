import pytest
from unittest.mock import patch
from dewey.core.utils import MyUtils

@pytest.fixture
def mock_base_script(mocker):
    """Mock BaseScript methods to isolate MyUtils."""
    mocker.patch("dewey.core.utils.BaseScript.__init__", return_value=None)
    mocker.patch("dewey.core.utils.BaseScript.get_config_value", return_value="test_value")
    mocker.patch("dewey.core.utils.BaseScript.db_conn", return_value=None)
    mocker.patch("dewey.core.utils.BaseScript.llm_client", return_value=None)
    mocker.patch("dewey.core.utils.BaseScript.logger")

@pytest.fixture
def my_utils(mock_base_script):
    """Fixture for MyUtils with mocked dependencies."""
    return MyUtils()

def test_my_utils_initialization(my_utils):
    """Test that MyUtils can be initialized."""
    assert my_utils is not None

def test_example_utility_function(my_utils):
    """Test the example utility function."""
    input_data = "test_input"
    result = my_utils.example_utility_function(input_data)
    assert result == f"Processed: {input_data}"
