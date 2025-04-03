#!/bin/bash

# Script to batch refactor and test multiple directories
# Created: $(date)

set -e  # Exit on error

# Base directory
BASE_DIR="/Users/srvo/dewey"
# Path to the conventions file
CONVENTIONS_FILE="CONVENTIONS.md"
# Path to the test directory
TEST_DIR="tests"
# Default model to use
MODEL="deepinfra/google/gemini-2.0-flash-001"
# Default to making code testable
NO_TESTABILITY=false
# Default to not running test-fix cycle
RUN_TEST_FIX=false

# Display a header banner
echo "============================================================"
echo "      BATCH REFACTORING AND TEST GENERATION SCRIPT"
echo "============================================================"
echo "Started at: $(date)"
echo ""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model|-m)
            MODEL="$2"
            shift 2
            ;;
        --no-testability)
            NO_TESTABILITY=true
            shift
            ;;
        --run-test-fix)
            RUN_TEST_FIX=true
            shift
            ;;
        --max-iterations)
            MAX_ITERATIONS="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --model|-m MODEL          Model to use (default: $MODEL)"
            echo "  --no-testability          Don't modify source files for testability"
            echo "  --run-test-fix            Run test-fix cycle after generating tests"
            echo "  --max-iterations N        Maximum number of test-fix iterations (default: 5)"
            echo "  --verbose|-v              Enable verbose output"
            echo "  --help|-h                 Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Prepare verbose flag
VERBOSE_FLAG=""
if [ "${VERBOSE:-false}" = true ]; then
    VERBOSE_FLAG="--verbose"
fi

# Function to process a directory
process_directory() {
    local dir="$1"
    local dir_name=$(basename "$dir")

    echo "------------------------------------------------------------"
    echo "Processing directory: $dir_name"
    echo "Started at: $(date)"
    echo "------------------------------------------------------------"

    # Build the command with the appropriate flags
    local cmd="python \"$BASE_DIR/scripts/aider_refactor_and_test.py\" \
        --src-dir \"$dir\" \
        --test-dir \"$TEST_DIR\" \
        --conventions-file \"$CONVENTIONS_FILE\" \
        --model \"$MODEL\" \
        --run-tests \
        $VERBOSE_FLAG"

    # Add the no-testability flag if specified
    if [ "$NO_TESTABILITY" = true ]; then
        cmd="$cmd --no-testability"
    fi

    # Run the refactor and test script on this directory
    eval $cmd
    local refactor_status=$?

    # If we're running the test-fix cycle and the refactor didn't fail catastrophically
    if [ "$RUN_TEST_FIX" = true ] && [ $refactor_status -ne 255 ]; then
        echo "Running test-fix cycle for $dir_name"

        # Build the test-fix command
        local fix_cmd="\"$BASE_DIR/scripts/test_fix_cycle.sh\" \
            --dir \"$dir\" \
            --test-dir \"$TEST_DIR\" \
            --conventions-file \"$CONVENTIONS_FILE\" \
            --model \"$MODEL\" \
            --fix-only \
            $VERBOSE_FLAG"

        # Add the no-testability flag if specified
        if [ "$NO_TESTABILITY" = true ]; then
            fix_cmd="$fix_cmd --no-testability"
        fi

        # Add max iterations if specified
        if [ ! -z "${MAX_ITERATIONS:-}" ]; then
            fix_cmd="$fix_cmd --max-iterations $MAX_ITERATIONS"
        fi

        # Run the test-fix cycle
        eval $fix_cmd
        local fix_status=$?

        # Take the worst status between refactor and fix
        if [ $fix_status -ne 0 ]; then
            refactor_status=$fix_status
        fi
    fi

    echo ""
    if [ $refactor_status -eq 0 ]; then
        echo "✅ Successfully completed processing of: $dir_name"
    else
        echo "❌ Error processing directory: $dir_name (exit code: $refactor_status)"
    fi
    echo "Finished at: $(date)"
    echo "------------------------------------------------------------"
    echo ""

    return $refactor_status
}

# List of directories to process
directories=(
    "$BASE_DIR/src/dewey/core/analysis"
    "$BASE_DIR/src/dewey/core/architecture"
    "$BASE_DIR/src/dewey/core/automation"
    "$BASE_DIR/src/dewey/core/bookkeeping"
    "$BASE_DIR/src/dewey/core/config"
    "$BASE_DIR/src/dewey/core/crm"
    "$BASE_DIR/src/dewey/core/data_upload"
    "$BASE_DIR/src/dewey/core/db"
    "$BASE_DIR/src/dewey/core/engines"
    "$BASE_DIR/src/dewey/core/maintenance"
    "$BASE_DIR/src/dewey/core/research"
    "$BASE_DIR/src/dewey/core/sync"
    "$BASE_DIR/src/dewey/core/tui"
    "$BASE_DIR/src/dewey/core/utils"
)

# Track successful and failed directories
successful=()
failed=()

# Process each directory
for dir in "${directories[@]}"; do
    if process_directory "$dir"; then
        successful+=("$(basename "$dir")")
    else
        failed+=("$(basename "$dir")")
    fi
done

# Summary report
echo "============================================================"
echo "                  SUMMARY REPORT"
echo "============================================================"
echo "Total directories processed: ${#directories[@]}"
echo "Successfully completed: ${#successful[@]}"
echo "Failed: ${#failed[@]}"
echo "Testability modifications: $([ "$NO_TESTABILITY" = false ] && echo "Enabled" || echo "Disabled")"
echo "Test-fix cycle: $([ "$RUN_TEST_FIX" = false ] && echo "Disabled" || echo "Enabled")"
echo ""

if [ ${#successful[@]} -gt 0 ]; then
    echo "Successfully processed directories:"
    for dir in "${successful[@]}"; do
        echo "- $dir"
    done
    echo ""
fi

if [ ${#failed[@]} -gt 0 ]; then
    echo "Failed directories:"
    for dir in "${failed[@]}"; do
        echo "- $dir"
    done
    echo ""
fi

echo "Process completed at: $(date)"
echo "============================================================"
