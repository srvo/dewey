"""
Production UI tests for the Dewey application

These tests are designed to work with the actual database and connections,
allowing for testing against real data environments.
"""

import sys
import os

# Add the project root to sys.path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
