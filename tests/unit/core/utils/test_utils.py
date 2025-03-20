import pytest
from dewey.core.utils import MyUtils
from unittest.mock import patch


@pytest.fixture
def utils_instance(caplog):
    caplog.set_level("INFO")  # Ensure all log messages are captured
    return MyUtils(config_section="test_config")


def test_example_utility_function(utils_instance, caplog):
    input_data = "test_input"
    result = utils_instance.example_utility_function(input_data)
    assert result == "Processed: test_input"
    assert "Processing input data: test_input" in caplog.text
    assert "Output data: Processed: test_input" in caplog.text


@pytest.mark.usefixtures("utils_instance")
def test_run_method(utils_instance, caplog):
    caplog.set_level("INFO")
    with patch.object(utils_instance, "db_conn") as mock_db_conn, \
         patch.object(utils_instance, "llm_client") as mock_llm_client:

        # Mock the db_conn and llm_client to simulate their availability
        mock_db_conn.return_value = True
        mock_llm_client.return_value = True

        utils_instance.run()

        assert "Starting utility functions..." in caplog.text

        # Check if database operations were attempted
        if mock_db_conn.return_value:
            assert "Executing example database operation..." in caplog.text
            # You might want to further mock the cursor and execute methods
            # to avoid actual database calls during testing

        # Check if LLM call was attempted
        if mock_llm_client.return_value:
            assert "Making example LLM call..." in caplog.text

        assert "Utility functions completed." in caplog.text
