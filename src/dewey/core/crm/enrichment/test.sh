#!/bin/bash
# Test script for the enrichment pipeline

# Set the path to the dewey directory
DEWEY_DIR="$HOME/dewey"
LOG_FILE="$DEWEY_DIR/test_output.txt"

# Change to the dewey directory
cd "$DEWEY_DIR" || {
    echo "Failed to change to directory $DEWEY_DIR. Exiting."
    exit 1
}

# Run the simple test script
echo "Running simple test script..."
python src/dewey/core/crm/enrichment/simple_test.py > "$LOG_FILE" 2>&1

# Check if the simple test was successful
if grep -q "Test completed successfully" "$LOG_FILE"; then
    echo "Simple test completed successfully!"
else
    echo "Simple test failed. See output below for details."
    cat "$LOG_FILE"
    exit 1
fi

# Run the enrichment test script
echo -e "\nRunning enrichment test script..."
python src/dewey/core/crm/enrichment/test_enrichment.py > "$LOG_FILE" 2>&1

# Display the output
echo -e "\nTest output:"
cat "$LOG_FILE"

# Check if the enrichment test was successful
if grep -q "Test completed successfully" "$LOG_FILE"; then
    echo -e "\nEnrichment test completed successfully!"
    exit 0
else
    echo -e "\nEnrichment test failed. See output above for details."
    exit 1
fi
