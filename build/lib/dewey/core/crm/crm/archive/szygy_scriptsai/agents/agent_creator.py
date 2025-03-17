"""Agent creator for dynamically generating and configuring AI agents."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import structlog
import json

from ..base import SyzygyAgent, FunctionDefinition

logger = structlog.get_logger(__name__)


class AgentConfig(BaseModel):
    """Configuration for a new agent."""

    name: str
    description: str
    task_type: str
    model: str = "mixtral-8x7b"
    complexity: int = Field(ge=0, le=2)
    functions: List[Dict[str, Any]] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    required_imports: List[str] = Field(default_factory=list)
    base_classes: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    methods: List[Dict[str, Any]] = Field(default_factory=list)


class AgentCreator(SyzygyAgent):
    """Agent for creating and configuring other AI agents.

    Features:
    - Dynamic agent creation
    - Function definition generation
    - System prompt crafting
    - Model selection
    - Code generation
    - Configuration validation
    """

    def __init__(self):
        """Initialize the agent creator."""
        super().__init__(
            task_type="agent_creation",
            model="qwen-coder-32b",  # Use code-specialized model
            complexity=2,
            functions=[
                FunctionDefinition(
                    name="create_agent_config",
                    description="Create configuration for a new agent",
                    parameters={
                        "name": {
                            "type": "string",
                            "description": "Name of the agent class",
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the agent's purpose and features",
                        },
                        "task_type": {
                            "type": "string",
                            "description": "Type of task this agent handles",
                        },
                        "model": {
                            "type": "string",
                            "description": "Default model to use",
                        },
                        "complexity": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 2,
                            "description": "Task complexity level",
                        },
                        "functions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "parameters": {"type": "object"},
                                    "required": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                            "description": "List of function definitions",
                        },
                        "system_prompt": {
                            "type": "string",
                            "description": "Default system prompt for the agent",
                        },
                        "required_imports": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Required Python imports",
                        },
                        "base_classes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Base classes to inherit from",
                        },
                        "attributes": {
                            "type": "object",
                            "description": "Class attributes and their types",
                        },
                        "methods": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "parameters": {"type": "object"},
                                    "return_type": {"type": "string"},
                                    "is_async": {"type": "boolean"},
                                },
                            },
                            "description": "Methods to implement",
                        },
                    },
                    required=["name", "description", "task_type"],
                )
            ],
        )

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

    async def create_agent(
        self, purpose: str, requirements: List[str], context: Optional[Dict] = None
    ) -> AgentConfig:
        """Create a new agent configuration based on requirements.

        Args:
            purpose: High-level purpose of the agent
            requirements: List of specific requirements
            context: Optional additional context

        Returns:
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

        result = await self.run(
            prompt=prompt,
            metadata={"purpose": purpose},
            result_type="agent_config",
            entity_type="agent",
            entity_id=str(hash(purpose))[:8],
            response_format={"type": "json_object"},
        )

        # Parse and validate the configuration
        if isinstance(result, dict):
            if "function_call" in result:
                args = json.loads(result["function_call"]["arguments"])
                return AgentConfig(**args)
            return AgentConfig(**result)
        else:
            result_dict = json.loads(result)
            return AgentConfig(**result_dict)

    async def generate_code(self, config: AgentConfig) -> str:
        """Generate Python code for the agent configuration.

        Args:
            config: Agent configuration

        Returns:
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
            ]
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
                ]
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
                ]
            )

        # Add methods
        if config.methods:
            for method in config.methods:
                code_parts.extend(self._generate_method(method))

        return "\n".join(code_parts)

    def _generate_models(self, method: Dict[str, Any]) -> List[str]:
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
                ]
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
                ]
            )
        return models

    def _generate_functions(self, functions: List[Dict[str, Any]]) -> List[str]:
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
                ]
            )
        return function_parts

    def _generate_method(self, method: Dict[str, Any]) -> List[str]:
        """Generate a method definition."""
        method_parts = [""]
        async_def = "async " if method.get("is_async", True) else ""
        params = method.get("parameters", {})
        param_str = ", ".join(
            [f"{name}: {type_hint}" for name, type_hint in params.items()]
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
            ]
        )

        return method_parts
