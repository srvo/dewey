"""
Service registry for locating and managing service implementations.

This module provides a central registry for service implementations, allowing
modules to discover and use services without direct dependencies.
"""

import logging
from typing import Any, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceRegistry:
    """
    Registry for service implementations.

    This class provides a central registry for service implementations.
    It implements the Singleton pattern to ensure only one registry exists.

    Examples
    --------
        # Registering a service
        registry = ServiceRegistry()
        registry.register(LLMProvider, LiteLLMProvider())

        # Getting a service
        llm_provider = registry.get(LLMProvider)
        if llm_provider:
            text = llm_provider.generate_text("Hello, world!")

    """

    _instance = None

    def __new__(cls) -> "ServiceRegistry":
        """Implement singleton pattern to ensure only one registry exists."""
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
            cls._instance._services: dict[type, Any] = {}
            cls._instance._factories: dict[type, callable] = {}
            logger.debug("Created new ServiceRegistry instance")
        return cls._instance

    def register(self, interface: type[T], implementation: T) -> None:
        """
        Register a service implementation.

        Args:
        ----
            interface: The interface or abstract class
            implementation: The concrete implementation

        """
        self._services[interface] = implementation
        logger.debug(f"Registered implementation for {interface.__name__}")

    def register_factory(self, interface: type[T], factory: callable) -> None:
        """
        Register a factory function for creating a service implementation.

        Args:
        ----
            interface: The interface or abstract class
            factory: A callable that returns an implementation

        """
        self._factories[interface] = factory
        logger.debug(f"Registered factory for {interface.__name__}")

    def get(self, interface: type[T], create_if_missing: bool = True) -> T | None:
        """
        Get a service implementation.

        Args:
        ----
            interface: The interface or abstract class
            create_if_missing: Whether to call the factory if registered

        Returns:
        -------
            The implementation or None if not found and no factory exists

        """
        # Check if we have a direct implementation
        if interface in self._services:
            return cast(T, self._services[interface])

        # If not, check if we have a factory and should create
        if create_if_missing and interface in self._factories:
            try:
                implementation = self._factories[interface]()
                self._services[interface] = implementation
                logger.debug(
                    f"Created implementation for {interface.__name__} using factory",
                )
                return cast(T, implementation)
            except Exception as e:
                logger.error(
                    f"Error creating implementation for {interface.__name__}: {e}",
                )
                return None

        logger.warning(f"No implementation found for {interface.__name__}")
        return None

    def clear(self) -> None:
        """
        Clear all registered services and factories.

        This is primarily useful for testing.
        """
        self._services.clear()
        self._factories.clear()
        logger.debug("Cleared all services and factories")


# Create singleton instance
service_registry = ServiceRegistry()
