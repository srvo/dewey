import pytest
import logging
from dewey.core.utils import MyUtils

logger = logging.getLogger(__name__)

@pytest.fixture
def utils_instance(caplog):
    caplog.set_level(logging.INFO)
    utils = MyUtils(config_section="test_config")
    logger.info(f"Utils instance initialized: {utils}")
    return utils

def test_my_utils_initialization(utils_instance):
    logger.info("Starting test_my_utils_initialization")
    assert utils_instance is not None, "Utils instance should not be None"
    logger.info("test_my_utils_initialization passed")

def test_example_utility_function(utils_instance, caplog):
    logger.info("Starting test_example_utility_function")
    input_data = "test_input"
    result = utils_instance.example_utility_function(input_data)
    logger.info(f"Result of example_utility_function: {result}")
    assert "Processed: test_input" in result, "Result should contain 'Processed: test_input'"
    assert "Processing input data: test_input" in caplog.text
    assert "Output data: Processed: test_input" in caplog.text
    logger.info("test_example_utility_function passed")

def test_run_method(utils_instance, caplog):
    logger.info("Starting test_run_method")
    caplog.set_level(logging.INFO)
    utils_instance.run()
    assert "Starting utility functions..." in caplog.text
    assert "Example config value:" in caplog.text
    logger.info("test_run_method passed")
