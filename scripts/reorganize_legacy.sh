#!/bin/bash

# Create necessary directories
mkdir -p src/dewey/core/db
mkdir -p src/dewey/core/analysis
mkdir -p src/dewey/core/utils
mkdir -p src/dewey/core/maintenance
mkdir -p src/dewey/core/bookkeeping
mkdir -p src/dewey/llm/agents
mkdir -p src/dewey/llm/api_clients
mkdir -p src/dewey/llm/prompts
mkdir -p src/dewey/llm/utils

echo "Moving files to core modules..."
# Database related
mv src/dewey/legacy/db_converters.py src/dewey/core/db/

# Analysis related
mv src/dewey/legacy/controversy_detection.py src/dewey/core/analysis/
mv src/dewey/legacy/validation.py src/dewey/core/analysis/
mv src/dewey/legacy/merge_data.py src/dewey/core/analysis/
mv src/dewey/legacy/log_analyzer.py src/dewey/core/analysis/

# Utils
mv src/dewey/legacy/admin.py src/dewey/core/utils/
mv src/dewey/legacy/api_manager.py src/dewey/core/utils/

# Maintenance
mv src/dewey/legacy/precommit_analyzer.py src/dewey/core/maintenance/

# Bookkeeping
mv src/dewey/legacy/mercury_importer.py src/dewey/core/bookkeeping/

echo "Moving files to LLM module..."
# LLM Agents
mv src/dewey/legacy/tagging_engine.py src/dewey/llm/agents/
mv src/dewey/legacy/next_question_suggestion.py src/dewey/llm/agents/
mv src/dewey/legacy/pro_chat.py src/dewey/llm/agents/
mv src/dewey/legacy/chat.py src/dewey/llm/agents/
mv src/dewey/legacy/e2b_code_interpreter.py src/dewey/llm/agents/

# API Clients
mv src/dewey/legacy/image_generation.py src/dewey/llm/api_clients/

# Prompts
mv src/dewey/legacy/prompts.py src/dewey/llm/prompts/

# LLM Utils
mv src/dewey/legacy/event_callback.py src/dewey/llm/utils/

# Create __init__.py files
touch src/dewey/core/db/__init__.py
touch src/dewey/core/analysis/__init__.py
touch src/dewey/core/utils/__init__.py
touch src/dewey/core/maintenance/__init__.py
touch src/dewey/core/bookkeeping/__init__.py
touch src/dewey/llm/agents/__init__.py
touch src/dewey/llm/api_clients/__init__.py
touch src/dewey/llm/prompts/__init__.py
touch src/dewey/llm/utils/__init__.py

echo "Legacy code reorganization complete!"
