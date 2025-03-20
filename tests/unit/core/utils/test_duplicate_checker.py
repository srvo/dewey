import pytest
from unittest.mock import patch, MagicMock
from dewey.core.utils.duplicate_checker import DuplicateChecker


class TestDuplicateChecker:
    @pytest.fixture
    def duplicate_checker(self):
        return DuplicateChecker()

    def test_check_duplicates_logging(self, duplicate_checker, caplog):
        data = ["test1", "test2", "test1"]
        threshold = 0.9
        result = duplicate_checker.check_duplicates(data, threshold)

        assert "Running duplicate check with threshold." in caplog.text
        assert f"Data received for duplicate check: {data}" in caplog.text
        assert result == ["test1"]

    def test_run_method(self, duplicate_checker, caplog):
        mock_get_config_value = MagicMock(return_value=0.7)
        duplicate_checker.get_config_value = mock_get_config_value

        data = ["item1", "item2", "item1", "item3"]
        with patch.object(duplicate_checker, 'check_duplicates', return_value=["item1"]) as mock_check_duplicates:
            duplicate_checker.run(data=data)

            mock_check_duplicates.assert_called_once_with(data, 0.7)
            assert "Starting duplicate check..." in caplog.text
            assert "Duplicate check complete." in caplog.text
            assert "Found duplicates: ['item1']" in caplog.text

    def test_run_exception(self, duplicate_checker, caplog):
        mock_get_config_value = MagicMock(side_effect=Exception("Config Error"))
        duplicate_checker.get_config_value = mock_get_config_value

        with pytest.raises(Exception, match="Config Error"):
            duplicate_checker.run()

        assert "An error occurred: Config Error" in caplog.text

    def test_duplicate_checker_basic(self):
        """
        Test the basic functionality of the DuplicateChecker.
        """
        checker = DuplicateChecker()
        data = ["item1", "item2", "item1", "item3", "item2"]
        threshold = 0.8
        duplicates = checker.check_duplicates(data, threshold)
        assert set(duplicates) == {"item1", "item2"}
