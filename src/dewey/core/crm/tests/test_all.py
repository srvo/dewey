"""Main test runner for the CRM module tests.

This module provides a way to run all CRM module tests from a single entry point.
"""

import os
import sys

import pytest

from dewey.core.base_script import BaseScript


class CrmTestRunner(BaseScript):
    """A class to run all CRM tests.

    This class provides a way to run all tests in the CRM module
    with a single command, using the pytest framework.
    """

    def __init__(self) -> None:
        """Initialize the test runner."""
        super().__init__(config_section="crm_test_runner")

    def execute(self) -> None:
        """Run all CRM tests.

        This method discovers and runs all test files in the CRM tests directory.
        """
        self.logger.info("Starting CRM test suite...")

        try:
            # Get the directory where this file is located
            test_dir = os.path.dirname(os.path.abspath(__file__))

            # Run pytest on the test directory
            result = pytest.main(["-v", test_dir])

            # Process the result
            if result == 0:
                self.logger.info("All tests passed!")
            else:
                self.logger.error(f"Tests failed with exit code: {result}")

        except Exception as e:
            self.logger.error(f"Error running tests: {e}")
            raise

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.execute()


if __name__ == "__main__":
    # Run the tests
    runner = CrmTestRunner()
    runner.run()

    # Exit with the appropriate status code
    sys.exit(0)
