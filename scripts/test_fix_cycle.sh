#!/bin/bash
# Test and Fix Cycle - Wrapper for test_and_fix.py script

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
    echo "  --conventions|-c FILE     Path to conventions file (default: CONVENTIONS.md)"
    echo "  --verbose|-v              Enable verbose output"
    echo "  --timeout|-T SECONDS      Timeout in seconds for processing each file (default: 120)"
    echo "  --fix-conftest|-f         Focus on fixing conftest.py files if they have syntax errors"
    echo "  --help|-h                 Display this help message and exit"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  $0 --dir src/dewey/core/db --verbose"
    echo "  $0 --dir src/dewey/core/db --fix-conftest --verbose  # Focus on fixing conftest.py"
}

# Check if no arguments were provided
if [ $# -eq 0 ]; then
    usage
    exit 1
fi

# Default values
TARGET_DIR=""
TEST_DIR="tests"
MODEL="deepinfra/google/gemini-2.0-flash-001"
MAX_ITERATIONS=5
DRY_RUN=false
CONVENTIONS_FILE="CONVENTIONS.md"
VERBOSE=false
TIMEOUT=120
FIX_CONFTEST=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir|-d)
            TARGET_DIR="$2"
            shift 2
            ;;
        --test-dir|-t)
            TEST_DIR="$2"
            shift 2
            ;;
        --model|-m)
            MODEL="$2"
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
        --conventions|-c)
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

# Check required arguments
if [ -z "$TARGET_DIR" ]; then
    echo -e "${RED}Error: --dir is required${NC}"
    usage
    exit 1
fi

# Check if directory exists
if [ ! -e "$TARGET_DIR" ]; then
    echo -e "${RED}Error: Directory does not exist: $TARGET_DIR${NC}"
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

# Build command arguments
ARGS=""
ARGS+=" --dir \"$TARGET_DIR\""
ARGS+=" --test-dir \"$TEST_DIR\""
ARGS+=" --model \"$MODEL\""
ARGS+=" --max-iterations $MAX_ITERATIONS"
ARGS+=" --timeout $TIMEOUT"
ARGS+=" --conventions-file \"$CONVENTIONS_FILE\""

if [ "$DRY_RUN" = true ]; then
    ARGS+=" --dry-run"
fi

if [ "$VERBOSE" = true ]; then
    ARGS+=" --verbose"
fi

if [ "$FIX_CONFTEST" = true ]; then
    echo -e "${YELLOW}Focus mode: Will prioritize fixing conftest.py files if they have syntax errors${NC}"
    
    # First, check if there's a syntax error in any conftest.py file
    CONFTEST_FILES=$(find "$TEST_DIR" -name "conftest.py" -type f)
    
    if [ -z "$CONFTEST_FILES" ]; then
        echo -e "${YELLOW}No conftest.py files found in $TEST_DIR${NC}"
    else
        echo -e "Found conftest.py files:"
        for CONFTEST in $CONFTEST_FILES; do
            echo -e "  - $CONFTEST"
            
            # Try to compile the conftest file to check for syntax errors
            SYNTAX_CHECK=$(python -c "import ast; ast.parse(open('$CONFTEST').read())" 2>&1)
            
            if [ $? -ne 0 ]; then
                echo -e "${RED}Syntax error in $CONFTEST:${NC}"
                echo -e "$SYNTAX_CHECK"
                
                # Try to fix the syntax error using Aider directly
                echo -e "${YELLOW}Attempting to fix syntax error in $CONFTEST...${NC}"
                python "$SCRIPT_DIR/aider_refactor.py" --dir "$CONFTEST" --model "$MODEL" --verbose \
                    --custom-prompt "Fix the syntax error in this conftest.py file. Make sure the file is valid Python code that can be imported without syntax errors."
                
                # Check if the fix worked
                SYNTAX_CHECK_AFTER=$(python -c "import ast; ast.parse(open('$CONFTEST').read())" 2>&1)
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}Successfully fixed syntax error in $CONFTEST${NC}"
                else
                    echo -e "${RED}Failed to fix syntax error in $CONFTEST${NC}"
                    echo -e "${RED}You may need to fix this file manually before running the tests${NC}"
                    
                    if [ "$DRY_RUN" = false ]; then
                        echo -e "${RED}Exiting due to syntax error in conftest.py${NC}"
                        exit 1
                    fi
                fi
            else
                echo -e "${GREEN}No syntax errors found in $CONFTEST${NC}"
            fi
        done
    fi
fi

# Print banner
echo -e "
${BOLD}==============================================
TEST AND FIX CYCLE
==============================================
Target: ${BLUE}$TARGET_DIR${NC}
Test directory: ${BLUE}$TEST_DIR${NC}
Model: ${BLUE}$MODEL${NC}
Max iterations: ${BLUE}$MAX_ITERATIONS${NC}
Dry run: ${BLUE}$DRY_RUN${NC}
Started at: $(date)
=============================================${NC}
"

# Run the command
echo -e "${BOLD}Running test_and_fix.py...${NC}"
eval "python \"$SCRIPT_DIR/test_and_fix.py\"$ARGS"
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