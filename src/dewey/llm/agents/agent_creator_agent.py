"""Agent creator for dynamically generating and configuring AI agents using smolagents."""

from __future__ import annotations

import json
from typing import Any

import structlog
from pydantic import BaseModel, Field

from smolagents import Tool
from .base_agent import DeweyBaseAgent

logger = structlog.get_logger(__name__)


class AgentConfig(BaseModel):
    """Configuration for a new agent."""

    name: str
    description: str
    task_type: str
    model: str = "mixtral-8x7b"
    complexity: int = Field(ge=0, le=2)
    functions: list[dict[str, Any]] = Field(default_factory=list)
    system_prompt: str | None = None
    required_imports: list[str] = Field(default_factory=list)
    base_classes: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    methods: list[dict[str, Any]] = Field(default_factory=list)


class AgentCreatorAgent(DeweyBaseAgent):
    """Agent for creating and configuring other AI agents.

    Features:
    - Dynamic agent creation
    - Function definition generation
    - System prompt crafting
    - Model selection
    - Code generation
    - Configuration validation
    """

    def __init__(self) -> None:
        """Initialize the agent creator."""
        super().__init__(
            task_type="agent_creation",
            model_id="Qwen/Qwen2.5-Coder-32B-Instruct" , # Use code-specialized model
        )
        self.add_tools([
            Tool.from_function(self.create_agent_config, description="Create configuration for a new agent")
        ])

    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent creator."""
        return """You are an expert AI agent creator in the Syzygy system.

Your role is to:
1. Design and configure new AI agents
2. Define appropriate function interfaces
3. Select optimal models for tasks
4. Generate clean, maintainable code
5. Ensure proper inheritance and composition

Key guidelines:
- Follow Python best practices
- Ensure proper error handling
- Include comprehensive documentation
- Consider scalability and maintainability
- Leverage existing Syzygy features

