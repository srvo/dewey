import pytest
from unittest.mock import MagicMock, patch
from dewey.core.crm.events.event_manager import EventManager, Contact, Email
import logging


@pytest.fixture
def event_manager(mocker: MagicMock) -> EventManager:
    """Fixture for creating an EventManager instance with mocked dependencies."""
    mocker.patch("dewey.core.crm.events.event_manager.BaseScript.__init__", return_value=None)
    event_manager = EventManager(request_id="test_request")
    event_manager.logger = mocker.MagicMock()
    event_manager.db_conn = mocker.MagicMock()
    event_manager.llm_client = mocker.MagicMock()
    return event_manager


def test_event_manager_initialization(event_manager: EventManager, mocker: MagicMock) -> None:
    """Test that the EventManager initializes correctly."""
    assert event_manager.request_id=None):
        if mocker: MagicMock) -> None:
    """Test that the EventManager initializes correctly."""
    assert event_manager.request_id is None:
            mocker: MagicMock) -> None:
    """Test that the EventManager initializes correctly."""
    assert event_manager.request_id = = "test_request"
    assert event_manager.max_retries == 3
    assert event_manager._events == []
    assert event_manager._context == {}
    event_manager.logger.info.assert_called_with("Initialized EventManager")


def test_run_not_implemented(event_manager: EventManager) -> None:
    """Test that the run method raises a NotImplementedError."""
    with pytest.raises(NotImplementedError
        event_manager.run()
    event_manager.logger.info.assert_called_with("Running EventManager...")


def test_objects(event_manager: EventManager) -> None:
    """Test that the objects method returns the stored events."""
    event_manager._events = [{"event_type": "test_event"}]
    assert event_manager.objects() == [{"event_type": "test_event"}]


def test_save(event_manager: EventManager) -> None:
    """Test that the save method logs the number of events."""
    event_manager._events = [{"event_type": "test_event"}]
    event_manager.save()
    event_manager.logger.info.assert_called_with("Saving 1 events (implementation placeholder).")


def test_all(event_manager: EventManager) -> None:
    """Test that the all method returns all stored events."""
    event_manager._events = [{"event_type": "test_event"}]
    assert event_manager.all() == [{"event_type": "test_event"}]


def test_iter(event_manager: EventManager) -> None:
    """Test that the EventManager is iterable."""
    event_manager._events = [{"event_type": "test_event"}]
    events = [event for event in event_manager]
    assert events == [{"event_type": "test_event"}]


def test_len(event_manager: EventManager) -> None:
    """Test that the len method returns the number of stored events."""
    event_manager._events = [{"event_type": "test_event"}, {"event_type": "another_event"}]
    assert len(event_manager) == 2


def test_filter(event_manager: EventManager) -> None:
    """Test that the filter method filters events based on keyword arguments."""
    event_manager._events = [
        {"event_type": "user_login", "entity_id": 123, "username": "test_user"},
        {"event_type": "order_placed", "entity_id": 456, "product_id": 789},
        {"event_type": "user_login", "entity_id": 123, "username": "another_user"},
    ]
    filtered_events = event_manager.filter(event_type="user_login", entity_id=123)
    assert len(filtered_events) == 2
    assert filtered_events[0]["username"] in ("test_user", "another_user")
    assert filtered_events[1]["username"] in ("test_user", "another_user")


def test_filter_no_match(event_manager: EventManager) -> None:
    """Test that the filter method returns an empty list when no events match the filter criteria."""
    event_manager._events = [
        {"event_type": "user_login", "entity_id": 123},
        {"event_type": "order_placed", "entity_id": 456},
    ]
    filtered_events = event_manager.filter(event_type="non_existent_event")
    assert len(filtered_events) == 0


def test_create(event_manager: EventManager) -> None:
    """Test that the create method creates and stores a new event."""
    event_manager.create(event_type="user_login", entity_id=123, username="test_user")
    assert len(event_manager._events) == 1
    event = event_manager._events[0]
    assert event["event_type"] == "user_login"
    assert event["entity_id"] == 123
    assert event["username"] == "test_user"
    event_manager.logger.info.assert_called()


def test_create_with_context(event_manager: EventManager) -> None:
    """Test that the create method includes context data in the new event."""
    event_manager.set_context(request_id="test_request", user_agent="Chrome")
    event_manager.create(event_type="user_login", entity_id=123)
    assert len(event_manager._events) == 1
    event = event_manager._events[0]
    assert event["request_id"] == "test_request"
    assert event["user_agent"] == "Chrome"


def test_enrich_contact(event_manager: EventManager) -> None:
    """Test that the enrich_contact method logs the contact information."""
    contact = Contact(id=1, name="John Doe", email="john.doe@example.com")
    event_manager.enrich_contact(contact)
    event_manager.logger.info.assert_called_with(f"Enriching events with contact: {contact}")


def test_enrich_email(event_manager: EventManager) -> None:
    """Test that the enrich_email method logs the email information."""
    email = Email(recipient="john.doe@example.com", subject="Test Email", body="This is a test email.")
    event_manager.enrich_email(email)
    event_manager.logger.info.assert_called_with(f"Enriching events with email: {email}")


def test_retry_success(event_manager: EventManager) -> None:
    """Test that the retry method returns the result of the function call if successful."""
    mock_func = MagicMock(return_value="Success")
    result = event_manager.retry(mock_func)
    assert result == "Success"
    mock_func.assert_called_once()


def test_retry_failure(event_manager: EventManager) -> None:
    """Test that the retry method retries the function call if an exception occurs."""
    mock_func = MagicMock(side_effect=[Exception("Test Exception"), "Success"])
    result = event_manager.retry(mock_func, countdown=0)
    assert result == "Success"
    assert mock_func.call_count == 2
    event_manager.logger.info.assert_called_with("Retrying function (attempt 1/3)...")
    event_manager.logger.error.assert_called()


def test_retry_max_retries_exceeded(event_manager: EventManager) -> None:
    """Test that the retry method raises an exception if the function fails after the maximum number of retries."""
    mock_func = MagicMock(side_effect=Exception("Test Exception"))
    with pytest.raises(Exception, match="Test Exception"):
        event_manager.retry(mock_func, countdown=0)
    assert mock_func.call_count == 4
    event_manager.logger.error.assert_called()


def test_set_context(event_manager: EventManager) -> None:
    """Test that the set_context method sets contextual data."""
    event_manager.set_context(request_id="test_request", user_agent="Chrome")
    assert event_manager._context == {"request_id": "test_request", "user_agent": "Chrome"}
    event_manager.logger.info.assert_called_with({"request_id": "test_request", "user_agent": "Chrome"})


def test_info(event_manager: EventManager) -> None:
    """Test that the info method logs an informational message."""
    event_manager.info("Test info message")
    event_manager.logger.info.assert_called_with("Test info message")


def test_error(event_manager: EventManager) -> None:
    """Test that the error method logs an error message."""
    event_manager.error("Test error message")
    event_manager.logger.error.assert_called_with("Test error message")


def test_exception(event_manager: EventManager) -> None:
    """Test that the exception method logs an exception message."""
    event_manager.exception("Test exception message")
    event_manager.logger.exception.assert_called_with("Test exception message")


@patch('time.sleep', return_value=None)
def test_retry_with_countdown(mock_sleep: MagicMock, event_manager: EventManager) -> None:
    """Test that the retry method waits the specified countdown before retrying."""
    mock_func = MagicMock(side_effect=[Exception("Test Exception"), "Success"])
    result = event_manager.retry(mock_func, countdown=1)
    assert result == "Success"
    assert mock_func.call_count == 2
    mock_sleep.assert_called_once_with(1)


def test_create_with_error_data(event_manager: EventManager) -> None:
    """Test that the create method correctly handles error and error_type arguments."""
    event_manager.create(
        event_type="api_error",
        entity_id="order_123",
        error="Failed to process order",
        error_type="APIError",
        status_code=500
    )
    assert len(event_manager._events) == 1
    event = event_manager._events[0]
    assert event["event_type"] == "api_error"
    assert event["entity_id"] == "order_123"
    assert event["error"] == "Failed to process order"
    assert event["error_type"] == "APIError"
    assert event["status_code"] == 500
    event_manager.logger.info.assert_called()


def test_retry_exponential_backoff(event_manager: EventManager, mocker: MagicMock) -> None:
    """Test that the retry method uses exponential backoff."""
    mock_func = MagicMock(side_effect=[Exception("Test Exception"), Exception("Test Exception"), "Success"])
    sleep_mock = mocker.patch('time.sleep')
    result = event_manager.retry(mock_func, countdown=1)
    assert result == "Success"
    assert mock_func.call_count == 3
    assert sleep_mock.call_count == 2
    sleep_mock.assert_called_with(4)  # 2 ** attempt (attempt 2)


def test_get_config_value(event_manager: EventManager) -> None:
    """Test that the get_config_value method retrieves configuration values correctly."""
    event_manager.config = {"llm": {"model": "test_model"}, "api": {"timeout": 10}}
    assert event_manager.get_config_value("llm.model") == "test_model"
    assert event_manager.get_config_value("api.timeout") == 10
    assert event_manager.get_config_value("nonexistent.value", "default_value") == "default_value"
    assert event_manager.get_config_value("llm.nonexistent", None) is None


def test_get_config_value_no_config_section(mocker: MagicMock) -> None:
    """Test get_config_value when no config_section is provided during initialization."""
    mocker.patch("dewey.core.crm.events.event_manager.BaseScript.__init__", return_value=None)
    event_manager = EventManager(request_id="test_request")
    event_manager.logger = mocker.MagicMock()
    event_manager.config = {"llm": {"model": "test_model"}}
    assert event_manager.get_config_value("llm.model") == "test_model"


def test_get_config_value_with_config_section(mocker: MagicMock) -> None:
    """Test get_config_value when a config_section is provided during initialization."""
    mocker.patch("dewey.core.crm.events.event_manager.BaseScript.__init__", return_value=None)
    event_manager = EventManager(request_id="test_request")
    event_manager.logger = mocker.MagicMock()
    event_manager.config = {"crm": {"llm": {"model": "test_model"}}}
    event_manager.config_section = "crm"
    assert event_manager.get_config_value("llm.model") == "test_model"


def test_get_config_value_with_default(event_manager: EventManager) -> None:
    """Test that the get_config_value method returns the default value when the key is not found."""
    event_manager.config = {"llm": {"model": "test_model"}}
    assert event_manager.get_config_value("nonexistent_key", "default_value") == "default_value"
    assert event_manager.get_config_value("llm.nonexistent_key", None) is None


def test_get_config_value_nested(event_manager: EventManager) -> None:
    """Test that the get_config_value method retrieves nested configuration values correctly."""
    event_manager.config = {"nested": {"level1": {"level2": "nested_value"}}}
    assert event_manager.get_config_value("nested.level1.level2") == "nested_value"
    assert event_manager.get_config_value("nested.level1.nonexistent", "default") == "default"
    assert event_manager.get_config_value("nonexistent.level1.level2", None) is None
