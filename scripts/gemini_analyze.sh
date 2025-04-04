#!/bin/bash
# gemini_analyze.sh - Run pre-commit and analyze with Gemini

# Set -e to exit on error, -x for debugging (uncomment for verbose debugging)
# set -e
# set -x

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  echo "Loading environment variables from .env file..."
  # Read .env file line by line, ignoring comments and empty lines
  while IFS= read -r line || [ -n "$line" ]; do
    # Skip comments and empty lines
    [[ $line =~ ^#.*$ || -z $line ]] && continue
    # Export variables - split at the first equals sign
    export "${line?}"
  done < .env
fi

# Check for API keys - try multiple providers
if [ -z "$DEEPINFRA_API_KEY" ] && [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
  echo "Error: No LLM API keys found. Please set one of these environment variables:"
  echo "- DEEPINFRA_API_KEY"
  echo "- GEMINI_API_KEY"
  echo "- GOOGLE_API_KEY"
  echo "You can add them to your .env file or export them in your terminal."
  exit 1
else
  # Show which key we're using (without showing the actual key)
  if [ -n "$DEEPINFRA_API_KEY" ]; then
    echo "Using DEEPINFRA_API_KEY from environment"
  elif [ -n "$GEMINI_API_KEY" ]; then
    echo "Using GEMINI_API_KEY from environment"
  elif [ -n "$GOOGLE_API_KEY" ]; then
    echo "Using GOOGLE_API_KEY from environment"
  fi
fi

# Set output file
PRECOMMIT_OUTPUT=${1:-"precommit_output.log"}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ANALYSIS_FILE="precommit_analysis_${TIMESTAMP}.md"

echo "Running pre-commit hooks and capturing output..."
echo "This might take a few minutes depending on the size of your codebase"

# Run pre-commit hooks and capture the output
echo "Running pre-commit hooks and capturing output to $PRECOMMIT_OUTPUT"
pre-commit run --all-files > "$PRECOMMIT_OUTPUT" 2>&1

echo "Pre-commit complete. Analyzing results..."
echo "Output saved to: $PRECOMMIT_OUTPUT"

# Make sure src is in the Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Now use Deepinfra's REST API directly for simplicity and reliability
# This bypasses potential issues with the Python client
API_KEY=""
MODEL=""

if [ -n "$DEEPINFRA_API_KEY" ]; then
  API_KEY="$DEEPINFRA_API_KEY"
  MODEL="deepinfra/google/gemini-2.0-flash-001"
elif [ -n "$GEMINI_API_KEY" ]; then
  API_KEY="$GEMINI_API_KEY"
  MODEL="gemini-1.5-pro"
elif [ -n "$GOOGLE_API_KEY" ]; then
  API_KEY="$GOOGLE_API_KEY"
  MODEL="gemini-1.5-pro"
fi

echo "Using model: $MODEL"

# Create the system prompt
SYSTEM_PROMPT=$(cat <<'EOF'
You are an expert code quality analyst. Your task is to:

1. Analyze the raw output from pre-commit hooks
2. Identify all code quality issues and categorize them by type and severity
3. Create a comprehensive, actionable plan for fixing these issues
4. Prioritize issues based on their impact and difficulty to fix
5. Provide specific code examples for common fixes

The output should be formatted in Markdown with clear sections:

1. Executive Summary - A brief overview of the issues found
2. High Priority Issues - Critical issues that need immediate attention
3. Medium Priority Issues - Important issues to address after high priority ones
4. Low Priority Issues - Issues that can be addressed later
5. File-by-File Analysis - Detailed breakdown of issues by file
6. Common Patterns - Recurring issues and how to fix them systematically
7. Implementation Plan - Step-by-step approach to tackle all issues

For each issue, include:
- File path and line number
- Error code and description
- Recommended fix with code example when applicable
- Potential impact of the issue

Your goal is to provide a clear, actionable roadmap that developers can follow to improve code quality.
EOF
)

# Read the pre-commit output file content
if [ -f "$PRECOMMIT_OUTPUT" ]; then
  PRECOMMIT_CONTENT=$(cat "$PRECOMMIT_OUTPUT")
else
  echo "Error: Pre-commit output file not found: $PRECOMMIT_OUTPUT"
  exit 1
fi

# Create the user prompt
USER_PROMPT="Here is the raw output from running pre-commit hooks on our codebase:

\`\`\`
$PRECOMMIT_CONTENT
\`\`\`

Please analyze this output and create a comprehensive, actionable plan for fixing the identified issues."

# Directly call the DeepInfra API endpoint
echo "Sending request to LLM API..."
if [ "$MODEL" == "deepinfra/google/gemini-2.0-flash-001" ]; then
  # Create a temporary JSON file for the request to avoid escaping issues
  REQUEST_JSON=$(mktemp)
  cat > "$REQUEST_JSON" << EOF
  {
    "input": {
      "messages": [
        {"role": "system", "content": $(printf '%s' "$SYSTEM_PROMPT" | jq -R -s .)},
        {"role": "user", "content": $(printf '%s' "$USER_PROMPT" | jq -R -s .)}
      ]
    },
    "stream": false
  }
EOF

  RESPONSE=$(curl -s -X POST "https://api.deepinfra.com/v1/inference/google/gemini-2.0-flash-001" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d @"$REQUEST_JSON")
  
  # Clean up the temp file
  rm -f "$REQUEST_JSON"
else
  # For Google's Gemini API (via Google AI Studio)
  # Create a temporary JSON file for the request to avoid escaping issues
  REQUEST_JSON=$(mktemp)
  cat > "$REQUEST_JSON" << EOF
  {
    "contents": [
      {"role": "user", "parts": [{"text": $(printf '%s\n\n%s' "$SYSTEM_PROMPT" "$USER_PROMPT" | jq -R -s .)}]}
    ]
  }
EOF

  RESPONSE=$(curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent" \
    -H "Content-Type: application/json" \
    -H "x-goog-api-key: $API_KEY" \
    -d @"$REQUEST_JSON")
  
  # Clean up the temp file
  rm -f "$REQUEST_JSON"
fi

# Save the raw response for debugging
RESPONSE_FILE="api_response_${TIMESTAMP}.json"
echo "$RESPONSE" > "$RESPONSE_FILE"
echo "Raw API response saved to $RESPONSE_FILE"

# Extract the content from the response
if [ "$MODEL" == "deepinfra/google/gemini-2.0-flash-001" ]; then
  # Install jq if not available
  if ! command -v jq &> /dev/null; then
    echo "jq is required for JSON parsing. Please install it with 'brew install jq' (macOS) or 'apt install jq' (Linux)"
    exit 1
  fi
  
  # Parse the DeepInfra response using jq
  CONTENT=$(echo "$RESPONSE" | jq -r '.output.message.content // empty')
else
  # Parse the Google Gemini response using jq
  CONTENT=$(echo "$RESPONSE" | jq -r '.candidates[0].content.parts[0].text // empty')
fi

# Check if we got content back
if [ -z "$CONTENT" ]; then
  echo "Error: No content returned from API. Raw response:"
  echo "$RESPONSE" | jq '.' || echo "$RESPONSE"  # Pretty print JSON if possible
  exit 1
fi

# Write the content to the file
echo "Writing analysis to $ANALYSIS_FILE..."
echo -e "$CONTENT" > "$ANALYSIS_FILE"

# Verify the file was created
if [ -f "$ANALYSIS_FILE" ]; then
  echo "Analysis complete! Results written to: $ANALYSIS_FILE"
  
  # Create a consistent symlink
  ln -sf "$ANALYSIS_FILE" "latest_precommit_analysis.md"
  echo "Created symlink: latest_precommit_analysis.md"
  
  echo "Command to open the analysis:"
  echo "   open latest_precommit_analysis.md   # macOS"
  echo "   xdg-open latest_precommit_analysis.md   # Linux"
else
  echo "Error: Failed to create analysis file: $ANALYSIS_FILE"
  exit 1
fi 