Always inherit from SyzygyAgent and follow the established patterns."""

    def create_agent_config(
        self,
        name: str,
        description: str,
        task_type: str,
        model: str = "mixtral-8x7b",
        complexity: int = 0,
        functions: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        required_imports: list[str] | None = None,
        base_classes: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
        methods: list[dict[str, Any]] | None = None,
    ) -> AgentConfig:
        """Create a new agent configuration based on requirements.

        Args:
        ----
            name: Name of the agent class
            description: Detailed description of the agent's purpose and features
            task_type: Type of task this agent handles
            model: Default model to use
            complexity: Task complexity level
            functions: List of function definitions
            system_prompt: Default system prompt for the agent
            required_imports: Required Python imports
            base_classes: Base classes to inherit from
            attributes: Class attributes and their types
            methods: Methods to implement

        Returns:
        -------
            Complete agent configuration

        """
        config = AgentConfig(
            name=name,
            description=description,
            task_type=task_type,
            model=model,
            complexity=complexity,
            functions=functions or [],
            system_prompt=system_prompt,
            required_imports=required_imports or [],
            base_classes=base_classes or [],
            attributes=attributes or {},
            methods=methods or [],
        )
        return config

    async def generate_code(self, config: AgentConfig) -> str:
        """Generate Python code for the agent configuration.

        Args:
        ----
            config: Agent configuration

        Returns:
        -------
            Complete Python code for the agent

        """
        # Start with imports
        code_parts = [
            '"""' + config.description + '"""',
            "",
            "from typing import List, Dict, Any, Optional",
            "from pydantic import BaseModel, Field",
            "import structlog",
            "import json",
            "",
            "from ..base import SyzygyAgent, FunctionDefinition",
            *[f"from {imp}" for imp in config.required_imports],
            "",
            "logger = structlog.get_logger(__name__)",
            "",
        ]

        # Add any model classes
        if config.methods:
            for method in config.methods:
                if method.get("request_model") or method.get("response_model"):
                    code_parts.extend(self._generate_models(method))

        # Start agent class
        base_classes = config.base_classes or ["SyzygyAgent"]
        class_def = f"class {config.name}({', '.join(base_classes)}):"
        code_parts.extend(
            [
                class_def,
                f'    """{config.description}',
                "    ",
                "    Features:",
                *[f"    - {line}" for line in config.description.split("\n")],
                '    """',
                "",
            ],
        )

        # Add initialization
        init_parts = [
            "    def __init__(self):",
            f'        """Initialize the {config.name.lower()}."""',
            "        super().__init__(",
            f'            task_type="{config.task_type}",',
            f'            model="{config.model}",',
            f"            complexity={config.complexity}",
        ]

        if config.functions:
            init_parts.extend(
                [
                    "            functions=[",
                    *self._generate_functions(config.functions),
                    "            ]",
                ],
            )

        init_parts.append("        )")
        code_parts.extend(init_parts)

        # Add system prompt if specified
        if config.system_prompt:
            code_parts.extend(
                [
                    "",
                    "    def get_system_prompt(self) -> str:",
                    f'        """Get the system prompt for the {config.name.lower()}."""',
                    '        return """' + config.system_prompt + '"""',
                ],
            )

        # Add methods
        if config.methods:
            for method in config.methods:
                code_parts.extend(self._generate_method(method))

        return "\n".join(code_parts)

    def _generate_models(self, method: dict[str, Any]) -> list[str]:
        """Generate Pydantic model classes for method parameters and responses."""
        models = []
        if request_model := method.get("request_model"):
            models.extend(
                [
                    f"class {request_model['name']}(BaseModel):",
                    f'    """{request_model["description"]}"""',
                    "",
                    *[
                        f"    {name}: {type_info}"
                        for name, type_info in request_model["fields"].items()
                    ],
                    "",
                ],
            )
        if response_model := method.get("response_model"):
            models.extend(
                [
                    f"class {response_model['name']}(BaseModel):",
                    f'    """{response_model["description"]}"""',
                    "",
                    *[
                        f"    {name}: {type_info}"
                        for name, type_info in response_model["fields"].items()
                    ],
                    "",
                ],
            )
        return models

    def _generate_functions(self, functions: list[dict[str, Any]]) -> list[str]:
        """Generate function definitions for the agent."""
        function_parts = []
        for func in functions:
            function_parts.extend(
                [
                    "                FunctionDefinition(",
                    f'                    name="{func["name"]}",',
                    f'                    description="{func["description"]}",',
                    "                    parameters={",
                    *[
                        f'                        "{name}": {json.dumps(param, indent=24)}'
                        for name, param in func["parameters"].items()
                    ],
                    "                    },",
                    f"                    required={json.dumps(func['required'])}",
                    "                ),",
                ],
            )
        return function_parts

    def _generate_method(self, method: dict[str, Any]) -> list[str]:
        """Generate a method definition."""
        method_parts = [""]
        async_def = "async " if method.get("is_async", True) else ""
        params = method.get("parameters", {})
        param_str = ", ".join(
            [f"{name}: {type_hint}" for name, type_hint in params.items()],
        )
        return_type = method.get("return_type", "None")

        method_parts.extend(
            [
                f"    {async_def}def {method['name']}({param_str}) -> {return_type}:",
                f'        """{method["description"]}',
                "        ",
                "        Args:",
                *[
                    f"            {name}: {desc}"
                    for name, desc in method.get("param_docs", {}).items()
                ],
                "        ",
                "        Returns:",
                f"            {method.get('return_doc', return_type)}",
                '        """',
                "        # TODO: Implement method",
                "        raise NotImplementedError",
            ],
        )

        return method_parts

    async def create_agent(
        self,
        purpose: str,
        requirements: list[str],
        context: dict | None = None,
    ) -> AgentConfig:
        """Create a new agent configuration based on requirements.

        Args:
        ----
            purpose: High-level purpose of the agent
            requirements: List of specific requirements
            context: Optional additional context

        Returns:
        -------
            Complete agent configuration

        """
        prompt = f"""Create a new AI agent with the following:

Purpose:
{purpose}

Requirements:
{json.dumps(requirements, indent=2)}

Additional Context:
{json.dumps(context, indent=2) if context else "None"}

Design an agent that:
1. Inherits from SyzygyAgent
2. Implements required functionality
3. Uses appropriate models
4. Has clear documentation
5. Follows best practices

The configuration should include:
- Appropriate function definitions
- System prompt
- Required attributes and methods
- Error handling
- Logging setup"""

        result = await self.run(prompt)

        # Parse and validate the configuration
        if isinstance(result, dict):
            if "function_call" in result:
                args = json.loads(result["function_call"]["arguments"])
                return AgentConfig(**args)
            return AgentConfig(**result)
        result_dict = json.loads(result)
        return AgentConfig(**result_dict)
