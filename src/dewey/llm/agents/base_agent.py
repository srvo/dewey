from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict, Union
import re
import jinja2
from jinja2 import StrictUndefined, Template
from logging import getLogger

from dewey.core.base_script import BaseScript

logger = getLogger(__name__)


class BaseAgent(BaseScript):
    """
    Base class for all agents.

    This class provides a foundation for building agents within the Dewey
    project, offering standardized configuration, logging, and database/LLM
    integration.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config_section: Optional[str] = None,
        requires_db: bool = False,
        enable_llm: bool = True,  # BaseAgent likely needs LLM
        **kwargs: Any,
    ) -> None:
        """
        Initializes the BaseAgent script.

        Args:
            name: Name of the agent (used for logging)
            description: Description of the agent
            config_section: Section in dewey.yaml to load for this agent
            requires_db: Whether this agent requires database access
            enable_llm: Whether this agent requires LLM access
            **kwargs: Keyword arguments passed to the BaseScript constructor.
        """
        super().__init__(
            name=name,
            description=description,
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
            **kwargs,
        )
        self.authorized_imports: List[str] = []  # Example attribute
        self.executor_type: str = "local"  # Example attribute
        self.executor_kwargs: Dict[str, Any] = {}  # Example attribute
        self.max_print_outputs_length: int = 1000  # Example attribute
        self.disable_rate_limit: bool = False  # New attribute to disable rate limiting

    def run(self) -> None:
        """
        Executes the agent's primary logic.

        This method should be overridden by subclasses to implement
        the specific behavior of the agent.
        """
        self.logger.info(f"Running agent: {self.name}")
        # Implement agent-specific logic here
        raise NotImplementedError("Subclasses must implement the run method.")

    def get_variable_names(self, template: str) -> Set[str]:
        """Extract variable names from a Jinja2 template."""
        pattern = re.compile(r"\{\{([^}]+)\}\}")  # Corrected regex
        return {match.group(1).strip() for match in pattern.finditer(template)}

    def populate_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Populate a Jinja2 template with variables."""
        compiled_template = Template(template, undefined=StrictUndefined)
        try:
            return compiled_template.render(**variables)
        except Exception as e:
            raise Exception(f"Error during jinja template rendering: {type(e).__name__}: {e}")

    def _generate_code(self, prompt: str) -> str:
        """Generates code based on the given prompt using the LLM.

        Args:
            prompt: The prompt to use for code generation.

        Returns:
            The generated code.
        """
        if not self.llm_client:
            raise ValueError("LLM client is not initialized. Ensure enable_llm=True in the constructor.")

        try:
            # Check if rate limiting should be disabled
            if self.disable_rate_limit:
                self.logger.warning("Rate limiting is disabled for this agent.")
            
            response = self.llm_client.generate(prompt, disable_rate_limit=self.disable_rate_limit)  # Assuming a generate method exists
            return response.text  # Assuming the response has a text attribute
        except Exception as e:
            self.logger.error(f"LLM code generation failed: {e}")
            raise

    def execute(self) -> None:
        """
        Execute the agent.

        This method handles the common setup and execution flow:
        1. Parse arguments
        2. Set up logging and configuration
        3. Run the agent
        4. Handle exceptions
        5. Clean up resources
        """
        try:
            # Parse arguments
            args = self.parse_args()

            # Run the agent
            self.logger.info(f"Starting execution of {self.name}")
            self.run()
            self.logger.info(f"Completed execution of {self.name}")

        except KeyboardInterrupt:
            self.logger.warning("Script interrupted by user")
            import sys
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error executing script: {e}", exc_info=True)
            import sys
            sys.exit(1)
        finally:
            # Clean up resources
            self._cleanup()

    def to_dict(self) -> dict[str, Any]:
        """Convert the agent to a dictionary representation.

        Returns:
            `dict`: Dictionary representation of the agent.
        """
        agent_dict = {
            "name": self.name,
            "description": self.description,
            "config_section": self.config_section,
            "requires_db": self.requires_db,
            "enable_llm": self.enable_llm,
            "authorized_imports": self.authorized_imports,
            "executor_type": self.executor_type,
            "executor_kwargs": self.executor_kwargs,
            "max_print_outputs_length": self.max_print_outputs_length,
            "disable_rate_limit": self.disable_rate_limit,
        }
        return agent_dict
