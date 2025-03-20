"""Tests for the base agent."""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any
from smolagents import DuckDuckGoSearchTool
from dewey.llm.agents.base_agent import DeweyBaseAgent, EngineTool, BaseAgent
from dewey.llm.llm_utils import LLMHandler
from dewey.core.engines.base import BaseEngine
import json
import logging


class MockEngine(BaseEngine):
    """Mock engine for testing."""

    def search(self, query: str) -> Dict:
        """Mock search method."""
        return {"results": [query]}

    def get_name(self) -> str:
        """Get engine name."""
        return "MockEngine"


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Provide a test configuration."""
    return {
        "llm": {
            "client": "deepinfra",
            "default_provider": "deepinfra",
            "providers": {
                "deepinfra": {
                    "api_key": "dummy_key",
                    "default_model": "google/gemini-2.0-flash-001",
                }
            },
        },
        "agents": {
            "test_agent": {"enabled": True, "version": "1.0"},
            "rag_search": {"enabled": True, "version": "1.0"},
            "sloan_optimize": {"enabled": True, "version": "1.0"},
            "ethical_analysis": {"enabled": True, "version": "1.0"},
            "unknown": {"enabled": True, "version": "1.0"},
        },
        "engines": {
            "mock_engine": {
                "enabled": True,
                "class": "tests.llm.agents.test_base_agent.MockEngine",
                "methods": ["search"],
                "params": {},
            }
        },
    }


class TestBaseAgent:
    """Test suite for BaseAgent functionality."""

    @pytest.fixture
    def base_agent(self, sample_config: Dict[str, Any]) -> BaseAgent:
        """Provide a BaseAgent instance for testing."""
        return BaseAgent(
            name="test_agent",
            description="Test agent",
            config_section="test_section",
            requires_db=True,
            enable_llm=True,
            config=sample_config
        )

    def test_initialization(self, base_agent: BaseAgent):
        """Test agent initialization with valid parameters."""
        assert base_agent.name == "test_agent"
        assert base_agent.description == "Test agent"
        assert base_agent.config_section == "test_section"
        assert base_agent.requires_db is True
        assert base_agent.enable_llm is True
        assert isinstance(base_agent.logger, logging.LoggerAdapter)

    def test_run_not_implemented(self, base_agent: BaseAgent):
        """Test run method raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            base_agent.run()

    def test_get_variable_names(self, base_agent: BaseAgent):
        """Test template variable extraction."""
        template = "Hello {{ name }}! Today is {{ day }}."
        variables = base_agent.get_variable_names(template)
        assert variables == {"name", "day"}

    def test_populate_template_valid(self, base_agent: BaseAgent):
        """Test template population with valid variables."""
        template = "Hello {{ name }}!"
        result = base_agent.populate_template(template, {"name": "World"})
        assert result == "Hello World!"

    def test_populate_template_missing_variable(self, base_agent: BaseAgent):
        """Test template population with missing variable."""
        template = "Hello {{ name }}!"
        with pytest.raises(Exception) as exc_info:
            base_agent.populate_template(template, {})
        assert "UndefinedError" in str(exc_info.type)

    def test_generate_code_success(self, base_agent: BaseAgent):
        """Test code generation with mock LLM."""
        mock_response = MagicMock()
        mock_response.text = "print('Hello World')"
        
        with patch.object(base_agent.llm_client, 'generate', return_value=mock_response):
            code = base_agent._generate_code("test prompt")
            assert code == "print('Hello World')"

    def test_generate_code_no_llm(self, base_agent: BaseAgent):
        """Test code generation without LLM client."""
        base_agent.llm_client = None
        with pytest.raises(ValueError, match="LLM client is not initialized"):
            base_agent._generate_code("test prompt")

    def test_execute_flow(self, base_agent: BaseAgent):
        """Test full execution flow with mock run."""
        with patch.object(base_agent, 'run'), \
             patch.object(base_agent, 'parse_args') as mock_parse, \
             patch.object(base_agent.logger, 'info') as mock_log:
            
            mock_parse.return_value = MagicMock()
            base_agent.execute()
            
            mock_log.assert_any_call("Starting execution of test_agent")
            mock_log.assert_any_call("Completed execution of test_agent")

    def test_execute_error_handling(self, base_agent: BaseAgent):
        """Test error handling during execution."""
        with patch.object(base_agent, 'run', side_effect=Exception("Test error")), \
             patch.object(base_agent.logger, 'error') as mock_log:
            
            with pytest.raises(SystemExit):
                base_agent.execute()
            
            mock_log.assert_called_with("Error executing script: Test error", exc_info=True)

    def test_to_dict_representation(self, base_agent: BaseAgent):
        """Test dictionary representation of agent."""
        agent_dict = base_agent.to_dict()
        assert agent_dict["name"] == "test_agent"
        assert agent_dict["description"] == "Test agent"
        assert agent_dict["config_section"] == "test_section"
        assert agent_dict["requires_db"] is True
        assert agent_dict["enable_llm"] is True
        assert isinstance(agent_dict["authorized_imports"], list)

