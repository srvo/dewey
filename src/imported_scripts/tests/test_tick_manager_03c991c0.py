import pytest
from port5.tick_manager import TickManagerApp


@pytest.mark.asyncio
async def test_ui_initialization() -> None:
    """Test that the UI initializes correctly."""
    app = TickManagerApp()
    app = await app.run_test()
    assert app.query_one("#title").text == "Tick Manager"
    assert app.query_one("#companies_table") is not None
    assert app.query_one("#tick_container") is not None
    await app.unmount()


@pytest.mark.asyncio
async def test_table_loading() -> None:
    """Test that the companies table loads data."""
    app = TickManagerApp()
    app = await app.run_test()
    await app.load_companies()
    table = app.query_one("#companies_table")
    assert len(table.rows) > 0
    assert table.columns[0].label == "Ticker"
    assert table.columns[1].label == "Company"
    assert table.columns[2].label == "Tick"
    await app.unmount()


def test_tick_validation() -> None:
    """Test tick value validation."""
    app = TickManagerApp()

    # Test valid values
    assert app.validate_tick_value("50") == 50
    assert app.validate_tick_value("-50") == -50

    # Test invalid values
    with pytest.raises(ValueError):
        app.validate_tick_value("101")
    with pytest.raises(ValueError):
        app.validate_tick_value("abc")


@pytest.mark.asyncio
async def test_tick_edit_screen() -> None:
    """Test the tick edit screen functionality."""
    app = TickManagerApp()
    app = await app.run_test()

    # Select first company
    table = app.query_one("#companies_table")
    table.cursor_row = 0
    await app.on_data_table_row_selected(table)

    # Open edit screen
    await app.run_action("show_tick_edit_screen", 1)
    edit_screen = app.screen_stack[-1]

    # Verify screen content
    assert edit_screen.query_one("#new_tick_input").value == "1"
    assert "Edit Tick" in edit_screen.query_one("Label").text

    # Test save action
    edit_screen.query_one("#new_tick_input").value = "50"
    await edit_screen.run_action("action_save")
    assert len(app.screen_stack) == 1  # Should return to main screen
    await app.unmount()


@pytest.mark.asyncio
async def test_button_interactions() -> None:
    """Test button interactions."""
    app = TickManagerApp()
    app = await app.run_test()

    # Test increase button
    increase_button = app.query_one("#increase_tick")
    assert increase_button.id == "increase_tick"

    # Test decrease button
    decrease_button = app.query_one("#decrease_tick")
    assert decrease_button.id == "decrease_tick"
    await app.unmount()
