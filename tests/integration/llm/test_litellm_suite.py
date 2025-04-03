"""Test suite for LiteLLM tests.

This module runs all LiteLLM tests as a suite.
"""

import os
import sys
import unittest

# Add the project root to the path to make imports work
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

# Import test classes - using absolute imports
from tests.prod.llm.test_exceptions import TestLLMExceptions
from tests.prod.llm.test_litellm_client import TestLiteLLMClient
from tests.prod.llm.test_litellm_integration import TestLiteLLMIntegration
from tests.prod.llm.test_litellm_utils import TestLiteLLMUtils


def create_test_suite():
    """Create a test suite containing all LiteLLM tests."""
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases from each test module
    test_suite.addTest(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestLiteLLMClient)
    )
    test_suite.addTest(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestLiteLLMUtils)
    )
    test_suite.addTest(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestLLMExceptions)
    )
    test_suite.addTest(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestLiteLLMIntegration)
    )

    return test_suite


if __name__ == "__main__":
    # Create the test suite
    suite = create_test_suite()

    # Run the test suite
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print(f"\nRan {result.testsRun} tests")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    # Set exit code based on test results
    import sys

    sys.exit(len(result.failures) + len(result.errors))
