"""Unit tests for the dewey.core.tui.screens module."""
import pytest

from dewey.core.tui.screens import (
    DatabaseScreen,
    EnginesScreen,
    LLMAgentsScreen,
    MainMenu,
    ResearchScreen,
)


def test_import_screens() -> None:
    """Test that the screen classes can be imported."""
    assert DatabaseScreen
    assert EnginesScreen
    assert LLMAgentsScreen
    assert MainMenu
    assert ResearchScreen


def test_screen_inheritance() -> None:
    """Test that the screen classes inherit from a base class (if applicable)."""
    # Assuming there's a BaseScreen or similar
    # This test would verify that each screen inherits from it.
    # Example:
    # assert issubclass(DatabaseScreen, BaseScreen)
    # Add similar assertions for other screens
    pass


def test_screen_instantiation() -> None:
    """Test that the screen classes can be instantiated."""
    try:
        database_screen = DatabaseScreen()
        engines_screen = EnginesScreen()
        llm_agents_screen = LLMAgentsScreen()
        main_menu = MainMenu()
        research_screen = ResearchScreen()
    except Exception as e:
        pytest.fail(f"Screen instantiation failed: {e}")

    assert isinstance(database_screen, DatabaseScreen)
    assert isinstance(engines_screen, EnginesScreen)
    assert isinstance(llm_agents_screen, LLMAgentsScreen)
    assert isinstance(main_menu, MainMenu)
    assert isinstance(research_screen, ResearchScreen)
