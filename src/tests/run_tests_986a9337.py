#!/usr/bin/env python3
"""Test runner for email sync service tests.
Executes all unit and integration tests and generates a report.
"""
import sys
import unittest
from pathlib import Path

# Add project root and test directory to path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))  # Add project root
sys.path.append(str(current_dir))  # Add tests directory

# Import test configuration
from config import cleanup_test_environment, setup_test_environment


def run_tests():
    """Discover and run all tests, generating a report."""
    # Set up test environment
    setup_test_environment()

    # Discover and run all tests
    test_loader = unittest.TestLoader()

    # Unit tests - will run even if API is not available
    unit_tests = test_loader.discover("unit", pattern="test_*.py")
    unit_result = unittest.TextTestRunner(verbosity=2).run(unit_tests)

    # Integration tests - some may be skipped if modules are not available
    integration_tests = test_loader.discover("integration", pattern="test_*.py")
    integration_result = unittest.TextTestRunner(verbosity=2).run(integration_tests)

    # Clean up test environment
    cleanup_test_environment()

    # Report results
    unit_result.testsRun + integration_result.testsRun
    total_errors = len(unit_result.errors) + len(integration_result.errors)
    total_failures = len(unit_result.failures) + len(integration_result.failures)
    len(unit_result.skipped) + len(integration_result.skipped)

    # Return success if no errors or failures
    return total_errors == 0 and total_failures == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