class TestDeweyBaseAgent:
    """Test suite for DeweyBaseAgent."""

    def test_initialization_valid_config(self, sample_config: Dict[str, Any]):
        """Test successful initialization with valid config."""
        agent = DeweyBaseAgent(sample_config, "test_agent")
        assert isinstance(agent.llm_handler, LLMHandler)
        assert agent.task_type == "test_agent"
        assert any(isinstance(tool, DuckDuckGoSearchTool) for tool in agent.tools)

    def test_validate_config_missing_keys(self):
        """Test validation fails when required keys are missing."""
        invalid_config = {}
        with pytest.raises(ValueError, match="Missing required config key"):
            DeweyBaseAgent(invalid_config, "test_agent")

    def test_get_system_prompt_known_type(self, sample_config: Dict[str, Any]):
        """Test system prompt for known task type."""
        agent = DeweyBaseAgent(sample_config, "rag_search")
        assert "semantic search" in agent._get_system_prompt("rag_search")

    def test_get_system_prompt_unknown_type(self, sample_config: Dict[str, Any]):
        """Test default prompt for unknown task type."""
        agent = DeweyBaseAgent(sample_config, "unknown")
        assert agent._get_system_prompt("unknown") == "You are a helpful AI assistant."

    def test_get_tools_with_engines(self, sample_config: Dict[str, Any]):
        """Test tool registration from config."""
        agent = DeweyBaseAgent(sample_config, "test_agent")
        tools = agent._get_tools()
        assert len(tools) >= 1  # At least one tool (MockEngine_search)
        assert any(isinstance(t, EngineTool) for t in tools)

    def test_get_tools_missing_methods(self, sample_config: Dict[str, Any]):
        """Test method not found doesn't create tool."""
        config = sample_config.copy()
        del config["engines"]["mock_engine"]["methods"]
        agent = DeweyBaseAgent(config, "test_agent")
        tools = agent._get_tools()
        assert len(tools) == 1  # Only DuckDuckGoSearchTool
        assert isinstance(tools[0], DuckDuckGoSearchTool)  # Verify it's the search tool

    def test_get_engine_class_invalid_path(self, sample_config: Dict[str, Any]):
        """Test engine class loading with invalid path."""
        config = sample_config.copy()
        config["engines"]["mock_engine"]["class"] = "invalid.module.MockEngine"
        agent = DeweyBaseAgent(config, "test_agent")
        tools = agent._get_tools()
        assert len(tools) == 1  # Only DuckDuckGoSearchTool
        assert isinstance(tools[0], DuckDuckGoSearchTool)

    def test_get_tools_invalid_method(self, sample_config: Dict[str, Any]):
        """Test tool creation with invalid method name."""
        config = sample_config.copy()
        config["engines"]["mock_engine"]["methods"] = ["nonexistent_method"]
        agent = DeweyBaseAgent(config, "test_agent")
        tools = agent._get_tools()
        assert len(tools) == 1  # Only DuckDuckGoSearchTool
        assert isinstance(tools[0], DuckDuckGoSearchTool)

    def test_validate_config_malformed_section(self):
        """Test validation with malformed config section."""
        invalid_config = {
            "llm": {"client": "deepinfra", "default_provider": "deepinfra"},
            "agents": "not_a_dict",  # This should be a dict
        }
        with pytest.raises(ValueError, match="Invalid configuration"):
            DeweyBaseAgent(invalid_config, "test_agent")

    def test_system_prompt_override(self, sample_config: Dict[str, Any]):
        """Test system prompt override from config."""
        config = sample_config.copy()
        config["agents"]["test_agent"]["system_prompt"] = "Custom system prompt"
        agent = DeweyBaseAgent(config, "test_agent")
        assert agent._get_system_prompt("test_agent") == "Custom system prompt"

    def test_get_config_value_existing_path(self, sample_config: Dict[str, Any]):
        """Test existing config value retrieval."""
        agent = DeweyBaseAgent(sample_config, "test_agent")
        value = agent.get_config_value("llm.providers.deepinfra.default_model")
        assert value == "google/gemini-2.0-flash-001"

    def test_get_config_value_missing_path(self, sample_config: Dict[str, Any]):
        """Test missing config value returns default."""
        agent = DeweyBaseAgent(sample_config, "test_agent")
        value = agent.get_config_value("nonexistent.path", default="default")
        assert value == "default"


