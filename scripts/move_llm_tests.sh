#!/bin/bash

# Create necessary directories if they don't exist
mkdir -p tests/dewey/llm/{agents,models,api_clients,utils}

# Move agent-related tests
mv tests/llm/agents/test_base_agent.py tests/dewey/llm/agents/
mv tests/llm/agents/test_sloan_optimizer.py tests/dewey/llm/agents/
mv tests/llm/test_agent_creator_agent.py tests/dewey/llm/agents/

# Move model-related tests
mv tests/llm/test_gemini.py tests/dewey/llm/models/
mv tests/llm/test_gemini_client.py tests/dewey/llm/models/

# Move API client tests
mv tests/llm/test_deepinfra.py tests/dewey/llm/api_clients/
mv tests/llm/api_clients/* tests/dewey/llm/api_clients/ 2>/dev/null || true

# Move utility tests
mv tests/llm/test_tool_launcher.py tests/dewey/llm/utils/
mv tests/llm/test_llm_utils.py tests/dewey/llm/utils/
mv tests/llm/test_exceptions.py tests/dewey/llm/utils/

# Move conftest and init
mv tests/llm/conftest.py tests/dewey/llm/
mv tests/llm/__init__.py tests/dewey/llm/

# Create __init__.py files in all directories
find tests/dewey/llm -type d -exec touch {}/__init__.py \;

# Remove old directory structure
rm -rf tests/llm

echo "LLM test files moved successfully!"
