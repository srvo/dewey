#!/usr/bin/env python
"""Test script for triage agent."""

import asyncio
import os
import sys

import django
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# Load environment variables
load_dotenv()

from syzygy.ai.base import SyzygyAgent
from syzygy.ai.workflows.email_triage import process_email_payload


def triage_tests() -> None:
    SyzygyAgent()
    # Example test triage logic
    failed_tests = get_failed_tests()
    for test in failed_tests:
        payload = extract_payload(test)
        process_email_payload(payload)
        # Further triage logic


if __name__ == "__main__":
    asyncio.run(triage_tests())