class TestEngineTool:
    """Test suite for EngineTool."""

    def test_tool_metadata(self):
        """Test metadata population from method signature."""
        engine = MockEngine()
        tool = EngineTool(engine, "search")
        assert tool.name == "MockEngine_search"
        assert tool.inputs == {
            "query": {"type": "string", "description": "Parameter query for search"}
        }

    def test_tool_forward_valid(self):
        """Test parameter validation and execution."""
        engine = MockEngine()
        tool = EngineTool(engine, "search")
        result = tool.forward(query="test")
        assert result == '{"results": ["test"]}'

    def test_tool_forward_missing_param(self):
        """Test missing required parameter raises error."""
        engine = MockEngine()
        tool = EngineTool(engine, "search")
        with pytest.raises(ValueError, match="Missing required parameter: query"):
            tool.forward()

    def test_tool_forward_error_handling(self):
        """Test error handling in forward method."""
        engine = MockEngine()
        tool = EngineTool(engine, "search")
        with patch.object(engine, "search", side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                tool.forward(query="test")


@pytest.mark.integration
class TestDeweyBaseAgentIntegration:
    """Integration tests for DeweyBaseAgent."""

    @pytest.fixture(autouse=True)
    def setup(self, sample_config: Dict[str, Any]):
        """Set up test environment."""
        self.agent = DeweyBaseAgent(sample_config, "test_agent")

    def test_full_toolchain(self):
        """Integration test for tool execution chain."""
        # Create a mock tool and add it to the agent
        engine = MockEngine()
        tool = EngineTool(engine, "search")
        self.agent.tools.append(tool)

        # Test tool invocation
        result = tool.forward(query="test query")
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "results" in parsed
        assert "test query" in parsed["results"]

    def test_system_prompt_overrides(self):
        """Test prompt customization via config."""
        # Add a custom prompt to the config
        self.agent.config["agents"]["test_agent"]["system_prompt"] = "Custom prompt"
        assert self.agent._get_system_prompt("test_agent") == "Custom prompt"

    def test_llm_handler_usage(self):
        """Test LLM response generation."""
        with patch.object(
            self.agent.llm_handler, "get_model", return_value=MagicMock()
        ) as mock_model:
            # Set up the mock model's response
            mock_model.return_value.generate.return_value = "mock_response"

            # Test that the agent uses the LLM handler correctly
            prompt_templates = {
                "system_prompt": self.agent._get_system_prompt("test_agent"),
                "user_prompt": "Test prompt",
            }
            assert isinstance(self.agent.llm_handler, LLMHandler)
            assert self.agent.prompt_templates is not None
