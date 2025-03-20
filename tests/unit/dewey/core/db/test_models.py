"""Unit tests for the dewey.core.db.models module."""

import logging
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from dewey.core.base_script import BaseScript
from dewey.core.db.models import CRMContact, MyScript


def test_crm_contact_creation() -> None:
    """Test successful creation of a CRMContact instance."""
    contact = CRMContact(name="John Doe", email="john.doe@example.com")
    assert contact.name == "John Doe"
    assert contact.email == "john.doe@example.com"
    assert contact.phone is None
    assert contact.company is None
    assert contact.last_contacted is None
    assert contact.notes is None


def test_crm_contact_optional_fields() -> None:
    """Test creation of a CRMContact with all optional fields provided."""
    contact = CRMContact(
        name="Jane Smith",
        email="jane.smith@example.com",
        phone="555-123-4567",
        company="Acme Corp",
        last_contacted="2024-01-01",
        notes="Important client",
    )
    assert contact.name == "Jane Smith"
    assert contact.email == "jane.smith@example.com"
    assert contact.phone == "555-123-4567"
    assert contact.company == "Acme Corp"
    assert contact.last_contacted == "2024-01-01"
    assert contact.notes == "Important client"


def test_crm_contact_email_validation() -> None:
    """Test that CRMContact raises a ValidationError for invalid email."""
    with pytest.raises(ValidationError):
        CRMContact(name="Invalid", email="not-a-valid-email")


def test_crm_contact_id_optional() -> None:
    """Test that the id field is optional and can be None."""
    contact = CRMContact(name="Test", email="test@example.com")
    assert contact.id is None

    contact_with_id = CRMContact(name="Test", email="test@example.com", id=123)
    assert contact_with_id.id == 123


class TestMyScript:
    """Tests for the MyScript class."""

    @pytest.fixture
    def my_script(self) -> MyScript:
        """Fixture to create an instance of MyScript."""
        return MyScript()

    def test_my_script_initialization(self, my_script: MyScript) -> None:
        """Test that MyScript initializes correctly."""
        assert my_script.config_section == "db"
        assert my_script.logger is not None
        assert isinstance(my_script.logger, logging.Logger)

    @patch("dewey.core.db.models.BaseScript.get_config_value")
    @patch("dewey.core.db.models.BaseScript.logger")
    def test_my_script_run(
        self,
        mock_logger: Any,
        mock_get_config_value: Any,
        my_script: MyScript,
    ) -> None:
        """Test that MyScript.run() executes and logs messages."""
        mock_get_config_value.return_value = "test_db_url"
        my_script.run()

        mock_logger.info.assert_called()
        calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert "Running the script..." in calls
        assert "DB URL from config: test_db_url" in calls
        assert "Script completed." in calls
        mock_get_config_value.assert_called_once_with("db_url")

    @patch("dewey.core.db.models.BaseScript.get_config_value")
    def test_my_script_config_access(
        self, mock_get_config_value: Any, my_script: MyScript
    ) -> None:
        """Test that MyScript can access configuration values."""
        mock_get_config_value.return_value = "test_db_url"
        db_url = my_script.get_config_value("db_url")
        assert db_url == "test_db_url"
        mock_get_config_value.assert_called_once_with("db_url")

    def test_base_script_inheritance(self, my_script: MyScript) -> None:
        """Test that MyScript inherits from BaseScript."""
        assert isinstance(my_script, BaseScript)
