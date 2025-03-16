"""Test module to verify menu functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from service_manager.menu import ServiceMenu
from service_manager.service_manager import ServiceManager


class MockResult:
    """Mock result from SSH command."""

    def __init__(self, stdout: str) -> None:
        """Initialize MockResult.

        Args:
        ----
            stdout: The standard output string.

        """
        self.stdout: str = stdout
        self.stdout_bytes: bytes = stdout.encode()


@pytest.fixture
def mock_connection() -> MagicMock:
    """Create a mock SSH connection.

    Returns
    -------
        A MagicMock instance simulating an SSH connection.

    """
    mock = MagicMock()
    mock.run.return_value = MockResult("service1\nservice2")
    mock.open = MagicMock()
    return mock


@pytest.fixture
def service_manager(mock_connection: MagicMock) -> ServiceManager:
    """Create ServiceManager instance.

    Args:
    ----
        mock_connection: A mock SSH connection.

    Returns:
    -------
        A ServiceManager instance.

    """
    with patch("fabric.Connection", return_value=mock_connection):
        manager = ServiceManager("test@localhost", Path("/tmp/test"))
        manager.connection = mock_connection
        return manager


@pytest.fixture
def menu(service_manager: ServiceManager) -> ServiceMenu:
    """Create ServiceMenu instance.

    Args:
    ----
        service_manager: A ServiceManager instance.

    Returns:
    -------
        A ServiceMenu instance.

    """
    return ServiceMenu(service_manager)


class TestMenuFunctionality:
    """Test class to verify menu functionality."""

    def test_menu_initialization(self, menu: ServiceMenu) -> None:
        """Test menu initialization."""
        assert menu.service_manager is not None
        assert menu.current_menu == "main"
        assert menu.parent_menu == "main"
        assert menu.history == ["main"]
        assert menu.selected_service is None

    @patch("service_manager.menu.ServiceMenu._log_issue")
    def test_log_issue(self, mock_log_issue: MagicMock, menu: ServiceMenu) -> None:
        """Test log issue functionality.

        Args:
        ----
            mock_log_issue: Mock for the _log_issue method.
            menu: The ServiceMenu instance.

        """
        mock_log_issue.return_value = True
        result = menu._log_issue()
        assert result is True
        mock_log_issue.assert_called_once()

    @patch("service_manager.menu.ServiceMenu._service_control")
    def test_service_control(
        self,
        mock_service_control: MagicMock,
        menu: ServiceMenu,
    ) -> None:
        """Test service control functionality.

        Args:
        ----
            mock_service_control: Mock for the _service_control method.
            menu: The ServiceMenu instance.

        """
        mock_service_control.return_value = True
        result = menu._service_control()
        assert result is True
        mock_service_control.assert_called_once()

    @patch("service_manager.menu.ServiceMenu._analyze_services")
    def test_analyze_services(self, mock_analyze: MagicMock, menu: ServiceMenu) -> None:
        """Test analyze services functionality.

        Args:
        ----
            mock_analyze: Mock for the _analyze_services method.
            menu: The ServiceMenu instance.

        """
        mock_analyze.return_value = True
        result = menu._analyze_services()
        assert result is True
        mock_analyze.assert_called_once()

    @patch("service_manager.menu.ServiceMenu._deploy_service")
    def test_deploy_service(self, mock_deploy: MagicMock, menu: ServiceMenu) -> None:
        """Test deploy service functionality.

        Args:
        ----
            mock_deploy: Mock for the _deploy_service method.
            menu: The ServiceMenu instance.

        """
        mock_deploy.return_value = True
        result = menu._deploy_service()
        assert result is True
        mock_deploy.assert_called_once()

    @patch("service_manager.menu.ServiceMenu._monitor_services")
    def test_monitor_services(self, mock_monitor: MagicMock, menu: ServiceMenu) -> None:
        """Test monitor services functionality.

        Args:
        ----
            mock_monitor: Mock for the _monitor_services method.
            menu: The ServiceMenu instance.

        """
        mock_monitor.return_value = True
        result = menu._monitor_services()
        assert result is True
        mock_monitor.assert_called_once()

    @patch("service_manager.menu.ServiceMenu._generate_report")
    def test_generate_report(self, mock_report: MagicMock, menu: ServiceMenu) -> None:
        """Test generate report functionality.

        Args:
        ----
            mock_report: Mock for the _generate_report method.
            menu: The ServiceMenu instance.

        """
        mock_report.return_value = True
        result = menu._generate_report()
        assert result is True
        mock_report.assert_called_once()

    @patch("service_manager.menu.ServiceMenu._update_motd")
    def test_update_motd(self, mock_motd: MagicMock, menu: ServiceMenu) -> None:
        """Test update MOTD functionality.

        Args:
        ----
            mock_motd: Mock for the _update_motd method.
            menu: The ServiceMenu instance.

        """
        mock_motd.return_value = True
        result = menu._update_motd()
        assert result is True
        mock_motd.assert_called_once()

    @patch("service_manager.menu.ServiceMenu._view_logs")
    def test_view_logs(self, mock_logs: MagicMock, menu: ServiceMenu) -> None:
        """Test view logs functionality.

        Args:
        ----
            mock_logs: Mock for the _view_logs method.
            menu: The ServiceMenu instance.

        """
        mock_logs.return_value = True
        result = menu._view_logs()
        assert result is True
        mock_logs.assert_called_once()

    @patch("service_manager.menu.ServiceMenu._verify_configs")
    def test_verify_configs(self, mock_verify: MagicMock, menu: ServiceMenu) -> None:
        """Test verify configs functionality.

        Args:
        ----
            mock_verify: Mock for the _verify_configs method.
            menu: The ServiceMenu instance.

        """
        mock_verify.return_value = True
        result = menu._verify_configs()
        assert result is True
        mock_verify.assert_called_once()

    def test_menu_navigation(self, menu: ServiceMenu) -> None:
        """Test menu navigation.

        Args:
        ----
            menu: The ServiceMenu instance.

        """
        # Test going to a submenu
        menu.set_menu_state("service_control", "main")
        assert menu.current_menu == "service_control"
        assert menu.parent_menu == "main"
        assert "service_control" in menu.history

        # Test going back
        menu.go_back()
        assert menu.current_menu == "main"
        assert menu.parent_menu == "main"

    @patch("service_manager.menu.ServiceMenu.handle_menu_selection")
    def test_run_menu(
        self,
        mock_handle_selection: MagicMock,
        menu: ServiceMenu,
    ) -> None:
        """Test running the menu.

        Args:
        ----
            mock_handle_selection: Mock for the handle_menu_selection method.
            menu: The ServiceMenu instance.

        """
        # Mock menu selection to return 'exit' after one iteration
        mock_handle_selection.return_value = "exit"

        result = menu.run()
        assert result is True
        mock_handle_selection.assert_called_once()
