#!/bin/bash

# Script to run code quality checks and fixes on Python files
# It combines black formatting, flake8 linting, and automatic fixes for common issues

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default values
TARGET_DIR=""
CHECK_ONLY=false
MAX_LINE_LENGTH=88
VERBOSE=false
USE_AIDER=false
MODEL="deepinfra/google/gemini-2.0-flash-001"
CONVENTIONS_FILE="CONVENTIONS.md"
CHECK_FOR_URLS=false

# Print usage information
usage() {
    echo -e "${BOLD}USAGE:${NC} $0 [OPTIONS] --dir DIRECTORY"
    echo ""
    echo "OPTIONS:"
    echo "  --dir, -d DIRECTORY      Directory containing Python files to process (required)"
    echo "  --check-only, -c         Only check for issues without making changes"
    echo "  --max-line-length NUM    Maximum line length for flake8 (default: 88)"
    echo "  --verbose, -v            Enable verbose output"
    echo "  --use-aider, -a          Use Aider to fix any remaining issues after linting"
    echo "  --model MODEL            Model to use with Aider (default: deepinfra/google/gemini-2.0-flash-001)"
    echo "  --conventions FILE       Path to conventions file (default: CONVENTIONS.md)"
    echo "  --check-for-urls         Enable URL detection in Aider (default: disabled)"
    echo "  --help, -h               Display this help message and exit"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir|-d)
            TARGET_DIR="$2"
            shift 2
            ;;
        --check-only|-c)
            CHECK_ONLY=true
            shift
            ;;
        --max-line-length)
            MAX_LINE_LENGTH="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --use-aider|-a)
            USE_AIDER=true
            shift
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --conventions)
            CONVENTIONS_FILE="$2"
            shift 2
            ;;
        --check-for-urls)
            CHECK_FOR_URLS=true
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

# Check for required directory
if [ -z "$TARGET_DIR" ]; then
    echo -e "${RED}Error: Missing required argument: --dir${NC}"
    usage
    exit 1
fi

# Check if directory exists
if [ ! -e "$TARGET_DIR" ]; then
    echo -e "${RED}Error: Path does not exist: $TARGET_DIR${NC}"
    exit 1
fi

# Check if it's a file or directory
IS_FILE=false
if [ -f "$TARGET_DIR" ]; then
    IS_FILE=true
    echo -e "${YELLOW}Note: Processing single file: $TARGET_DIR${NC}"
fi

# Make sure we have all required tools
echo -e "${BOLD}Checking dependencies...${NC}"
missing_deps=false

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    missing_deps=true
fi

if ! python3 -c "import black" 2> /dev/null; then
    echo -e "${YELLOW}Warning: black not found. Installing...${NC}"
    pip install black
fi

if ! python3 -c "import flake8" 2> /dev/null; then
    echo -e "${YELLOW}Warning: flake8 not found. Installing...${NC}"
    pip install flake8
fi

if [ "$USE_AIDER" = true ] && ! python3 -c "import aider" 2> /dev/null; then
    echo -e "${YELLOW}Warning: aider not found. Installing...${NC}"
    pip install aider-chat
fi

if [ "$missing_deps" = true ]; then
    echo -e "${RED}Error: Please install the missing dependencies and try again.${NC}"
    exit 1
fi

# Build base command arguments (common to both scripts)
BASE_ARGS="--dir \"$TARGET_DIR\""
if [ "$VERBOSE" = true ]; then
    BASE_ARGS="$BASE_ARGS --verbose"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Make scripts executable if needed
chmod +x "$SCRIPT_DIR/code_quality.py" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/fix_common_issues.py" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/aider_refactor.py" 2>/dev/null || true

echo -e "${BOLD}==============================================${NC}"
echo -e "${BOLD}PYTHON CODE QUALITY IMPROVEMENT PROCESS${NC}"
echo -e "${BOLD}==============================================${NC}"
echo -e "Target directory: ${BOLD}$TARGET_DIR${NC}"
echo -e "Mode: ${BOLD}$([ "$CHECK_ONLY" = true ] && echo "Check only" || echo "Fix issues")${NC}"
echo -e "Max line length: ${BOLD}$MAX_LINE_LENGTH${NC}"
echo -e "Use Aider: ${BOLD}$([ "$USE_AIDER" = true ] && echo "Yes" || echo "No")${NC}"
echo -e "URL detection: ${BOLD}$([ "$CHECK_FOR_URLS" = true ] && echo "Enabled" || echo "Disabled")${NC}"
echo -e "Started at: ${BOLD}$(date)${NC}"
echo -e "${BOLD}==============================================${NC}"
echo ""

# Step 1: Fix common issues first
echo -e "${BOLD}STEP 1: Fixing common Python issues...${NC}"
if [ "$CHECK_ONLY" = true ]; then
    eval "python3 \"$SCRIPT_DIR/fix_common_issues.py\" $BASE_ARGS --dry-run"
