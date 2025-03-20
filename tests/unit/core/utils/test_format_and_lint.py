import pytest
from unittest.mock import patch
from dewey.core.utils.format_and_lint import FormatAndLint
from dewey.core.base_script import BaseScript

class TestFormatAndLint:
    @pytest.fixture
    def format_and_lint(self):
        return FormatAndLint()

    @patch.object(BaseScript, 'get_config_value')
    @patch.object(BaseScript, 'logger')
    def test_run(self, mock_logger, mock_get_config_value, format_and_lint):
        mock_get_config_value.return_value = 'test_value'
        format_and_lint.run()
        mock_logger.info.assert_called()
