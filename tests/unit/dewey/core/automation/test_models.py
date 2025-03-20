"""Tests for dewey.core.automation.models."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from typing import Any, Dict, List, Optional

from dewey.core.automation.models import Script, Service
from dewey.core.base_script import BaseScript


class TestScript:
    """Tests for the Script class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript."""
        mock_script = MagicMock(spec=BaseScript)
        mock_script.config = {}
        mock_script.logger = MagicMock()
        return mock_script

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_script_initialization(self, mock_init: MagicMock, mock_base_script: MagicMock) -> None:
        """Test that a Script object can be initialized with valid data."""
        script = Script(
            name="Test Script", description="A test script.", config={"key": "value"}
        )
        assert script.name == "Test Script"
        assert script.description == "A test script."
        assert script.config == {"key": "value"}
        mock_init.assert_called_once_with(config_section="Test Script")

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_script_post_init(self, mock_init: MagicMock) -> None:
        """Test that the __post_init__ method calls the superclass constructor."""
        script = Script(name="Test Script")
        mock_init.assert_called_once_with(config_section="Test Script")

    def test_script_run_raises_not_implemented_error(self) -> None:
        """Test that the run method raises a NotImplementedError."""
        script = Script(name="Test Script")
        with pytest.raises(NotImplementedError):
            script.run()


class TestService:
    """Tests for the Service class."""

    @pytest.fixture
    def service_data(self) -> Dict[str, Any]:
        """Fixture providing sample service data."""
        return {
            "name": "Test Service",
            "path": "/path/to/service",
            "config_path": "/path/to/config",
            "containers": ["container1", "container2"],
            "description": "A test service.",
            "config": {"key": "value"},
            "status": "active",
            "version": "2.0.0",
        }

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript."""
        mock_script = MagicMock(spec=BaseScript)
        mock_script.config = {}
        mock_script.logger = MagicMock()
        return mock_script

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_service_initialization(self, mock_init: MagicMock, service_data: Dict[str, Any]) -> None:
        """Test that a Service object can be initialized with valid data."""
        service = Service(
            name=service_data["name"],
            path=Path(service_data["path"]),
            config_path=Path(service_data["config_path"]),
            containers=service_data["containers"],
            description=service_data["description"],
            config=service_data["config"],
            status=service_data["status"],
            version=service_data["version"],
        )
        assert service.name == service_data["name"]
        assert service.path == Path(service_data["path"])
        assert service.config_path == Path(service_data["config_path"])
        assert service.containers == service_data["containers"]
        assert service.description == service_data["description"]
        assert service.config == service_data["config"]
        assert service.status == service_data["status"]
        assert service.version == service_data["version"]
        mock_init.assert_called_once_with(config_section=service_data["name"])

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_service_to_dict(self, mock_init: MagicMock, service_data: Dict[str, Any]) -> None:
        """Test that the to_dict method returns the correct dictionary representation."""
        service = Service(
            name=service_data["name"],
            path=Path(service_data["path"]),
            config_path=Path(service_data["config_path"]),
            containers=service_data["containers"],
            description=service_data["description"],
            config=service_data["config"],
            status=service_data["status"],
            version=service_data["version"],
        )
        service_dict = service.to_dict()
        assert service_dict["name"] == service_data["name"]
        assert service_dict["path"] == service_data["path"]
        assert service_dict["config_path"] == service_data["config_path"]
        assert service_dict["containers"] == service_data["containers"]
        assert service_dict["description"] == service_data["description"]
        assert service_dict["config"] == service_data["config"]
        assert service_dict["status"] == service_data["status"]
        assert service_dict["version"] == service_data["version"]

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_service_from_dict(self, mock_init: MagicMock, service_data: Dict[str, Any]) -> None:
        """Test that the from_dict method creates a Service object from a dictionary."""
        with patch("pathlib.Path") as MockPath:
            MockPath.side_effect = lambda x: Path(x)  # Ensure Path objects are created
            service = Service.from_dict(service_data)
            assert service.name == service_data["name"]
            assert service.path == Path(service_data["path"])
            assert service.config_path == Path(service_data["config_path"])
            assert service.containers == service_data["containers"]
            assert service.description == service_data["description"]
            assert service.config == service_data["config"]
            assert service.status == service_data["status"]
            assert service.version == service_data["version"]

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_service_from_dict_with_missing_optional_fields(self, mock_init: MagicMock) -> None:
        """Test that from_dict works correctly when optional fields are missing."""
        data = {
            "name": "Test Service",
            "path": "/path/to/service",
            "config_path": "/path/to/config",
            "containers": ["container1", "container2"],
        }
        with patch("pathlib.Path") as MockPath:
            MockPath.side_effect = lambda x: Path(x)  # Ensure Path objects are created
            service = Service.from_dict(data)
            assert service.name == data["name"]
            assert service.path == Path(data["path"])
            assert service.config_path == Path(data["config_path"])
            assert service.containers == data["containers"]
            assert service.description is None
            assert service.config is None
            assert service.status == "inactive"
            assert service.version == "1.0.0"

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_service_run_raises_not_implemented_error(
        self, mock_init: MagicMock, service_data: Dict[str, Any]
    ) -> None:
        """Test that the run method raises a NotImplementedError."""
        service = Service(
            name=service_data["name"],
            path=Path(service_data["path"]),
            config_path=Path(service_data["config_path"]),
            containers=service_data["containers"],
            description=service_data["description"],
            config=service_data["config"],
            status=service_data["status"],
            version=service_data["version"],
        )
        with pytest.raises(NotImplementedError):
            service.run()

    @patch("dewey.core.base_script.BaseScript.__init__")
    def test_service_initialization_base_script(self, mock_init: MagicMock, service_data: Dict[str, Any]) -> None:
        """Test that the Service object initializes the BaseScript."""
        Service(
            name=service_data["name"],
            path=Path(service_data["path"]),
            config_path=Path(service_data["config_path"]),
            containers=service_data["containers"],
            description=service_data["description"],
            config=service_data["config"],
            status=service_data["status"],
            version=service_data["version"],
        )
        mock_init.assert_called_once_with(config_section=service_data["name"])
