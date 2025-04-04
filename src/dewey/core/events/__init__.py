"""
Event system for inter-module communication in Dewey.

This module provides a centralized event bus that allows modules to communicate
without direct dependencies. It implements a publisher-subscriber pattern where
modules can publish events and subscribe to events from other modules.
"""

from dewey.core.events.event_bus import EventBus, event_bus

__all__ = ["EventBus", "event_bus"] 