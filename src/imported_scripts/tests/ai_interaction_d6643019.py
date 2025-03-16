#!/usr/bin/env python
"""Test script for AI interaction."""

import asyncio
import os
import sys

import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from syzygy.ai.test_agent import test_philosophical_discussion


async def main() -> None:
    """Run the AI test."""
    try:
        await test_philosophical_discussion()
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
