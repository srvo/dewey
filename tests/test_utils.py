import pytest
from dewey.core.utils import MyUtils

@pytest.fixture
def utils():
    # Initialize MyUtils with a test configuration section
    return MyUtils(config_section="test_config")

def test_example_utility_function(utils):
    input_data = "test input"
    result = utils.example_utility_function(input_data)
    assert "Processed:" in result
    assert input_data in result