else
    eval "python3 \"$SCRIPT_DIR/fix_common_issues.py\" $BASE_ARGS"
fi
echo ""

# Step 2: Run black and flake8
echo -e "${BOLD}STEP 2: Running black formatter and flake8...${NC}"
CODE_QUALITY_ARGS="$BASE_ARGS --max-line-length $MAX_LINE_LENGTH"
if [ "$CHECK_ONLY" = true ]; then
    CODE_QUALITY_ARGS="$CODE_QUALITY_ARGS --check-only"
fi
eval "python3 \"$SCRIPT_DIR/code_quality.py\" $CODE_QUALITY_ARGS"
echo ""

# Step 3: Run Aider for remaining issues (if enabled)
if [ "$USE_AIDER" = true ] && [ "$CHECK_ONLY" = false ]; then
    echo -e "${BOLD}STEP 3: Using Aider to fix remaining issues...${NC}"
    # Create a temporary file to capture flake8 output
    FLAKE8_OUTPUT=$(mktemp)
    
    # Run flake8 to capture remaining issues
    if [ "$IS_FILE" = true ]; then
        flake8 "$TARGET_DIR" --max-line-length="$MAX_LINE_LENGTH" > "$FLAKE8_OUTPUT" 2>/dev/null || true
    else
        find "$TARGET_DIR" -name "*.py" -exec flake8 {} --max-line-length="$MAX_LINE_LENGTH" \; > "$FLAKE8_OUTPUT" 2>/dev/null || true
    fi
    
    # If there are remaining issues, run aider to fix them
    if [ -s "$FLAKE8_OUTPUT" ]; then
        ISSUE_COUNT=$(wc -l < "$FLAKE8_OUTPUT")
        echo -e "Found ${ISSUE_COUNT} remaining flake8 issues. Using Aider to fix them..."
        
        # Show a sample of issues if verbose
        if [ "$VERBOSE" = true ]; then
            echo -e "\nSample of remaining issues:"
            head -n 5 "$FLAKE8_OUTPUT"
            if [ "$ISSUE_COUNT" -gt 5 ]; then
                echo -e "... and $(( ISSUE_COUNT - 5 )) more issues.\n"
            fi
        fi
        
        # Set environment variables for Aider to run non-interactively
        export AIDER_NO_AUTO_COMMIT=1
        export AIDER_CHAT_HISTORY_FILE=/dev/null
        export AIDER_NO_INPUT=1
        export AIDER_QUIET=1
        export AIDER_DISABLE_STREAMING=1
        
        # Prepare aider command with proper arguments
        AIDER_ARGS="--dir \"$TARGET_DIR\" --model \"$MODEL\" --conventions-file \"$CONVENTIONS_FILE\""
        if [ "$VERBOSE" = true ]; then
            AIDER_ARGS="$AIDER_ARGS --verbose"
        fi
        if [ "$CHECK_ONLY" = true ]; then
            AIDER_ARGS="$AIDER_ARGS --dry-run"
        fi
        if [ "$CHECK_FOR_URLS" = true ]; then
            AIDER_ARGS="$AIDER_ARGS --check-for-urls"
        fi
        
        # Run aider to fix the remaining issues
        echo -e "Running Aider to fix remaining issues..."
        AIDER_CMD="python3 \"$SCRIPT_DIR/aider_refactor.py\" $AIDER_ARGS"
        
        if [ "$VERBOSE" = true ]; then
            echo "Command: $AIDER_CMD"
        fi
        
        # Use a timeout to avoid hanging
        timeout 300s bash -c "$AIDER_CMD" || {
            echo -e "${RED}Error: Aider process timed out or encountered an error.${NC}"
            echo -e "${YELLOW}You can run it manually with:${NC}"
            echo -e "$AIDER_CMD"
        }
    else
        echo -e "${GREEN}No remaining flake8 issues found. Skipping Aider.${NC}"
    fi
    
    # Clean up
    rm -f "$FLAKE8_OUTPUT"
    echo ""
fi

# Step 4: Final report
echo -e "${BOLD}==============================================${NC}"
echo -e "${BOLD}PROCESS COMPLETED${NC}"
echo -e "${BOLD}==============================================${NC}"
echo -e "Finished at: ${BOLD}$(date)${NC}"
echo ""

echo -e "${GREEN}${BOLD}NEXT STEPS:${NC}"
echo "1. Review the changes made to your files"
echo "2. Run any tests to ensure functionality wasn't affected"
echo "3. For any remaining issues, manual fixes may be required"
echo ""

if [ "$CHECK_ONLY" = true ]; then
    echo -e "${YELLOW}Note: This was a dry run. No changes were made to your files.${NC}"
    echo -e "To apply the changes, run the script without the --check-only flag."
fi

echo -e "${BOLD}==============================================${NC}" 