from pathlib import Path
from typing import Any

import pytest
from service_manager.service_manager import Service, ServiceManager


@pytest.fixture
def mock_menu_config() -> dict[str, Any]:
    """Create mock menu configuration."""
    return {
        "title": "Service Manager",
        "theme": {"background": "blue", "foreground": "white", "border": "rounded"},
        "options": [
            {
                "name": "View Services",
                "command": "view",
                "description": "List all services and their status",
            },
            {
                "name": "Deploy Service",
                "command": "deploy",
                "description": "Deploy a new service",
            },
            {
                "name": "Monitor Services",
                "command": "monitor",
                "description": "View service monitoring dashboard",
            },
            {
                "name": "Exit",
                "command": "exit",
                "description": "Exit the service manager",
            },
        ],
    }


@pytest.fixture
def mock_gum_output() -> dict[str, str]:
    """Create mock gum command output."""
    return {
        "choose": "View Services",
        "input": "test-service",
        "confirm": "true",
        "style": "Styled output",
        "spin": "Operation completed",
    }


def test_menu_rendering(
    service_manager: ServiceManager,
    mock_menu_config: dict[str, Any],
) -> None:
    """Test menu rendering functionality."""

    # Mock gum style command
    def mock_run_command(cmd: str) -> str:
        if "gum style" in cmd:
            return mock_menu_config["title"]
        return ""

    service_manager.run_command = mock_run_command  # type: ignore

    # Test menu rendering
    menu_output = service_manager.render_menu(mock_menu_config)
    assert mock_menu_config["title"] in menu_output
    assert all(option["name"] in menu_output for option in mock_menu_config["options"])


def test_menu_navigation(
    service_manager: ServiceManager,
    mock_menu_config: dict[str, Any],
    mock_gum_output: dict[str, str],
) -> None:
    """Test menu navigation functionality."""

    # Mock gum choose command
    def mock_run_command(cmd: str) -> str:
        if "gum choose" in cmd:
            return mock_gum_output["choose"]
        return ""

    service_manager.run_command = mock_run_command  # type: ignore

    # Test menu selection
    selected = service_manager.handle_menu_selection(mock_menu_config["options"])
    assert selected == "view"

    # Test menu navigation history
    history = service_manager.get_menu_history()
    assert len(history) > 0
    assert history[-1] == "view"


def test_submenu_rendering(
    service_manager: ServiceManager,
    mock_menu_config: dict[str, Any],
    mock_gum_output: dict[str, str],
) -> None:
    """Test submenu rendering functionality."""
    submenu_config = {
        "title": "Service Actions",
        "parent": "View Services",
        "options": [
            {
                "name": "Start Service",
                "command": "start",
                "description": "Start the selected service",
            },
            {
                "name": "Stop Service",
                "command": "stop",
                "description": "Stop the selected service",
            },
            {"name": "Back", "command": "back", "description": "Return to main menu"},
        ],
    }

    # Mock gum commands
    def mock_run_command(cmd: str) -> str:
        if "gum style" in cmd:
            return submenu_config["title"]
        if "gum choose" in cmd:
            return "Start Service"
        return ""

    service_manager.run_command = mock_run_command  # type: ignore

    # Test submenu rendering
    submenu_output = service_manager.render_submenu(submenu_config)
    assert submenu_config["title"] in submenu_output
    assert all(option["name"] in submenu_output for option in submenu_config["options"])

    # Test submenu selection
    selected = service_manager.handle_menu_selection(submenu_config["options"])
    assert selected == "start"


def test_menu_input_handling(
    service_manager: ServiceManager,
    mock_gum_output: dict[str, str],
) -> None:
    """Test menu input handling functionality."""

    # Mock gum input command
    def mock_run_command(cmd: str) -> str:
        if "gum input" in cmd:
            return mock_gum_output["input"]
        if "gum confirm" in cmd:
            return mock_gum_output["confirm"]
        return ""

    service_manager.run_command = mock_run_command  # type: ignore

    # Test text input
    service_name = service_manager.get_user_input("Enter service name:")
    assert service_name == "test-service"

    # Test confirmation
    confirmed = service_manager.get_user_confirmation("Proceed with deployment?")
    assert confirmed is True


def test_menu_command_execution(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_gum_output: dict[str, str],
) -> None:
    """Test menu command execution functionality."""
    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock command execution
    def mock_run_command(cmd: str) -> str:
        if "gum spin" in cmd:
            return mock_gum_output["spin"]
        return ""

    service_manager.run_command = mock_run_command  # type: ignore

    # Test command execution with progress indicator
    result = service_manager.execute_menu_command(
        command="deploy",
        service=service,
        message="Deploying service...",
    )
    assert result == mock_gum_output["spin"]


def test_menu_error_handling(
    service_manager: ServiceManager,
    mock_gum_output: dict[str, str],
) -> None:
    """Test menu error handling functionality."""

    # Mock error display
    def mock_run_command(cmd: str) -> str:
        if "gum style" in cmd and "--foreground red" in cmd:
            return "Error: Invalid selection"
        return ""

    service_manager.run_command = mock_run_command  # type: ignore

    # Test error display
    error_message = service_manager.display_error("Invalid selection")
    assert "Error" in error_message
    assert "Invalid selection" in error_message


def test_menu_help_system(
    service_manager: ServiceManager,
    mock_menu_config: dict[str, Any],
    mock_gum_output: dict[str, str],
) -> None:
    """Test menu help system functionality."""

    # Mock help display
    def mock_run_command(cmd: str) -> str:
        if "gum style" in cmd:
            return mock_gum_output["style"]
        return ""

    service_manager.run_command = mock_run_command  # type: ignore

    # Test help content generation
    help_content = service_manager.generate_help_content(mock_menu_config["options"])
    assert any(
        option["description"] in help_content for option in mock_menu_config["options"]
    )

    # Test help display
    help_output = service_manager.display_help()
    assert help_output == mock_gum_output["style"]


def test_menu_state_management(
    service_manager: ServiceManager,
    mock_menu_config: dict[str, Any],
) -> None:
    """Test menu state management functionality."""
    # Test menu state initialization
    service_manager.initialize_menu_state()
    assert service_manager.get_current_menu() == "main"

    # Test menu state transitions
    service_manager.set_menu_state("submenu", "View Services")
    assert service_manager.get_current_menu() == "submenu"
    assert service_manager.get_parent_menu() == "main"

    # Test menu state history
    service_manager.go_back()
    assert service_manager.get_current_menu() == "main"

    # Test menu state reset
    service_manager.reset_menu_state()
    assert service_manager.get_current_menu() == "main"
    assert len(service_manager.get_menu_history()) == 1
