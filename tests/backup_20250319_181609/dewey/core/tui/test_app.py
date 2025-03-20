#!/usr/bin/env python3
"""Test suite for the Dewey TUI application."""

import pytest
from textual.pilot import Pilot
from textual.widgets import Button, Input, DataTable, ProgressBar

from dewey.core.tui.app import DeweyTUI
from dewey.core.tui.screens import UploadScreen, AnalysisScreen, ConfigScreen

@pytest.mark.asyncio
async def test_app_navigation(pilot: Pilot[DeweyTUI]):
    """Test navigation between screens."""
    app = pilot.app
    
    # Test initial screen is upload
    assert isinstance(app.screen, UploadScreen)
    
    # Test navigation to analysis screen
    await pilot.press("a")
    assert isinstance(app.screen, AnalysisScreen)
    
    # Test navigation to config screen
    await pilot.press("c")
    assert isinstance(app.screen, ConfigScreen)
    
    # Test navigation back to upload screen
    await pilot.press("u")
    assert isinstance(app.screen, UploadScreen)
    
    # Test escape to go back
    await pilot.press("a")  # Go to analysis
    assert isinstance(app.screen, AnalysisScreen)
    await pilot.press("escape")  # Go back
    assert isinstance(app.screen, UploadScreen)

@pytest.mark.asyncio
async def test_upload_screen(pilot: Pilot[DeweyTUI], tmp_path):
    """Test upload screen functionality."""
    app = pilot.app
    
    # Ensure we're on upload screen
    await pilot.press("u")
    assert isinstance(app.screen, UploadScreen)
    
    # Test input fields
    source_dir_input = app.query_one("#source_dir", Input)
    target_db_input = app.query_one("#target_db", Input)
    
    await pilot.click("#source_dir")
    await pilot.type(str(tmp_path))
    assert source_dir_input.value == str(tmp_path)
    
    await pilot.click("#target_db")
    await pilot.type("test_db")
    assert target_db_input.value == "test_db"
    
    # Test upload button
    upload_btn = app.query_one("#upload_btn", Button)
    assert upload_btn.visible
    
    # Test progress bar and status table exist
    assert app.query_one("#upload_progress", ProgressBar)
    assert app.query_one("#upload_status", DataTable)

@pytest.mark.asyncio
async def test_analysis_screen(pilot: Pilot[DeweyTUI]):
    """Test analysis screen functionality."""
    app = pilot.app
    
    # Navigate to analysis screen
    await pilot.press("a")
    assert isinstance(app.screen, AnalysisScreen)
    
    # Test database input
    db_input = app.query_one("#database", Input)
    await pilot.click("#database")
    await pilot.type("test_db")
    assert db_input.value == "test_db"
    
    # Test analyze button
    analyze_btn = app.query_one("#analyze_btn", Button)
    assert analyze_btn.visible
    
    # Test progress bar and results table exist
    assert app.query_one("#analysis_progress", ProgressBar)
    assert app.query_one("#analysis_results", DataTable)

@pytest.mark.asyncio
async def test_config_screen(pilot: Pilot[DeweyTUI]):
    """Test configuration screen functionality."""
    app = pilot.app
    
    # Navigate to config screen
    await pilot.press("c")
    assert isinstance(app.screen, ConfigScreen)
    
    # Test input fields
    token_input = app.query_one("#token", Input)
    db_input = app.query_one("#default_db", Input)
    
    await pilot.click("#token")
    await pilot.type("test_token")
    assert token_input.value == "test_token"
    
    await pilot.click("#default_db")
    await pilot.type("default_db")
    assert db_input.value == "default_db"
    
    # Test save button
    save_btn = app.query_one("#save_btn", Button)
    assert save_btn.visible

def test_app_snapshot(snap_compare):
    """Test application appearance using snapshots."""
    # Test initial upload screen
    assert snap_compare("dewey/core/tui/app.py")
    
    # Test analysis screen
    assert snap_compare("dewey/core/tui/app.py", press=["a"])
    
    # Test config screen
    assert snap_compare("dewey/core/tui/app.py", press=["c"])
    
    # Test filled upload screen
    assert snap_compare(
        "dewey/core/tui/app.py",
        press=["u"],
        run_before=lambda pilot: setattr(pilot.app.query_one("#source_dir"), "value", "/test/path")
    )

@pytest.mark.asyncio
async def test_worker_messages(pilot: Pilot[DeweyTUI]):
    """Test worker message handling."""
    app = pilot.app
    
    # Test upload progress message
    await pilot.press("u")
    screen = app.screen
    progress_bar = screen.query_one("#upload_progress", ProgressBar)
    status_table = screen.query_one("#upload_status", DataTable)
    
    # Simulate upload progress
    screen.on_upload_worker_upload_progress(
        screen.UploadWorker.UploadProgress(
            file="test.csv",
            status="uploading",
            progress=0.5
        )
    )
    assert progress_bar.progress == 0.5
    assert "test.csv" in status_table.get_row_at(0)
    
    # Test analysis progress message
    await pilot.press("a")
    screen = app.screen
    progress_bar = screen.query_one("#analysis_progress", ProgressBar)
    results_table = screen.query_one("#analysis_results", DataTable)
    
    # Simulate analysis progress
    screen.on_analysis_worker_analysis_progress(
        screen.AnalysisWorker.AnalysisProgress(
            total=10,
            current=5,
            table="test_table"
        )
    )
    assert progress_bar.progress == 0.5
    assert "test_table" in results_table.get_row_at(0)

@pytest.fixture
async def pilot():
    """Fixture for creating a Textual pilot."""
    app = DeweyTUI()
    async with app.run_test() as pilot:
        yield pilot 