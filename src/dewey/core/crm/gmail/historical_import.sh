#!/bin/bash
# Gmail Historical Import Script
# This script performs a one-time import of all historical emails from Gmail
# It imports full message content including body, CCs, BCCs, and attachments
# Uses nohup to run in the background and survive terminal disconnections

# Set the path to the dewey directory
DEWEY_DIR="$HOME/dewey"
DB_PATH="$HOME/dewey_emails.duckdb"
LOG_FILE="$DEWEY_DIR/logs/gmail_historical_import.log"
NOHUP_LOG="$DEWEY_DIR/logs/gmail_historical_nohup.log"

# Create logs directory if it doesn't exist
mkdir -p "$DEWEY_DIR/logs"

# Activate virtual environment if it exists
if [ -f "$DEWEY_DIR/.venv/bin/activate" ]; then
    source "$DEWEY_DIR/.venv/bin/activate"
fi

# Log start time
echo "$(date): Starting Gmail historical import" >> "$LOG_FILE"

# Function to run the import
run_import() {
    nohup python "$DEWEY_DIR/src/dewey/core/crm/gmail/simple_import.py" \
        --historical \
        --max 500 \
        --batch-size 25 \
        --db-path "$DB_PATH" \
        --checkpoint \
        >> "$LOG_FILE" 2>&1 &
    
    # Save the PID to a file for later reference
    echo $! > "$DEWEY_DIR/logs/gmail_import.pid"
    echo "$(date): Started import process with PID $!" >> "$LOG_FILE"
    echo "Import process started with PID $! in the background."
    echo "You can check progress with ./check_progress.sh"
    echo "Log file: $LOG_FILE"
}

# Check if there's already a running import process
PID=$(pgrep -f "python.*simple_import.py.*--historical")
if [ -n "$PID" ]; then
    echo "Import process is already running with PID $PID"
    echo "If you want to restart it, kill it first with: kill $PID"
    exit 0
fi

# Run the import in the background
run_import

echo "$(date): Historical import started in background. Check $LOG_FILE for progress." >> "$LOG_FILE"
echo "To monitor progress, run: ./check_progress.sh"

# Usage:
# Run this script once to import all historical emails:
# ./historical_import.sh
#
# After the historical import is complete, set up the regular import to run every 5 minutes:
# crontab -e
# */5 * * * * $HOME/dewey/src/dewey/core/crm/gmail/run_import.sh

# Note: If the historical import is interrupted, you can resume it by running:
# ./historical_import.sh
# The script will automatically continue from where it left off. 