from unittest.mock import Mock

import pytest
from dewey.core.base_script import BaseScript
from dewey.llm.agents.base_agent import BaseAgent


@pytest.fixture()
def basic_agent():
    return BaseAgent(
        name="TestAgent",
        description="Test Description",
        config_section="llm",
        requires_db=True,
    )


@pytest.fixture()
def unlimited_agent():
    return BaseAgent(name="UnlimitedAgent", disable_rate_limit=True, enable_llm=True)


def test_agent_initialization(basic_agent):
    assert isinstance(basic_agent, BaseScript)
    assert basic_agent.name == "TestAgent"
    assert basic_agent.description == "Test Description"
    assert basic_agent.config_section == "llm"
    assert basic_agent.requires_db is True
    assert basic_agent.enable_llm is True
    assert basic_agent.disable_rate_limit is False


def test_unlimited_agent_initialization(unlimited_agent):
    assert unlimited_agent.disable_rate_limit is True
    assert unlimited_agent.executor_type == "local"
    assert unlimited_agent.max_print_outputs_length == 1000


def test_to_dict_serialization(basic_agent):
    agent_dict = basic_agent.to_dict()
    assert agent_dict == {
        "name": "TestAgent",
        "description": "Test Description",
        "config_section": "llm",
        "requires_db": True,
        "enable_llm": True,
        "authorized_imports": [],
        "executor_type": "local",
        "executor_kwargs": {},
        "max_print_outputs_length": 1000,
        "disable_rate_limit": False,
    }


def test_generate_code_without_rate_limit(unlimited_agent, monkeypatch):
    mock_response = Mock()
    mock_response.text = "def test(): pass"

    mock_client = Mock()
    mock_client.generate.return_value = mock_response
    unlimited_agent.llm_client = mock_client

    result = unlimited_agent._generate_code("test prompt")
    assert result == "def test(): pass"
    mock_client.generate.assert_called_once_with("test prompt", disable_rate_limit=True)


def test_run_method_not_implemented(basic_agent):
    with pytest.raises(NotImplementedError):
        basic_agent.run()
