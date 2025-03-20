import pytest
from unittest.mock import patch
from dewey.core.utils.duplicate_checker import DuplicateChecker


def test_duplicate_checker_run_no_error(caplog):
    """
    Test that DuplicateChecker.run() executes without errors and logs messages.
    """
    checker = DuplicateChecker()
    checker.run()

    # Assert that the expected log messages are present
    assert "Starting duplicate check..." in caplog.text
    assert "Placeholder: Running duplicate check with threshold." in caplog.text
    assert "Duplicate check complete." in caplog.text


def test_duplicate_checker_check_duplicates(caplog):
    """
    Test the check_duplicates method.
    """
    checker = DuplicateChecker()
    threshold = 0.9
    checker.check_duplicates(threshold)
    assert f"Placeholder: Running duplicate check with threshold." in caplog.text


def test_run_exception(caplog):
    """Test the exception handling in run."""
    checker = DuplicateChecker()
    with patch.object(checker, 'get_config_value', side_effect=Exception("Config Error")):
        with pytest.raises(Exception, match="Config Error"):
            checker.run()
        assert "An error occurred: Config Error" in caplog.text
