"""Tests for TUI screen components."""
import pytest
from textual.widgets import Button, Label, Static
from dewey.core.tui.app import (
    ModuleScreen, ResearchScreen, DatabaseScreen,
    EnginesScreen, LLMAgentsScreen, MainMenu
)

@pytest.mark.asyncio
async def test_module_screen_initialization(test_screen):
    """Test module screen initialization."""
    assert test_screen.title == "Test Module"
    assert test_screen.status == "Idle"

@pytest.mark.asyncio
async def test_module_screen_bindings(test_screen):
    """Test module screen keyboard bindings."""
    bindings = test_screen.BINDINGS
    binding_keys = {b.key for b in bindings}
    assert "q" in binding_keys  # Quit
    assert "b" in binding_keys  # Back
    assert "r" in binding_keys  # Refresh

@pytest.mark.asyncio
async def test_research_screen_content(app, screen_content):
    """Test research screen content."""
    screen = ResearchScreen("Research")
    await app.push_screen(screen)
    
    content = app.query_one("#content", Static)
    rendered = content.render()
    
    # Check all sections are present
    for section in screen_content["research"]["sections"]:
        assert section in rendered

@pytest.mark.asyncio
async def test_database_screen_content(app, screen_content):
    """Test database screen content."""
    screen = DatabaseScreen("Database")
    await app.push_screen(screen)
    
    content = app.query_one("#content", Static)
    rendered = content.render()
    
    for section in screen_content["database"]["sections"]:
        assert section in rendered

@pytest.mark.asyncio
async def test_engines_screen_content(app, screen_content):
    """Test engines screen content."""
    screen = EnginesScreen("Engines")
    await app.push_screen(screen)
    
    content = app.query_one("#content", Static)
    rendered = content.render()
    
    for section in screen_content["engines"]["sections"]:
        assert section in rendered

@pytest.mark.asyncio
async def test_llm_agents_screen_content(app, screen_content):
    """Test LLM agents screen content."""
    screen = LLMAgentsScreen("LLM Agents")
    await app.push_screen(screen)
    
    content = app.query_one("#content", Static)
    rendered = content.render()
    
    for section in screen_content["llm_agents"]["sections"]:
        assert section in rendered

@pytest.mark.asyncio
async def test_main_menu_buttons(app, button_map):
    """Test main menu button functionality."""
    menu = MainMenu()
    await app.push_screen(menu)
    
    # Check all buttons are present
    buttons = app.query(Button)
    button_ids = {btn.id for btn in buttons}
    
    for btn_id in button_map:
        assert btn_id in button_ids

@pytest.mark.asyncio
async def test_screen_status_updates(app):
    """Test screen status label updates."""
    screen = ModuleScreen("Test")
    await app.push_screen(screen)
    
    status_label = app.query_one("#status", Label)
    
    # Test initial status
    assert "Loading" in status_label.render()
    
    # Test status update
    screen.status = "Processing"
    await app.pause()
    assert "Processing" in status_label.render()
    
    screen.status = "Complete"
    await app.pause()
    assert "Complete" in status_label.render()

@pytest.mark.asyncio
async def test_screen_refresh(app):
    """Test screen refresh functionality."""
    screen = ResearchScreen("Research")
    await app.push_screen(screen)
    
    content = app.query_one("#content", Static)
    initial_content = content.render()
    
    # Simulate refresh
    await app.press("r")
    await app.pause()
    
    refreshed_content = content.render()
    assert initial_content == refreshed_content

@pytest.mark.asyncio
async def test_screen_navigation(app, pilot):
    """Test navigation between screens."""
    # Start at main menu
    menu = MainMenu()
    await app.push_screen(menu)
    
    # Navigate to Research screen
    await pilot.click(Button(id="research"))
    assert isinstance(app.screen, ResearchScreen)
    
    # Go back to main menu
    await pilot.press("b")
    assert isinstance(app.screen, MainMenu)

@pytest.mark.asyncio
async def test_screen_styling(app, css_rules):
    """Test screen component styling."""
    screen = ResearchScreen("Research")
    await app.push_screen(screen)
    
    # Test content container styling
    content = app.query_one("#content")
    content_style = app.get_component_rich_style(content)
    assert css_rules["content"]["padding"] in content_style.css
    
    # Test module title styling
    title = app.query_one("#module-title")
    assert "text-align: center" in app.get_component_rich_style(title).css

@pytest.mark.asyncio
async def test_screen_error_handling(app):
    """Test screen error handling."""
    screen = ModuleScreen("Test")
    await app.push_screen(screen)
    
    # Test status update with error
    screen.status = "Error: Failed to load content"
    await app.pause()
    
    status_label = app.query_one("#status", Label)
    assert "Error" in status_label.render()

@pytest.mark.asyncio
async def test_screen_content_formatting(app):
    """Test screen content formatting."""
    screen = ResearchScreen("Research")
    await app.push_screen(screen)
    
    content = app.query_one("#content", Static)
    rendered = content.render()
    
    # Check formatting markers
    assert "[bold]" in rendered
    assert "•" in rendered  # Bullet points
    assert "-" in rendered  # Sub-items 