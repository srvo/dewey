
# Refactored from: test_ui
# Date: 2025-03-16T16:19:11.365987
# Refactor Version: 1.0
"""Test module for the Textual UI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from service_manager.service_manager import ServiceManager
from service_manager.ui import IssueScreen, ServiceControlScreen, ServiceManagerApp
from textual.screen import Screen


@pytest.fixture
def mock_connection() -> MagicMock:
    """Create a mock SSH connection.

    Returns
    -------
        MagicMock: A mock SSH connection object.

    """
    mock = MagicMock()
    mock.run.return_value = MagicMock(stdout="service1\nservice2")
    mock.open = MagicMock()
    return mock


@pytest.fixture
def service_manager(mock_connection: MagicMock) -> ServiceManager:
    """Create a ServiceManager instance.

    Args:
    ----
        mock_connection: A mock SSH connection object.

    Returns:
    -------
        ServiceManager: A ServiceManager instance.

    """
    with patch("fabric.Connection", return_value=mock_connection):
        manager = ServiceManager("test@localhost", Path("/tmp/test"))
        manager.connection = mock_connection
        return manager


@pytest.fixture
def app(service_manager: ServiceManager) -> ServiceManagerApp:
    """Create a ServiceManagerApp instance.

    Args:
    ----
        service_manager: A ServiceManager instance.

    Returns:
    -------
        ServiceManagerApp: A ServiceManagerApp instance.

    """
    return ServiceManagerApp(service_manager)


async def test_app_title(app: ServiceManagerApp) -> None:
    """Test the application title.

    Args:
    ----
        app: A ServiceManagerApp instance.

    """
    async with app.run_test():
        assert app.title == "Service Manager"


async def test_service_control_screen(
    app: ServiceManagerApp,
    service_manager: ServiceManager,
) -> None:
    """Test the service control screen functionality.

    Args:
    ----
        app: A ServiceManagerApp instance.
        service_manager: A ServiceManager instance.

    """
    # Mock get_services to return test data
    service_manager.get_services.return_value = [
        MagicMock(name="service1", containers=[]),
        MagicMock(name="service2", containers=["container1"]),
    ]

    async with app.run_test() as pilot:
        # Navigate to service control screen
        await pilot.press("s")

        # Check if services are listed
        service_list = app.query_one("ServiceList")
        assert len(service_list.services) == 2

        # Select first service
        await pilot.click("ServiceItem")

        # Try to start the service
        await pilot.click("#start")

        # Verify service control was called
        service_manager.control_service.assert_called_once_with("service1", "start")


async def test_issue_screen(
    app: ServiceManagerApp,
    service_manager: ServiceManager,
) -> None:
    """Test the issue screen functionality.

    Args:
    ----
        app: A ServiceManagerApp instance.
        service_manager: A ServiceManager instance.

    """
    # Mock GitHub integration
    service_manager.github = MagicMock()
    service_manager.github.create_github_issue.return_value = (
        "https://github.com/test/test/issues/1"
    )

    async with app.run_test() as pilot:
        # Navigate to issue screen
        await pilot.press("i")

        # Enter issue details
        await pilot.click("#title")
        await pilot.write("Test Issue")
        await pilot.click("#description")
        await pilot.write("Test Description")

        # Submit the issue
        await pilot.click("#submit")

        # Verify issue creation was called
        service_manager.github.create_github_issue.assert_called_once_with(
            None,
            "Test Issue",
            "Test Description",
            {},
        )


async def test_app_navigation(app: ServiceManagerApp) -> None:
    """Test the application navigation.

    Args:
    ----
        app: A ServiceManagerApp instance.

    """
    async with app.run_test() as pilot:
        # Initial screen
        assert isinstance(app.screen, Screen)

        # Navigate to services screen
        await pilot.press("s")
        assert isinstance(app.screen, ServiceControlScreen)

        # Go back
        await pilot.press("escape")
        assert isinstance(app.screen, Screen)

        # Navigate to issue screen
        await pilot.press("i")
        assert isinstance(app.screen, IssueScreen)

        # Go back
        await pilot.press("escape")
        assert isinstance(app.screen, Screen)


async def test_service_list_refresh(
    app: ServiceManagerApp,
    service_manager: ServiceManager,
) -> None:
    """Test the service list refresh functionality.

    Args:
    ----
        app: A ServiceManagerApp instance.
        service_manager: A ServiceManager instance.

    """
    # Mock get_services to return different data on each call
    service_manager.get_services.side_effect = [
        [MagicMock(name="service1", containers=[])],
        [MagicMock(name="service1", containers=["container1"])],
    ]

    async with app.run_test() as pilot:
        # Navigate to service control screen
        await pilot.press("s")

        # Check initial status
        service_list = app.query_one("ServiceList")
        assert service_list.services[0]["status"] == "stopped"

        # Refresh
        await pilot.press("r")

        # Check updated status
        assert service_list.services[0]["status"] == "running"


async def test_error_handling(
    app: ServiceManagerApp,
    service_manager: ServiceManager,
) -> None:
    """Test error handling within the application.

    Args:
    ----
        app: A ServiceManagerApp instance.
        service_manager: A ServiceManager instance.

    """
    # Mock service control to fail
    service_manager.control_service.return_value = False

    async with app.run_test() as pilot:
        # Navigate to service control screen
        await pilot.press("s")

        # Select service and try to start it
        await pilot.click("ServiceItem")
        await pilot.click("#start")

        # Verify error notification
        notifications = app.query("Notification")
        assert any("Failed to start service" in n.message for n in notifications)
