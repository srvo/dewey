#!/usr/bin/env python3
"""Test suite for TUI workers."""

import pytest
from pathlib import Path
from textual.pilot import Pilot

from dewey.core.tui.app import DeweyTUI
from dewey.core.tui.screens import UploadScreen, AnalysisScreen
from tests.helpers import (
    wait_for_worker,
    simulate_file_upload,
    simulate_table_analysis,
    simulate_config_save,
)


@pytest.mark.asyncio
async def test_upload_worker(pilot: Pilot[DeweyTUI], sample_csv_file: Path):
    """Test the upload worker functionality."""
    app = pilot.app

    # Simulate file upload
    await simulate_file_upload(pilot, str(sample_csv_file.parent), "test_db")

    # Verify progress updates
    screen = app.screen
    progress_bar = screen.query_one("#upload_progress")
    status_table = screen.query_one("#upload_status")

    assert progress_bar.progress > 0
    assert len(status_table.rows) > 0
    assert any(sample_csv_file.name in row for row in status_table.rows)


@pytest.mark.asyncio
async def test_analysis_worker(pilot: Pilot[DeweyTUI]):
    """Test the analysis worker functionality."""
    app = pilot.app

    # Simulate table analysis
    await simulate_table_analysis(pilot, "test_db")

    # Verify progress updates
    screen = app.screen
    progress_bar = screen.query_one("#analysis_progress")
    results_table = screen.query_one("#analysis_results")

    assert progress_bar.progress > 0
    assert len(results_table.rows) > 0


@pytest.mark.asyncio
async def test_config_worker(pilot: Pilot[DeweyTUI], test_config_dir: Path):
    """Test the config worker functionality."""
    app = pilot.app

    # Simulate config save
    await simulate_config_save(pilot, "test_token", "test_db")

    # Verify config file was created
    config_file = test_config_dir / "dewey.yaml"
    assert config_file.exists()

    # Verify config contents
    config_text = config_file.read_text()
    assert "test_token" in config_text
    assert "test_db" in config_text


@pytest.mark.asyncio
async def test_worker_error_handling(pilot: Pilot[DeweyTUI]):
    """Test worker error handling."""
    app = pilot.app

    # Test upload worker error
    await pilot.press("u")
    screen = app.screen

    # Trigger error with invalid path
    await simulate_file_upload(pilot, "/nonexistent/path", "test_db")

    # Verify error is displayed
    status_table = screen.query_one("#upload_status")
    assert any("error" in str(row).lower() for row in status_table.rows)

    # Test analysis worker error
    await pilot.press("a")
    screen = app.screen

    # Trigger error with invalid database
    await simulate_table_analysis(pilot, "nonexistent_db")

    # Verify error is displayed
    results_table = screen.query_one("#analysis_results")
    assert any("error" in str(row).lower() for row in results_table.rows)


@pytest.mark.asyncio
async def test_concurrent_workers(pilot: Pilot[DeweyTUI], sample_csv_file: Path):
    """Test running multiple workers concurrently."""
    app = pilot.app

    # Start upload
    await pilot.press("u")
    await pilot.click("#source_dir")
    await pilot.type(str(sample_csv_file.parent))
    await pilot.click("#target_db")
    await pilot.type("test_db")
    await pilot.click("#upload_btn")

    # Start analysis while upload is running
    await pilot.press("a")
    await pilot.click("#database")
    await pilot.type("test_db")
    await pilot.click("#analyze_btn")

    # Wait for both workers to complete
    await wait_for_worker(pilot, "upload_worker")
    await wait_for_worker(pilot, "analysis_worker")

    # Verify both operations completed
    upload_screen = app.query_one(UploadScreen)
    analysis_screen = app.query_one(AnalysisScreen)

    assert len(upload_screen.query_one("#upload_status").rows) > 0
    assert len(analysis_screen.query_one("#analysis_results").rows) > 0
