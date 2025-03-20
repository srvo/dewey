from unittest.mock import patch

import pytest
from dewey.core.utils.duplicate_checker import DuplicateChecker


def test_duplicate_checker_run():
    """
    Test that the DuplicateChecker can be instantiated and its run method can be called without errors.
    """
    checker = DuplicateChecker()
    with patch.object(checker.logger, "info") as mock_info, \
         patch.object(checker.logger, "debug") as mock_debug:
        checker.run()

        assert mock_info.call_count == 2
        mock_info.assert_any_call("Starting duplicate check...")
        mock_info.assert_any_call("Duplicate check complete.")
        mock_debug.assert_called_once()
