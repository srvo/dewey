from typing import Any, Dict, List, Optional
from dewey.core.base_script import BaseScript


class BaseEngine(BaseScript):
    """Base class for search and analysis engines.

    Inherits from BaseScript and provides standardized access to
    configuration, logging, and other utilities.
    """

    def __init__(self, name: str, description: str = "Base Engine") -> None:
        """Initialize the engine.

        Args:
            name: The name of the engine.
            description: A brief description of the engine.
        """
        super().__init__(name=name, description=description)
        self.templates: Dict[str, str] = {}

    def run(self) -> None:
        """
        Run the engine.  This method should be overridden by subclasses
        to implement the engine's primary logic.
        """
        self.logger.info(f"Running {self.name}...")
        raise NotImplementedError("The run method must be implemented in the subclass.")

    def add_template(self, name: str, template: str) -> None:
        """Add a template to the engine.

        Args:
            name: Template name.
            template: Template string.
        """
        self.logger.debug(f"Adding template: {name}")
        self.templates[name] = template

    def get_template(self, name: str) -> Optional[str]:
        """Get a template by name.

        Args:
            name: Template name.

        Returns:
            Template string if found, None otherwise.
        """
        self.logger.debug(f"Getting template: {name}")
        return self.templates.get(name)

    def search(self, query: str) -> List[Dict[str, str]]:
        """Search for information.

        Args:
            query: Search query.

        Returns:
            List of search results.
        """
        self.logger.info(f"Searching for: {query}")
        return []

    def analyze(self, template_name: str, **kwargs: Any) -> str:
        """Analyze data using a template.

        Args:
            template_name: Name of the template to use.
            **kwargs: Template variables.

        Returns:
            Analysis result.
        """
        self.logger.info(f"Analyzing with template: {template_name}")
        template = self.get_template(template_name)
        if template is None:
            error_message = f"No template found with name: {template_name}"
            self.logger.error(error_message)
            return error_message

        try:
            formatted_template = template.format(**kwargs)
            self.logger.debug(f"Formatted template: {formatted_template}")
            return formatted_template
        except KeyError as e:
            error_message = f"Missing required variable: {e}"
            self.logger.error(error_message)
            return error_message
        except Exception as e:
            error_message = f"Error formatting template: {e}"
            self.logger.exception(error_message)
            return error_message
