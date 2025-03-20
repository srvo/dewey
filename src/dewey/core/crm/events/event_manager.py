from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
    Tuple,
    Callable,
)
import time
from dataclasses import dataclass
from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection
from dewey.llm import llm_utils


# Define placeholder classes for Contact and Email, replace with actual definitions if available
@dataclass
class Contact:
    """Placeholder for a Contact class."""
    id: int
    name: str
    email: str


@dataclass
class Email:
    """Placeholder for an Email class."""
    recipient: str
    subject: str
    body: str


class EventManager(BaseScript):
    """
    A comprehensive class for managing events, including creation, filtering,
    retries, logging, and context management.
    """

    def __init__(self, request_id: str, max_retries: int = 3) -> None:
        """
        Initializes the EventManager with a request ID and maximum retry attempts.

        Args:
            request_id: A unique identifier for the request.
            max_retries: The maximum number of retries for operations. Defaults to 3.
        """
        super().__init__(config_section='crm')

        self.request_id = request_id
        self.max_retries = max_retries
        self._events: List[Dict[str, Any]] = []  # Internal storage for events
        self._context: Dict[str, Any] = {}  # Contextual data

    def run(self) -> None:
        """
        Executes the main logic of the EventManager.

        This method currently serves as a placeholder and raises a NotImplementedError.
        Subclasses should override this method to implement their specific logic.

        Raises:
            NotImplementedError: If the method is not overridden in a subclass.
        """
        self.logger.info("Running EventManager...")
        # Example of accessing a config value
        max_retries_config = self.get_config_value("settings.max_retries", 3)
        self.logger.info(f"Max retries from config: {max_retries_config}")

        # Example of using the database connection (if enabled)
        if self.db_conn:
            try:
                with self.db_conn.cursor() as cur:
                    cur.execute("SELECT 1")  # Example query
                    result = cur.fetchone()
                    self.logger.info(f"Database connection test: {result}")
            except Exception as e:
                self.logger.error(f"Error connecting to the database: {e}")

        # Example of using the LLM client (if enabled)
        if self.llm_client:
            try:
                response = self.llm_client.generate_text("Write a short poem about events.")
                self.logger.info(f"LLM response: {response}")
            except Exception as e:
                self.logger.error(f"Error using LLM client: {e}")

        raise NotImplementedError("The run method must be implemented")

    def objects(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all stored event objects.

        Returns:
            A list of dictionaries, where each dictionary represents an event.
        """
        return self._events

    def save(self) -> None:
        """
        Placeholder for saving events.  In a real implementation, this would
        persist the events to a database or other storage.
        """
        self.logger.info(f"Saving {len(self._events)} events (implementation placeholder).")
        # In a real implementation, this would save self._events to a database, file, etc.
        pass

    def all(self) -> List[Dict[str, Any]]:
        """
        Returns all stored events.  Equivalent to `objects()`.

        Returns:
            A list of dictionaries, where each dictionary represents an event.
        """
        return self.objects()

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """
        Returns an iterator for the stored events.

        Yields:
            Dictionaries representing individual events.
        """
        return iter(self._events)

    def __len__(self) -> int:
        """
        Returns the number of stored events.

        Returns:
            The number of stored events as an integer.
        """
        return len(self._events)

    def filter(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Filters the stored events based on keyword arguments.

        Args:
            **kwargs: Keyword arguments representing filter criteria.  For example,
                      `filter(event_type="user_login", entity_id=123)`

        Returns:
            A list of dictionaries that match the filter criteria.
        """
        filtered_events: List[Dict[str, Any]] = []
        for event in self._events:
            match = True
            for key, value in kwargs.items():
                if key not in event or event[key] != value:
                    match = False
                    break
            if match:
                filtered_events.append(event)
        return filtered_events

    def create(
        self,
        event_type: str,
        entity_id: Optional[Union[int, str]] = None,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        **kwargs: Any,  # Allow for arbitrary event data
    ) -> None:
        """
        Creates a new event and stores it.

        Args:
            event_type: The type of the event (e.g., "user_login", "order_placed").
            entity_id: Optional ID of the entity associated with the event.
            error: Optional error message if the event represents an error.
            error_type: Optional type of the error.
            **kwargs: Additional event-specific data.
        """
        event: Dict[str, Any] = {
            "event_type": event_type,
            "entity_id": entity_id,
            "error": error,
            "error_type": error_type,
            **self._context,  # Include context data
            **kwargs,  # Include any additional data passed in
        }
        self._events.append(event)
        self.logger.info(f"Created event: {event}")

    def enrich_contact(self, contact: Contact) -> None:
        """
        Placeholder for enriching events with contact information.

        Args:
            contact: A Contact object.
        """
        self.logger.info(f"Enriching events with contact: {contact}")
        # In a real implementation, this would add contact-related data to existing events.
        pass

    def enrich_email(self, email: Email) -> None:
        """
        Placeholder for enriching events with email information.

        Args:
            email: An Email object.
        """
        self.logger.info(f"Enriching events with email: {email}")
        # In a real implementation, this would add email-related data to existing events.
        pass

    def retry(self, func: Callable[..., Any], *args: Any, countdown: int = 0, **kwargs: Any) -> Any:
        """
        Retries a function call if an exception occurs.

        Args:
            func: The function to retry.
            *args: Positional arguments to pass to the function.
            countdown: The initial countdown in seconds before the first retry.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The result of the function call if successful.

        Raises:
            Exception: If the function fails after the maximum number of retries.
        """
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"Retrying function (attempt {attempt}/{self.max_retries})...")
                if attempt > 0 and countdown > 0:
                    time.sleep(countdown)
                return func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Function failed (attempt {attempt}/{self.max_retries}): {e}")
                if attempt == self.max_retries:
                    self.logger.error(f"Function failed after {self.max_retries} retries.")
                    raise  # Re-raise the exception after all retries
                # Exponential backoff (optional)
                countdown = 2 ** attempt  # Double the countdown each time
                time.sleep(countdown)

    def set_context(self, **kwargs: Any) -> None:
        """
        Sets contextual data that will be added to all subsequent events.

        Args:
            **kwargs: Keyword arguments representing context data.
        """
        self._context.update(kwargs)
        self.logger.info(f"Set context: {kwargs}")

    def info(self, message: str) -> None:
        """
        Logs an informational message.

        Args:
            message: The message to log.
        """
        self.logger.info(message)

    def error(self, message: str) -> None:
        """
        Logs an error message.

        Args:
            message: The error message to log.
        """
        self.logger.error(message)

    def exception(self, message: str) -> None:
        """
        Logs an exception message.  This is typically used when an exception
        has already been caught.

        Args:
            message: The exception message to log.
        """
        self.logger.exception(message)
