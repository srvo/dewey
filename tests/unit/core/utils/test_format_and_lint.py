import pytest
import logging
from dewey.core.utils.format_and_lint import FormatAndLint

def test_format_and_lint_run(caplog):
    """
    Test that the FormatAndLint class can be instantiated and the run method executes without error.
    """
    caplog.set_level(logging.INFO)
    formatter = FormatAndLint()
    formatter.run()
    assert "Starting formatting and linting process." in caplog.text
    assert "Example config value:" in caplog.text
    assert "Formatting and linting process completed." in caplog.text
