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

# Display a header banner
echo "============================================================"
echo "      BATCH REFACTORING AND TEST GENERATION SCRIPT"
echo "============================================================"
echo "Started at: $(date)"
echo ""

# Function to process a directory
process_directory() {
    local dir="$1"
    local dir_name=$(basename "$dir")
    
    echo "------------------------------------------------------------"
    echo "Processing directory: $dir_name"
    echo "Started at: $(date)"
    echo "------------------------------------------------------------"
    
    # Run the refactor and test script on this directory
    python "$BASE_DIR/scripts/aider_refactor_and_test.py" \
        --src-dir "$dir" \
        --test-dir "$TEST_DIR" \
        --conventions-file "$CONVENTIONS_FILE" \
        --model "$MODEL"
    
    local status=$?
    
    echo ""
    if [ $status -eq 0 ]; then
        echo "✅ Successfully completed processing of: $dir_name"
    else
        echo "❌ Error processing directory: $dir_name (exit code: $status)"
    fi
    echo "Finished at: $(date)"
    echo "------------------------------------------------------------"
    echo ""
    
    return $status
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