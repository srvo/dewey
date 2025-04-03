#!/bin/bash

# Create necessary directories
mkdir -p tests/dewey/core/{research/{analysis,engines,integration},db,tui,automation,crm,bookkeeping,utils}
mkdir -p tests/dewey/llm/{agents,models,prompts,utils}

# Move test files to their appropriate locations
mv tests/test_tui.py tests/dewey/core/tui/test_app.py
mv tests/test_tui_workers.py tests/dewey/core/tui/test_workers.py
mv tests/test_ethical_analyzer.py tests/dewey/core/research/analysis/test_ethical_analyzer.py
mv tests/test_duplicate_checker.py tests/dewey/core/utils/test_duplicate_checker.py
mv tests/test_search_analysis_integration.py tests/dewey/core/research/integration/test_search_analysis_integration.py

# Move any existing test files from old structure
if [ -d "tests/unit" ]; then
    mv tests/unit/* tests/dewey/core/
    rmdir tests/unit
fi

if [ -d "tests/src" ]; then
    mv tests/src/* tests/dewey/
    rmdir tests/src
fi

# Create empty __init__.py files
find tests/dewey -type d -exec touch {}/__init__.py \;

# Remove empty directories
find tests -type d -empty -delete

echo "Test reorganization complete!"
