#!/usr/bin/env python
"""Validate the reorganized test structure by running tests in different directories.

This script runs pytest on the reorganized test directories and reports any issues.
"""

import os
import subprocess
import sys
from pathlib import Path

from dewey.core.base_script import BaseScript


class TestValidator(BaseScript):
    """Validate the test structure by running tests in different directories."""

    def __init__(self) -> None:
        """Initialize the TestValidator."""
        super().__init__(config_section="test_validator")
        self.success = True

    def execute(self) -> int:
        """Execute the test validation script.

        This method is required by the BaseScript abstract class.

        Returns
        -------
            int: Exit code (0 for success, 1 for failure)

        """
        return self.run()

    def run(self) -> int:
        """Run the test validation.

        Returns
        -------
            int: Exit code (0 for success, 1 for failure)

        """
        self.logger.info("Validating test structure...")

        # Define test directories to validate
        test_dirs = [
            "tests/unit/core/db",
            "tests/unit/llm",
            "tests/integration/db",
            "tests/integration/llm",
            "tests/unit/core/bookkeeping",
            "tests/integration/ui",
        ]

        # Run pytest on each directory
        for test_dir in test_dirs:
            self._run_tests(test_dir)

        # Report overall status
        if self.success:
            self.logger.info("✅ All tests passed! Test structure is valid.")
            return 0
        else:
            self.logger.error("❌ Some tests failed. Review the output above.")
            return 1

    def _run_tests(self, test_dir: str) -> None:
        """Run pytest on a specific directory.

        Args:
        ----
            test_dir: The directory to run tests in.

        """
        if not Path(test_dir).exists():
            self.logger.warning(f"Test directory {test_dir} does not exist. Skipping.")
            return

        self.logger.info(f"Running tests in {test_dir}...")

        # Run pytest with minimal output
        try:
            result = subprocess.run(
                ["uv", "run", "pytest", test_dir, "-v"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Check if tests passed
            if result.returncode == 0:
                self.logger.info(f"✅ Tests in {test_dir} passed!")
            else:
                self.success = False
                self.logger.error(f"❌ Tests in {test_dir} failed!")
                self.logger.error(f"Output:\n{result.stdout}")
                self.logger.error(f"Errors:\n{result.stderr}")

        except Exception as e:
            self.success = False
            self.logger.exception(f"Error running tests in {test_dir}: {e}")


if __name__ == "__main__":
    validator = TestValidator()
    sys.exit(validator.execute())
