#!/usr/bin/env python3
"""Test helper utilities for the Dewey project."""

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

from textual.pilot import Pilot

T = TypeVar("T")


async def wait_for_condition(
    condition: Callable[[], bool], timeout: float = 1.0, interval: float = 0.1,
) -> None:
    """
    Wait for a condition to become true.

    Args:
    ----
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds

    Raises:
    ------
        TimeoutError: If condition is not met within timeout

    """
    start_time = asyncio.get_event_loop().time()
    while not condition():
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError("Condition not met within timeout")
        await asyncio.sleep(interval)


async def wait_for_worker(
    pilot: Pilot[Any], worker_id: str, timeout: float = 5.0,
) -> None:
    """
    Wait for a worker to complete.

    Args:
    ----
        pilot: Textual pilot instance
        worker_id: ID of the worker to wait for
        timeout: Maximum time to wait in seconds

    Raises:
    ------
        TimeoutError: If worker does not complete within timeout

    """

    async def check_worker():
        """Function check_worker."""
        workers = pilot.app.query(f"#{worker_id}")
        return not workers or not any(w.is_running for w in workers)

    await wait_for_condition(check_worker, timeout=timeout)


async def simulate_file_upload(
    pilot: Pilot[Any], source_path: str, target_db: str,
) -> None:
    """
    Simulate a file upload operation.

    Args:
    ----
        pilot: Textual pilot instance
        source_path: Path to source file/directory
        target_db: Target database name

    """
    # Navigate to upload screen
    await pilot.press("u")

    # Fill in form
    await pilot.click("#source_dir")
    await pilot.type(source_path)
    await pilot.click("#target_db")
    await pilot.type(target_db)

    # Start upload
    await pilot.click("#upload_btn")

    # Wait for upload to complete
    await wait_for_worker(pilot, "upload_worker")


async def simulate_table_analysis(pilot: Pilot[Any], database: str) -> None:
    """
    Simulate a table analysis operation.

    Args:
    ----
        pilot: Textual pilot instance
        database: Database to analyze

    """
    # Navigate to analysis screen
    await pilot.press("a")

    # Fill in form
    await pilot.click("#database")
    await pilot.type(database)

    # Start analysis
    await pilot.click("#analyze_btn")

    # Wait for analysis to complete
    await wait_for_worker(pilot, "analysis_worker")


async def simulate_config_save(pilot: Pilot[Any], token: str, default_db: str) -> None:
    """
    Simulate saving configuration.

    Args:
    ----
        pilot: Textual pilot instance
        token: MotherDuck token
        default_db: Default database name

    """
    # Navigate to config screen
    await pilot.press("c")

    # Fill in form
    await pilot.click("#token")
    await pilot.type(token)
    await pilot.click("#default_db")
    await pilot.type(default_db)

    # Save config
    await pilot.click("#save_btn")

    # Wait for save to complete
    await wait_for_worker(pilot, "config_worker")
