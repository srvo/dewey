from unittest.mock import MagicMock, patch

import pytest
from port5.tick_manager import (
    TickEditScreen,
    TickManagerApp,
    cleanup_tick_history,
    validate_tick_history_data,
)
from textual.widgets import Button


@pytest.fixture
def mock_db():
    """Fixture providing a mock database connection."""
    return MagicMock()


@pytest.fixture
def app_instance(mock_db):
    """Fixture providing a TickManagerApp instance with a mock database."""
    app = TickManagerApp()
    app.md_conn = mock_db
    return app


def test_validate_tick_value_valid() -> None:
    """Test valid tick values."""
    app = TickManagerApp()
    assert app.validate_tick_value("50") == 50
    assert app.validate_tick_value("-100") == -100
    assert app.validate_tick_value("0") == 0


def test_validate_tick_value_invalid() -> None:
    """Test invalid tick values."""
    app = TickManagerApp()
    with pytest.raises(ValueError, match="Tick value must be between -100 and 100"):
        app.validate_tick_value("150")
    with pytest.raises(ValueError, match="Tick value must be between -100 and 100"):
        app.validate_tick_value("-150")
    with pytest.raises(ValueError):
        app.validate_tick_value("abc")


def test_load_companies(mock_db, app_instance) -> None:
    """Test loading companies from database."""
    # Mock database response
    mock_db.execute.return_value.fetchall.return_value = [
        ("AAPL", "Apple Inc.", 10),
        ("GOOGL", "Alphabet Inc.", 20),
    ]

    app_instance.load_companies()
    table = app_instance.query_one("#companies_table")

    # Verify table is populated correctly
    assert len(table.rows) == 2
    assert table.get_row_at(0) == ("AAPL", "Apple Inc.", "10")
    assert table.get_row_at(1) == ("GOOGL", "Alphabet Inc.", "20")


def test_save_tick_update_success(mock_db, app_instance) -> None:
    """Test successful tick update."""
    # Mock database responses
    mock_db.execute.return_value.fetchone.return_value = (10,)

    app_instance.save_tick_update("AAPL", "15", "Test note")

    # Verify database operations were called
    mock_db.execute.assert_any_call(
        "UPDATE main.current_universe SET tick = ? WHERE ticker = ?",
        [15, "AAPL"],
    )
    mock_db.execute.assert_any_call(
        "INSERT INTO main.tick_history (ticker, old_tick, new_tick, note, date) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
        ["AAPL", 10, 15, "Test note"],
    )


def test_tick_edit_screen_validation() -> None:
    """Test tick edit screen validation."""
    screen = TickEditScreen(
        ticker="AAPL",
        company_name="Apple Inc.",
        current_tick="10",
        last_note="Test note",
    )

    # Test valid input
    screen.query_one("#new_tick_input").value = "15"
    screen.query_one("#note_input").text = "Updated note"
    screen.action_save()

    # Test invalid input
    screen.query_one("#new_tick_input").value = "invalid"
    with pytest.raises(ValueError):
        screen.action_save()


def test_validate_tick_history_data_valid(mock_db) -> None:
    """Test tick history validation with valid data."""
    mock_db.execute.return_value.fetchone.side_effect = [
        (100,),  # total_records
        (0,),  # invalid_ticks
        (0,),  # duplicate_entries
    ]

    is_valid, stats = validate_tick_history_data(mock_db)
    assert is_valid is True
    assert stats == {"total_records": 100, "invalid_ticks": 0, "duplicate_entries": 0}


def test_cleanup_tick_history_success(mock_db) -> None:
    """Test tick history cleanup."""
    result = cleanup_tick_history(mock_db)
    assert result is True
    assert mock_db.execute.call_count == 2  # Should call DELETE and cleanup queries


def test_setup_database_failure(mock_db) -> None:
    """Test database setup failure handling."""
    app = TickManagerApp()
    with patch("duckdb.connect", side_effect=Exception("Connection failed")):
        with pytest.raises(
            RuntimeError,
            match="Failed to connect to database after 3 attempts",
        ):
            app.setup_database()


def test_on_button_pressed_increase_tick(app_instance) -> None:
    """Test increase tick button press."""
    # Set up selected company
    app_instance.selected_company = ["AAPL", "Apple Inc.", "10"]

    # Simulate button press
    button = Button(id="increase_tick")
    app_instance.on_button_pressed(Button.Pressed(button))

    # Verify edit screen was pushed
    assert len(app_instance.screen_stack) == 2


def test_on_button_pressed_no_selection(app_instance) -> None:
    """Test button press with no company selected."""
    app_instance.selected_company = None
    button = Button(id="increase_tick")
    app_instance.on_button_pressed(Button.Pressed(button))

    # Verify notification was shown
    assert app_instance.notifications == ["Please select a company first"]
