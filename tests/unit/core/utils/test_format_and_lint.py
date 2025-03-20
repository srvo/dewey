import pytest
from dewey.core.utils.format_and_lint import FormatAndLint
import logging

def test_format_and_lint_run(caplog):
    """
    Test that the FormatAndLint class runs without errors and logs messages.
    """
    caplog.set_level(logging.INFO)
    formatter = FormatAndLint()
    formatter.run()
    assert "Starting formatting and linting process." in caplog.text
    assert "Formatting and linting process completed." in caplog.text
