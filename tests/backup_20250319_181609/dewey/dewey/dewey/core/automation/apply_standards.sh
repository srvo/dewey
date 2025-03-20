#!/bin/bash

# Usage: ./scripts/apply_standards.sh <target_directory>

set -eo pipefail

TARGET_DIR="${1}"
CONVENTIONS_FILE="../.aider/CONVENTIONS.md"

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: Target directory '$TARGET_DIR' does not exist"
    exit 1
fi

if [[ ! -f "$CONVENTIONS_FILE" ]]; then
    echo "Error: Conventions file '$CONVENTIONS_FILE' not found"
    exit 1
fi

# Define the base aider command
AIDER_CMD="aider --no-show-model-warnings --model gemini/gemini-2.0-flash --yes"

# Process all Python files recursively
find "$TARGET_DIR" -type f -name '*.py' | while read -r file; do
    echo "Processing $file..."
    
    $AIDER_CMD \
        --message "Review the coding conventions in CONVENTIONS.md and update the code to strictly comply with all style guidelines including: 
        - Adding Google-style docstrings with type hints
        - Ensuring PEP 8 compliance
        - Improving variable naming
        - Adding error handling
        - Breaking down complex functions
        - Adding comments for clarity
        Preserve all existing functionality while improving code quality." \
        "$file" \
        "$CONVENTIONS_FILE"
done

echo "Standards application complete."
