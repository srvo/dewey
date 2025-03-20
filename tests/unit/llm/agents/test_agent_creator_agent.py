import pytest
import json
from dewey.llm.agents.agent_creator_agent import AgentCreatorAgent, AgentConfig
from pydantic import ValidationError


@pytest.fixture
def agent_creator():
    """Function agent_creator."""
    return AgentCreatorAgent()


def test_create_agent_config_valid_params(agent_creator):
    """Test creating a valid agent configuration with all parameters."""
    config = agent_creator.create_agent_config(
        name="TestAgent",
        description="A test agent for validation",
        task_type="testing",
        model="test_model",
        complexity=1,
        functions=[
            {
                "name": "test_func",
                "description": "A test function",
                "parameters": {"param1": "str"},
                "required": ["param1"],
            }
        ],
        system_prompt="Test system prompt",
        required_imports=["import logging"],
        base_classes=["BaseAgent"],
        attributes={"test_attr": "value"},
        methods=[
            {
                "name": "test_method",
                "description": "Test method",
                "parameters": {"arg1": "int"},
                "return_type": "str",
                "param_docs": {"arg1": "An integer parameter"},
            }
        ],
    )
    assert config.name == "TestAgent"
    assert config.description == "A test agent for validation"
    assert config.task_type == "testing"
    assert config.model == "test_model"
    assert config.complexity == 1
    assert len(config.functions) == 1
    assert config.functions[0]["name"] == "test_func"
    assert config.system_prompt == "Test system prompt"
    assert "import logging" in config.required_imports
    assert "BaseAgent" in config.base_classes
    assert config.attributes == {"test_attr": "value"}
    assert len(config.methods) == 1
    assert config.methods[0]["name"] == "test_method"


def test_create_agent_config_complexity_boundaries(agent_creator):
    """Test complexity at minimum and maximum values."""
    # Test min complexity
    config_min = agent_creator.create_agent_config(
        name="MinComplexity",
        description="Test min complexity",
        task_type="test",
        complexity=0,
    )
    assert config_min.complexity == 0

    # Test max complexity
    config_max = agent_creator.create_agent_config(
        name="MaxComplexity",
        description="Test max complexity",
        task_type="test",
        complexity=2,
    )
    assert config_max.complexity == 2

    # Test out of bounds (should raise)
    with pytest.raises(ValidationError):
        agent_creator.create_agent_config(
            name="InvalidComplexity",
            description="Invalid complexity test",
            task_type="test",
            complexity=3,
        )


def test_generate_code_with_models(agent_creator):
    """Test code generation with methods containing request/response models."""
    config = AgentConfig(
        name="TestAgentWithModels",
        description="Agent with method models",
        task_type="testing",
        methods=[
            {
                "name": "process_data",
                "description": "Process data with models",
                "request_model": {
                    "name": "RequestModel",
                    "description": "Request model for processing",
                    "fields": {"input": "str", "option": "bool"},
                },
                "response_model": {
                    "name": "ResponseModel",
                    "description": "Response model for results",
                    "fields": {"output": "str"},
                },
            }
        ],
    )
    code = agent_creator.generate_code(config)
    assert "class RequestModel(BaseModel):" in code
    assert "class ResponseModel(BaseModel):" in code
    assert "class TestAgentWithModels(SyzygyAgent):" in code
    assert "async def process_data(self, input: str, option: bool) -> str:" in code


def test_generate_code_without_models(agent_creator):
    """Test code generation without any method models."""
    config = AgentConfig(
        name="SimpleAgent", description="Agent without models", task_type="simple"
    )
    code = agent_creator.generate_code(config)
    assert "class SimpleAgent(SyzygyAgent):" in code
    assert "def __init__(self):" in code
    assert "super().__init__(" in code


@pytest.mark.asyncio
async def test_create_agent_valid_params(agent_creator):
    """Test creating an agent with valid purpose and requirements."""

    class MockAgentCreator(AgentCreatorAgent):
        """Class MockAgentCreator."""

        async def run(self, prompt: str) -> dict:
            """Function run."""
            return {
                "function_call": {
                    "name": "create_agent_config",
                    "arguments": json.dumps(
                        {
                            "name": "MockAgent",
                            "description": "Mock agent for testing",
                            "task_type": "mock",
                            "model": "mock_model",
                            "complexity": 1,
                        }
                    ),
                }
            }

    mock_creator = MockAgentCreator()
    config = await mock_creator.create_agent(
        purpose="Test agent creation",
        requirements=["handle test tasks", "use test model"],
        context={"env": "test"},
    )
    assert isinstance(config, AgentConfig)
    assert config.name == "MockAgent"
    assert config.task_type == "mock"


@pytest.mark.asyncio
async def test_create_agent_invalid_result(agent_creator):
    """Test handling invalid result format from LLM."""

    class InvalidResultAgentCreator(AgentCreatorAgent):
        """Class InvalidResultAgentCreator."""

        async def run(self, prompt: str) -> str:
            """Function run."""
            return "invalid json string"

    invalid_creator = InvalidResultAgentCreator()
    with pytest.raises(json.JSONDecodeError):
        await invalid_creator.create_agent("Purpose", ["req1"])


def test_get_system_prompt(agent_creator):
    """Test system prompt content."""
    prompt = agent_creator.get_system_prompt()
    assert "Syzygy system" in prompt
    assert "Follow Python best practices" in prompt
