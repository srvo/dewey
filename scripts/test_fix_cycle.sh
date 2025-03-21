#!/bin/bash
# Test-Fix Cycle Script
# Runs tests and fixes code in a cycle until tests pass

set -e  # Exit on any error

# Colors for output
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
BOLD="\033[1m"
NC="\033[0m" # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Print usage information
function usage() {
    echo -e "${BOLD}Usage:${NC} $0 [options]"
    echo ""
    echo "Run tests for a directory and fix any failing tests using Aider."
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  --dir|-d DIR              Directory to process (required)"
    echo "  --test-dir|-t DIR         Directory containing tests (default: tests)"
    echo "  --model|-m MODEL          Model to use for refactoring (default: deepinfra/google/gemini-2.0-flash-001)"
    echo "  --max-iterations|-i NUM   Maximum number of test-fix iterations (default: 5)"
    echo "  --dry-run|-n              Don't make any changes, just show what would be done"
    echo "  --conventions-file|-c FILE Path to conventions file (default: CONVENTIONS.md)"
    echo "  --verbose|-v              Enable verbose output"
    echo "  --timeout|-T SECONDS      Timeout in seconds for processing each file (default: 120)"
    echo "  --fix-conftest|-f         Focus on fixing conftest.py files if they have syntax errors"
    echo "  --no-persist-session      Disable persistent sessions"
    echo "  --no-testability          Don't modify source files for testability"
    echo "  --testable-only           Only focus on making source files testable, don't run tests"
    echo "  --generate-then-fix       First generate tests with aider_refactor_and_test.py, then fix them"
    echo "  --fix-only                Skip initial test generation and only fix existing tests"
    echo "  --help|-h                 Display this help message and exit"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  $0 --dir src/dewey/core/db --verbose"
    echo "  $0 --dir src/dewey/core/db --fix-conftest --verbose  # Focus on fixing conftest.py"
    echo "  $0 --dir src/dewey/core/db --testable-only --verbose  # Only make source files testable"
    echo "  $0 --dir src/dewey/core/db --generate-then-fix       # Generate tests and then fix them"
}

# Check if no arguments were provided
if [ $# -eq 0 ]; then
    usage
    exit 1
fi

# Default values
DIR=""
TEST_DIR="tests"
MODEL_NAME="deepinfra/google/gemini-2.0-flash-001"
MAX_ITERATIONS=5
DRY_RUN=false
CONVENTIONS_FILE="CONVENTIONS.md"
VERBOSE=false
TIMEOUT=120
FIX_CONFTEST=false
PERSIST_SESSION=true  # Default to using persistent sessions
NO_TESTABILITY=false  # Default to modifying source files for testability
TESTABLE_ONLY=false   # Default to running tests as well
GENERATE_THEN_FIX=false  # Default to not generating tests first
FIX_ONLY=false  # Default to generating tests if needed

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir|-d)
            DIR="$2"
            shift 2
            ;;
        --test-dir|-t)
            TEST_DIR="$2"
            shift 2
            ;;
        --model|-m)
            MODEL_NAME="$2"
            shift 2
            ;;
        --max-iterations|-i)
            MAX_ITERATIONS="$2"
            shift 2
            ;;
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        --conventions-file|-c)
            CONVENTIONS_FILE="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --timeout|-T)
            TIMEOUT="$2"
            shift 2
            ;;
        --fix-conftest|-f)
            FIX_CONFTEST=true
            shift
            ;;
        --no-persist-session)
            PERSIST_SESSION=false
            shift
            ;;
        --no-testability)
            NO_TESTABILITY=true
            shift
            ;;
        --testable-only)
            TESTABLE_ONLY=true
            shift
            ;;
        --generate-then-fix)
            GENERATE_THEN_FIX=true
            shift
            ;;
        --fix-only)
            FIX_ONLY=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Check if directory is provided
if [ -z "$DIR" ]; then
    echo -e "${RED}Error: --dir is required${NC}"
    usage
    exit 1
fi

# Check if directory exists
if [ ! -e "$DIR" ]; then
    echo -e "${RED}Error: Directory does not exist: $DIR${NC}"
    exit 1
fi

# Check for required dependencies
echo -e "${BOLD}Checking dependencies...${NC}"
missing_deps=false

if ! python -c "import pytest" 2> /dev/null; then
    echo -e "${YELLOW}Warning: pytest not found. Installing...${NC}"
    pip install pytest pytest-mock pytest-cov pytest-asyncio
fi

if ! python -c "import flake8" 2> /dev/null; then
    echo -e "${YELLOW}Warning: flake8 not found. Installing...${NC}"
    pip install flake8
fi

