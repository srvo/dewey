import pytest
from unittest.mock import patch
from dewey.core.utils.duplicate_checker import DuplicateChecker

class TestDuplicateChecker:
    @pytest.fixture
    def duplicate_checker(self):
        return DuplicateChecker()

    def test_run_success(self, duplicate_checker):
        with patch.object(duplicate_checker.logger, 'info') as mock_info, \
             patch.object(duplicate_checker, 'get_config_value', return_value=0.8):
            duplicate_checker.run()
            assert mock_info.call_count >= 2
            assert "Starting duplicate check..." in str(mock_info.call_args_list[0])
            assert "Duplicate check complete." in str(mock_info.call_args_list[-1])

    def test_run_exception(self, duplicate_checker):
        with patch.object(duplicate_checker, 'get_config_value', side_effect=Exception("Config Error")), \
             pytest.raises(Exception, match="Config Error"):
            duplicate_checker.run()
