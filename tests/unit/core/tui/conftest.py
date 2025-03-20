"""Test fixtures for TUI testing."""

import pytest
from dewey.core.tui.app import DeweyTUI, ModuleScreen


@pytest.fixture
async def app():
    """Provide a test TUI application instance."""
    app = DeweyTUI()
    async with app.run_test() as pilot:
        yield pilot.app


@pytest.fixture
async def pilot():
    """Provide a test pilot instance."""
    app = DeweyTUI()
    async with app.run_test() as pilot:
        yield pilot


@pytest.fixture
def test_screen():
    """Provide a test module screen instance."""
    return ModuleScreen("Test Module")


@pytest.fixture
def screen_content():
    """Provide test content for screens."""
    return {
        "research": {
            "title": "Research Module",
            "sections": [
                "Financial Analysis",
                "Ethical Analysis",
                "Research Workflows",
            ],
        },
        "database": {
            "title": "Database Module",
            "sections": ["Schema Management", "Data Operations"],
        },
        "engines": {
            "title": "Engines Module",
            "sections": ["Research Engines", "Analysis Engines", "Data Processing"],
        },
        "llm_agents": {
            "title": "LLM Agents",
            "sections": ["RAG Agent", "Ethical Analysis Agent", "Research Agent"],
        },
    }


@pytest.fixture
def button_map():
    """Provide a mapping of button IDs to screen classes."""
    return {
        "research": "ResearchScreen",
        "database": "DatabaseScreen",
        "engines": "EnginesScreen",
        "llm-agents": "LLMAgentsScreen",
    }


@pytest.fixture
def css_rules():
    """Provide expected CSS rules for components."""
    return {
        "menu": {"width": "80%", "border": "solid green", "padding": "1"},
        "button": {"width": "20", "margin": "1 2"},
        "content": {"padding": "1"},
    }