if ! python -c "import aider" 2> /dev/null; then
    echo -e "${YELLOW}Warning: aider not found. Installing...${NC}"
    pip install aider-chat
fi

# Check if all test_and_fix.py dependencies are importable
if ! python -c "from pathlib import Path; import re, argparse, logging, os, subprocess, sys" 2> /dev/null; then
    echo -e "${RED}Error: Basic Python dependencies are missing${NC}"
    exit 1
fi

echo -e "${GREEN}All dependencies are installed${NC}"

# Prepare verbose flag
VERBOSE_FLAG=""
if [ "$VERBOSE" = true ]; then
    VERBOSE_FLAG="--verbose"
fi

# Prepare dry-run flag
DRY_RUN_FLAG=""
if [ "$DRY_RUN" = true ]; then
    DRY_RUN_FLAG="--dry-run"
fi

# Prepare persist-session flag
PERSIST_SESSION_FLAG=""
if [ "$PERSIST_SESSION" = true ]; then
    PERSIST_SESSION_FLAG="--persist-session"
fi

# Prepare no-testability flag
NO_TESTABILITY_FLAG=""
if [ "$NO_TESTABILITY" = true ]; then
    NO_TESTABILITY_FLAG="--no-testability"
fi

# Print start message
echo -e "
${BOLD}==============================================
TEST AND FIX CYCLE
==============================================
Target: ${BLUE}$DIR${NC}
Test directory: ${BLUE}$TEST_DIR${NC}
Model: ${BLUE}$MODEL_NAME${NC}
Max iterations: ${BLUE}$MAX_ITERATIONS${NC}
Dry run: ${BLUE}$DRY_RUN${NC}
Persistent session: ${BLUE}$PERSIST_SESSION${NC}
Modify source for testability: ${BLUE}$([ "$NO_TESTABILITY" = false ] && echo "Yes" || echo "No")${NC}
Testable-only mode: ${BLUE}$TESTABLE_ONLY${NC}
Generate tests first: ${BLUE}$GENERATE_THEN_FIX${NC}
Fix tests only: ${BLUE}$FIX_ONLY${NC}
Started at: $(date)
=============================================${NC}
"

# Create session directory if it doesn't exist
SESSION_DIR=".aider/sessions"
mkdir -p "$SESSION_DIR"

# Generate a unique session identifier based on the directory being processed
SESSION_ID=$(echo "$DIR" | md5sum | cut -d' ' -f1)
SESSION_FILE="$SESSION_DIR/$SESSION_ID.json"

