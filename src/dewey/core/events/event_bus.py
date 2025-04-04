"""
Event bus implementation for Dewey's event-driven architecture.

This module provides a publisher-subscriber mechanism for inter-module communication.
"""

import inspect
import logging
import threading
import time
import traceback
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, get_type_hints

logger = logging.getLogger(__name__)

# Type variables for event data
T = TypeVar("T")
EventHandler = Callable[[T], None]
EventFilter = Callable[[T], bool]


class EventBus:
    """
    Central event bus for cross-module communication.
    
    Implements the publisher-subscriber pattern, allowing modules to communicate
    without direct dependencies. Events are typed and can include arbitrary data.
    
    Examples:
        # Publishing an event
        event_bus.publish("contact_discovered", {"name": "John Doe", "email": "john@example.com"})
        
        # Subscribing to an event
        def handle_contact(data):
            print(f"New contact: {data['name']}")
            
        event_bus.subscribe("contact_discovered", handle_contact)
    """
    
    def __init__(self):
        """Initialize the event bus with empty subscribers dictionary."""
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._filters: Dict[str, Dict[EventHandler, List[EventFilter]]] = {}
        self._lock = threading.RLock()
        self._debug_mode = False
        
    def subscribe(self, event_type: str, handler: EventHandler, 
                  filters: Optional[List[EventFilter]] = None) -> None:
        """
        Subscribe to an event type with optional filters.
        
        Args:
            event_type: The type of event to subscribe to
            handler: Callback function to be called when the event is published
            filters: Optional list of filter functions that determine if the handler should be called
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
                self._filters[event_type] = {}
                
            # Add the handler if it's not already subscribed
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                
                # Add filters if provided
                if filters:
                    self._filters[event_type][handler] = filters
                    
            logger.debug(f"Subscribed to event: {event_type}")
        
    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """
        Unsubscribe a handler from an event type.
        
        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove
            
        Returns:
            True if the handler was removed, False if it wasn't found
        """
        with self._lock:
            if event_type not in self._subscribers:
                return False
                
            if handler not in self._subscribers[event_type]:
                return False
                
            self._subscribers[event_type].remove(handler)
            
            # Remove associated filters
            if event_type in self._filters and handler in self._filters[event_type]:
                del self._filters[event_type][handler]
                
            logger.debug(f"Unsubscribed from event: {event_type}")
            return True
        
    def publish(self, event_type: str, data: Any = None) -> int:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: The type of event to publish
            data: The data associated with the event
            
        Returns:
            Number of handlers that processed the event
        """
        handlers_called = 0
        
        with self._lock:
            if event_type not in self._subscribers or not self._subscribers[event_type]:
                logger.debug(f"No subscribers for event: {event_type}")
                return 0
                
            handlers = self._subscribers[event_type].copy()
        
        for handler in handlers:
            try:
                # Check if this handler has filters
                if (event_type in self._filters and 
                    handler in self._filters[event_type] and 
                    self._filters[event_type][handler]):
                    
                    # Apply all filters - if any return False, skip this handler
                    should_handle = True
                    for filter_fn in self._filters[event_type][handler]:
                        if not filter_fn(data):
                            should_handle = False
                            break
                            
                    if not should_handle:
                        continue
                
                # Call the handler with the event data
                handler(data)
                handlers_called += 1
                
                if self._debug_mode:
                    logger.debug(f"Handler {handler.__name__} processed event: {event_type}")
                    
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
                if self._debug_mode:
                    logger.error(traceback.format_exc())
        
        return handlers_called
    
    def clear_all_subscribers(self) -> None:
        """Remove all subscribers from all event types (primarily for testing)."""
        with self._lock:
            self._subscribers.clear()
            self._filters.clear()
    
    def get_subscribers(self, event_type: str) -> List[EventHandler]:
        """
        Get all subscribers for a specific event type.
        
        Args:
            event_type: The event type to get subscribers for
            
        Returns:
            List of handler functions subscribed to the event type
        """
        with self._lock:
            if event_type not in self._subscribers:
                return []
            return self._subscribers[event_type].copy()
    
    def set_debug_mode(self, enabled: bool) -> None:
        """
        Enable or disable debug mode for detailed logging.
        
        Args:
            enabled: Whether to enable debug mode
        """
        self._debug_mode = enabled
        if enabled:
            logger.debug("Event bus debug mode enabled")
        else:
            logger.debug("Event bus debug mode disabled")


# Create a singleton instance
event_bus = EventBus() 