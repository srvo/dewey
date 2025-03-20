"""Unit tests for the dewey.core.tui.app module."""

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from textual.app import App
from textual.widgets import Button, Static

from dewey.core.base_script import BaseScript
from dewey.core.tui.app import (
    DatabaseScreen,
    DeweyTUI,
    EnginesScreen,
    LLMAgentsScreen,
    MainMenu,
    ModuleScreen,
    ResearchScreen,
    TUIApp,
    run,
)


@pytest.fixture
def mock_base_script(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Fixture to mock BaseScript."""
    mock = MagicMock(spec=BaseScript)
    monkeypatch.setattr("dewey.core.tui.app.BaseScript", mock)
    return mock


@pytest.fixture
def mock_database_connection(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Fixture to mock DatabaseConnection."""
    mock = MagicMock()
    monkeypatch.setattr("dewey.core.tui.app.DatabaseConnection", mock)
    return mock


@pytest.fixture
def mock_llm_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Fixture to mock LLMClient."""
    mock = MagicMock()
    monkeypatch.setattr("dewey.core.tui.app.LLMClient", mock)
    return mock


class TestModuleScreen:
    """Tests for the ModuleScreen class."""

    @pytest.fixture
    def module_screen(self) -> ModuleScreen:
        """Fixture to create a ModuleScreen instance."""
        return ModuleScreen("Test Module")

    def test_init(self, module_screen: ModuleScreen) -> None:
        """Test the __init__ method."""
        assert module_screen.title == "Test Module"
        assert module_screen.status == "Idle"

    def test_compose(self, module_screen: ModuleScreen) -> None:
        """Test the compose method."""
        result = list(module_screen.compose())
        assert len(result) == 3
        assert isinstance(result[0], Header)
        assert isinstance(result[1], Container)
        assert isinstance(result[2], Footer)

        main_content = result[1].children[0]
        assert isinstance(main_content, Vertical)
        assert len(main_content.children) == 3
        assert isinstance(main_content.children[0], Label)
        assert isinstance(main_content.children[1], Label)
        assert isinstance(main_content.children[2], Static)

    def test_on_mount(self, module_screen: ModuleScreen) -> None:
        """Test the on_mount method."""
        with patch.object(module_screen, "update_content") as mock_update_content:
            module_screen.on_mount()
            mock_update_content.assert_called_once()

    def test_update_content(self, module_screen: ModuleScreen) -> None:
        """Test the update_content method (should be empty in base class)."""
        module_screen.update_content()  # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_action_go_back(self, module_screen: ModuleScreen) -> None:
        """Test the action_go_back method."""
        mock_app = MagicMock()
        module_screen.app = mock_app
        await module_screen.action_go_back()
        mock_app.push_screen.assert_called_once_with("main")

    @pytest.mark.asyncio
    async def test_action_refresh(self, module_screen: ModuleScreen) -> None:
        """Test the action_refresh method."""
        with patch.object(module_screen, "update_content") as mock_update_content:
            await module_screen.action_refresh()
            mock_update_content.assert_called_once()


class TestResearchScreen:
    """Tests for the ResearchScreen class."""

    @pytest.fixture
    def research_screen(self) -> ResearchScreen:
        """Fixture to create a ResearchScreen instance."""
        return ResearchScreen("Research")

    def test_update_content(self, research_screen: ResearchScreen) -> None:
        """Test the update_content method."""
        content = MagicMock()
        research_screen.query_one = MagicMock(return_value=content)
        research_screen.update_content()
        research_screen.query_one.assert_called_once_with("#content", Static)
        content.update.assert_called_once()


class TestDatabaseScreen:
    """Tests for the DatabaseScreen class."""

    @pytest.fixture
    def database_screen(self) -> DatabaseScreen:
        """Fixture to create a DatabaseScreen instance."""
        return DatabaseScreen("Database")

    def test_update_content(self, database_screen: DatabaseScreen) -> None:
        """Test the update_content method."""
        content = MagicMock()
        database_screen.query_one = MagicMock(return_value=content)
        database_screen.update_content()
        database_screen.query_one.assert_called_once_with("#content", Static)
        content.update.assert_called_once()


class TestLLMAgentsScreen:
    """Tests for the LLMAgentsScreen class."""

    @pytest.fixture
    def llm_agents_screen(self) -> LLMAgentsScreen:
        """Fixture to create an LLMAgentsScreen instance."""
        return LLMAgentsScreen("LLM Agents")

    def test_update_content(self, llm_agents_screen: LLMAgentsScreen) -> None:
        """Test the update_content method."""
        content = MagicMock()
        llm_agents_screen.query_one = MagicMock(return_value=content)
        llm_agents_screen.update_content()
        llm_agents_screen.query_one.assert_called_once_with("#content", Static)
        content.update.assert_called_once()


class TestEnginesScreen:
    """Tests for the EnginesScreen class."""

    @pytest.fixture
    def engines_screen(self) -> EnginesScreen:
        """Fixture to create an EnginesScreen instance."""
        return EnginesScreen("Engines")

    def test_update_content(self, engines_screen: EnginesScreen) -> None:
        """Test the update_content method."""
        content = MagicMock()
        engines_screen.query_one = MagicMock(return_value=content)
        engines_screen.update_content()
        engines_screen.query_one.assert_called_once_with("#content", Static)
        content.update.assert_called_once()


class TestMainMenu:
    """Tests for the MainMenu class."""

    @pytest.fixture
    def main_menu(self) -> MainMenu:
        """Fixture to create a MainMenu instance."""
        return MainMenu()

    def test_compose(self, main_menu: MainMenu) -> None:
        """Test the compose method."""
        result = list(main_menu.compose())
        assert len(result) == 3
        assert isinstance(result[0], Header)
        assert isinstance(result[1], Container)
        assert isinstance(result[2], Footer)

        menu = result[1].children[0]
        assert isinstance(menu, Vertical)
        assert len(menu.children) == 6
        assert isinstance(menu.children[0], Label)
        assert isinstance(menu.children[1], Horizontal)
        assert isinstance(menu.children[2], Horizontal)
        assert isinstance(menu.children[3], Horizontal)
        assert isinstance(menu.children[4], Label)
        assert isinstance(menu.children[5], Horizontal)

    @pytest.mark.asyncio
    async def test_on_button_pressed(self, main_menu: MainMenu) -> None:
        """Test the on_button_pressed method."""
        mock_app = MagicMock()
        main_menu.app = mock_app
        mock_button = MagicMock(id="research")
        event = MagicMock(button=mock_button)
        await main_menu.on_button_pressed(event)
        mock_app.push_screen.assert_called_once()
        args, _ = mock_app.push_screen.call_args
        assert isinstance(args[0], ResearchScreen)

        mock_button = MagicMock(id="database")
        event = MagicMock(button=mock_button)
        await main_menu.on_button_pressed(event)
        assert mock_app.push_screen.call_count == 2
        args, _ = mock_app.push_screen.call_args
        assert isinstance(args[0], DatabaseScreen)

        mock_button = MagicMock(id="engines")
        event = MagicMock(button=mock_button)
        await main_menu.on_button_pressed(event)
        assert mock_app.push_screen.call_count == 3
        args, _ = mock_app.push_screen.call_args
        assert isinstance(args[0], EnginesScreen)

        mock_button = MagicMock(id="llm-agents")
        event = MagicMock(button=mock_button)
        await main_menu.on_button_pressed(event)
        assert mock_app.push_screen.call_count == 4
        args, _ = mock_app.push_screen.call_args
        assert isinstance(args[0], LLMAgentsScreen)

        mock_button = MagicMock(id="unknown")
        event = MagicMock(button=mock_button)
        await main_menu.on_button_pressed(event)
        assert mock_app.push_screen.call_count == 4  # No new screen pushed


class TestDeweyTUI:
    """Tests for the DeweyTUI class."""

    @pytest.fixture
    def dewey_tui(self) -> DeweyTUI:
        """Fixture to create a DeweyTUI instance."""
        return DeweyTUI()

    def test_on_mount(self, dewey_tui: DeweyTUI) -> None:
        """Test the on_mount method."""
        mock_app = MagicMock()
        dewey_tui.app = mock_app
        dewey_tui.on_mount()
        mock_app.push_screen.assert_called_once_with("main")


class TestTUIApp:
    """Tests for the TUIApp class."""

    @pytest.fixture
    def tui_app(self) -> TUIApp:
        """Fixture to create a TUIApp instance."""
        return TUIApp()

    @patch("dewey.core.tui.app.DeweyTUI.run")
    def test_run(self, mock_run: MagicMock, tui_app: TUIApp) -> None:
        """Test the run method."""
        tui_app.run()
        mock_run.assert_called_once()

    def test_setup_argparse(self, tui_app: TUIApp) -> None:
        """Test the setup_argparse method."""
        parser = tui_app.setup_argparse()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_cleanup(self, tui_app: TUIApp) -> None:
        """Test the _cleanup method."""
        with patch.object(tui_app, "_cleanup") as mock_cleanup:
            tui_app.execute()
            mock_cleanup.assert_called_once()

    @patch("dewey.core.tui.app.TUIApp.execute")
    def test_run_function(self, mock_execute: MagicMock) -> None:
        """Test the run function."""
        run()
        mock_execute.assert_called_once()

    @patch("dewey.core.tui.app.TUIApp.parse_args")
    @patch("dewey.core.tui.app.TUIApp.run")
    def test_execute_success(self, mock_run: MagicMock, mock_parse_args: MagicMock, tui_app: TUIApp, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method with successful execution."""
        mock_parse_args.return_value = argparse.Namespace()
        with caplog.at_level(logging.INFO):
            tui_app.execute()
        assert "Starting execution of DeweyTUI" in caplog.text
        assert "Completed execution of DeweyTUI" in caplog.text
        mock_run.assert_called_once()

    @patch("dewey.core.tui.app.TUIApp.parse_args")
    @patch("dewey.core.tui.app.TUIApp.run", side_effect=KeyboardInterrupt)
    def test_execute_keyboard_interrupt(self, mock_run: MagicMock, mock_parse_args: MagicMock, tui_app: TUIApp, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method with KeyboardInterrupt."""
        mock_parse_args.return_value = argparse.Namespace()
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.WARNING):
                tui_app.execute()
        assert exc_info.value.code == 1
        assert "Script interrupted by user" in caplog.text
        mock_run.assert_called_once()

    @patch("dewey.core.tui.app.TUIApp.parse_args")
    @patch("dewey.core.tui.app.TUIApp.run", side_effect=ValueError("Test Error"))
    def test_execute_exception(self, mock_run: MagicMock, mock_parse_args: MagicMock, tui_app: TUIApp, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method with an exception."""
        mock_parse_args.return_value = argparse.Namespace()
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.ERROR):
                tui_app.execute()
        assert exc_info.value.code == 1
        assert "Error executing script: Test Error" in caplog.text
        mock_run.assert_called_once()
