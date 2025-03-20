import pytest
from unittest.mock import patch
from dewey.core.utils.format_and_lint import FormatAndLint

def test_format_and_lint_error():
    """Test that FormatAndLint raises an exception when an error occurs and formatting_performed is False."""
    format_and_lint = FormatAndLint()
    with patch.object(FormatAndLint, 'get_config_value', side_effect=Exception("Test exception")):
        with pytest.raises(Exception, match="Test exception"):
            format_and_lint.run()
        assert format_and_lint.formatting_performed is False