# First, fix the test generation formatting error in aider_refactor_and_test.py if needed
if [ "$GENERATE_THEN_FIX" = true ] && [ "$FIX_ONLY" = false ]; then
    echo -e "${YELLOW}Checking if aider_refactor_and_test.py has string formatting errors...${NC}"
    # Create a temporary patch to fix the string formatting issue if it exists
    grep -q "Invalid format specifier ' \[1, 2, 3\]'" "$SCRIPT_DIR/aider_refactor_and_test.py" || {
        # Create a temporary patch
        cat > /tmp/fix_formatter.patch << 'EOF'
--- aider_refactor_and_test.py
+++ aider_refactor_and_test.py
@@ -190,7 +190,11 @@
         return mock_conn

     @pytest.fixture
-    def mock_config():
+    def mock_config() -> Dict[str, Any]:
         """Create a mock configuration."""
         return {{
             "settings": {{"key": "value"}},
EOF
        # Apply the patch if needed
        if [ -f /tmp/fix_formatter.patch ]; then
            echo -e "${YELLOW}Fixing string formatting in aider_refactor_and_test.py...${NC}"
            cd "$SCRIPT_DIR" && patch -p0 < /tmp/fix_formatter.patch || echo -e "${YELLOW}Patch didn't apply cleanly, probably already fixed${NC}"
            cd - > /dev/null
        fi
    }
fi

# If we're in generate-then-fix mode, we'll generate tests first
if [ "$GENERATE_THEN_FIX" = true ] && [ "$FIX_ONLY" = false ]; then
    echo -e "${GREEN}Generating tests for $DIR using aider_refactor_and_test.py...${NC}"
    
    # Build the command
    GEN_CMD="python \"$SCRIPT_DIR/aider_refactor_and_test.py\" --src-dir \"$DIR\" --test-dir \"$TEST_DIR\" --model \"$MODEL_NAME\" $VERBOSE_FLAG $DRY_RUN_FLAG --skip-refactor $NO_TESTABILITY_FLAG --conventions-file \"$CONVENTIONS_FILE\""
    
    # Execute the test generation
    echo -e "${BLUE}Executing: $GEN_CMD${NC}"
    eval $GEN_CMD || {
        echo -e "${YELLOW}Warning: Test generation had some issues. We'll fix them in the next step.${NC}"
    }

    echo -e "${GREEN}Generated tests. Now proceeding to fix any issues...${NC}"
fi

# If it's a directory, handle files individually first
if [ -d "$DIR" ] && [ "$TESTABLE_ONLY" = false ] && [ "$FIX_ONLY" = false ]; then
    echo -e "${GREEN}Processing directory: $DIR${NC}"
    
    # Find Python files in the directory
    PYTHON_FILES=$(find "$DIR" -name "*.py")
    NUM_FILES=$(echo "$PYTHON_FILES" | wc -l | tr -d ' ')
    
    if [ "$NUM_FILES" -eq 0 ]; then
        echo -e "${YELLOW}No Python files found in $DIR${NC}"
    else
        echo -e "Found $NUM_FILES Python files in $DIR"
        
        # Process each Python file individually first
        for PY_FILE in $PYTHON_FILES; do
            echo -e "${GREEN}Processing file: $PY_FILE${NC}"
            
            # If in testable-only mode, use our improved refactor script to focus on testability
            if [ "$TESTABLE_ONLY" = true ]; then
                echo -e "${YELLOW}Making $PY_FILE more testable...${NC}"
                python "$SCRIPT_DIR/aider_refactor_and_test.py" --src-dir "$PY_FILE" --test-dir "$TEST_DIR" --model "$MODEL_NAME" $VERBOSE_FLAG $DRY_RUN_FLAG --skip-refactor $PERSIST_SESSION_FLAG --conventions-file "$CONVENTIONS_FILE" $NO_TESTABILITY_FLAG
                continue
            fi
            
            # Run flake8 to check for syntax errors first
            python -m flake8 "$PY_FILE" >/dev/null 2>&1 || {
                echo -e "${YELLOW}Fixing flake8 issues in $PY_FILE${NC}"
                python "$SCRIPT_DIR/aider_refactor.py" --dir "$PY_FILE" --model "$MODEL_NAME" $VERBOSE_FLAG $DRY_RUN_FLAG $PERSIST_SESSION_FLAG --conventions-file "$CONVENTIONS_FILE" --timeout "$TIMEOUT" --session-dir "$SESSION_DIR"
            }
        done
    fi
fi

# If we're in testable-only mode, we're done
if [ "$TESTABLE_ONLY" = true ]; then
    echo -e "${GREEN}Completed testable-only mode processing${NC}"
    exit 0
fi

# Find generated test files that need to be fixed
if [ -d "$TEST_DIR/unit" ]; then
    TEST_MODULE_PATH=$(echo "$DIR" | sed 's|^src/||' | sed 's|/|.|g')
    TEST_PATH="$TEST_DIR/unit/$TEST_MODULE_PATH"
    
    if [ -d "$TEST_PATH" ]; then
        echo -e "${GREEN}Checking for syntax errors in generated test files...${NC}"
        TEST_FILES=$(find "$TEST_PATH" -name "test_*.py")
        
        for TEST_FILE in $TEST_FILES; do
            echo -e "${BLUE}Checking $TEST_FILE...${NC}"
            # Try to compile the test file to check for syntax errors
            python -m py_compile "$TEST_FILE" 2>/dev/null || {
                echo -e "${YELLOW}Fixing syntax errors in $TEST_FILE...${NC}"
                python "$SCRIPT_DIR/aider_refactor.py" --dir "$TEST_FILE" --model "$MODEL_NAME" $VERBOSE_FLAG $DRY_RUN_FLAG $PERSIST_SESSION_FLAG --conventions-file "$CONVENTIONS_FILE" --timeout "$TIMEOUT" --session-dir "$SESSION_DIR"
            }
        done
    fi
fi

# Then run the full test and fix cycle on the directory
echo -e "${BOLD}Running test_and_fix.py...${NC}"
eval "python \"$SCRIPT_DIR/test_and_fix.py\" --dir \"$DIR\" --max-iterations $MAX_ITERATIONS --model \"$MODEL_NAME\" $VERBOSE_FLAG $DRY_RUN_FLAG $PERSIST_SESSION_FLAG --conventions-file \"$CONVENTIONS_FILE\" --timeout $TIMEOUT --session-dir \"$SESSION_DIR\" $NO_TESTABILITY_FLAG"
RESULT=$?

# Print footer
echo -e "
${BOLD}==============================================
PROCESS COMPLETED
==============================================
Finished at: $(date)${NC}
"

# Display final message based on exit code
if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ SUCCESS: Tests are passing!${NC}"
else
    echo -e "${RED}❌ FAILURE: Tests are still failing.${NC}"
fi

exit $RESULT 