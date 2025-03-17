#!/bin/bash
# Gmail Import Cron Script
# This script is designed to be run as a cron job to import emails from Gmail
# It imports full message content including body, CCs, BCCs, and attachments
# Uses nohup to run in the background and survive terminal disconnections

# Set the path to the dewey directory
DEWEY_DIR="$HOME/dewey"
DB_PATH="$HOME/dewey_emails.duckdb"
LOG_FILE="$DEWEY_DIR/logs/gmail_import.log"

# Create logs directory if it doesn't exist
mkdir -p "$DEWEY_DIR/logs"

# Activate virtual environment if it exists
if [ -f "$DEWEY_DIR/.venv/bin/activate" ]; then
    source "$DEWEY_DIR/.venv/bin/activate"
fi

# Log start time
echo "$(date): Starting Gmail import" >> "$LOG_FILE"

# Check if there's already a running import process
PID=$(pgrep -f "python.*simple_import.py.*--days 1")
if [ -n "$PID" ]; then
    echo "$(date): Import process already running with PID $PID, skipping" >> "$LOG_FILE"
    exit 0
fi

# Run the import script for recent emails (last day) in the background
nohup python "$DEWEY_DIR/src/dewey/core/crm/gmail/simple_import.py" \
    --days 1 \
    --max 100 \
    --db-path "$DB_PATH" \
    >> "$LOG_FILE" 2>&1 &

# Log completion
echo "$(date): Gmail import started with PID $! in background" >> "$LOG_FILE"

# Example cron job (add to crontab -e):
# */5 * * * * $HOME/dewey/src/dewey/core/crm/gmail/run_import.sh 