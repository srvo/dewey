import pytest
from dewey.core.utils.format_and_lint import FormatAndLint
from unittest.mock import MagicMock

def test_format_and_lint_run():
    """
    Test that the run method executes without errors and sets the formatting_performed flag.
    """
    mock_logger = MagicMock()
    format_and_lint = FormatAndLint(logger=mock_logger)
    format_and_lint.run()
    assert format_and_lint.formatting_performed is True
    mock_logger.info.assert_called_with("Formatting and linting process completed.")
