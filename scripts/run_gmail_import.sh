#!/bin/bash

# Script to run Gmail import with proper configuration
# This script is meant to be run by cron

# Change to the project directory
cd ~/dewey || exit 1

# Set up Python environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    echo "$(date): No virtual environment found" >> "logs/gmail_import.log"
    exit 1
fi

# Add project root to PYTHONPATH
export PYTHONPATH=~/dewey:$PYTHONPATH

# Load environment variables if .env exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Log file
LOG_FILE="logs/gmail_import.log"
mkdir -p logs

# Check if another instance is running
LOCK_FILE="/tmp/gmail_import.lock"
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p $PID > /dev/null; then
        echo "$(date): Another import is running (PID: $PID). Exiting." >> "$LOG_FILE"
        exit 0
    fi
    rm -f "$LOCK_FILE"
fi

# Create lock file
echo $$ > "$LOCK_FILE"

# Function to clean up
cleanup() {
    rm -f "$LOCK_FILE"
}

# Set up trap to clean up on exit
trap cleanup EXIT

# Log start time
echo "$(date): Starting Gmail import" >> "$LOG_FILE"

# Run the import script
python -m dewey.core.crm.gmail.simple_import \
    --days 7 \
    --max 1000 \
    --checkpoint \
    --batch-size 50 \
    --db "md:dewey" \
    >> "$LOG_FILE" 2>&1

STATUS=$?

# Log completion
if [ $STATUS -eq 0 ]; then
    echo "$(date): Gmail import completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Gmail import failed with status $STATUS" >> "$LOG_FILE"
fi

# Clean up
cleanup 