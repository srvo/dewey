#!/bin/bash
# Run the email enrichment pipeline

# Set the path to the dewey directory
DEWEY_DIR="$HOME/dewey"
LOG_DIR="$DEWEY_DIR/logs"
LOG_FILE="$LOG_DIR/enrichment.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Check if another enrichment process is already running
PID=$(pgrep -f "python.*run_enrichment.py")
if [ -n "$PID" ]; then
    echo "$(date): Another enrichment process is already running (PID: $PID). Exiting." >> "$LOG_FILE"
    exit 0
fi

# Change to the dewey directory
cd "$DEWEY_DIR" || {
    echo "$(date): Failed to change to directory $DEWEY_DIR. Exiting." >> "$LOG_FILE"
    exit 1
}

# Parse command line arguments
BATCH_SIZE=50
MAX_EMAILS=100

while [[ $# -gt 0 ]]; do
    case $1 in
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --max-emails)
            MAX_EMAILS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Find Python executable
PYTHON_EXEC=$(which python3)
if [ -z "$PYTHON_EXEC" ]; then
    PYTHON_EXEC=$(which python)
fi

if [ -z "$PYTHON_EXEC" ]; then
    echo "$(date): Python executable not found. Exiting." >> "$LOG_FILE"
    exit 1
fi

# Run the enrichment pipeline
echo "$(date): Starting email enrichment pipeline (batch_size=$BATCH_SIZE, max_emails=$MAX_EMAILS)..." >> "$LOG_FILE"
nohup $PYTHON_EXEC src/dewey/core/crm/enrichment/run_enrichment.py --batch-size "$BATCH_SIZE" --max-emails "$MAX_EMAILS" >> "$LOG_FILE" 2>&1 &

# Wait for the process to complete
wait $!
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): Email enrichment pipeline completed successfully." >> "$LOG_FILE"
else
    echo "$(date): Email enrichment pipeline failed with exit code $EXIT_CODE." >> "$LOG_FILE"
fi

exit $EXIT_CODE

# Example cron job (add to crontab -e):
# Run every hour
# 0 * * * * $HOME/dewey/src/dewey/core/crm/enrichment/run_enrichment.sh

# Run after email import (every 5 minutes)
# */5 * * * * $HOME/dewey/src/dewey/core/crm/gmail/run_import.sh && sleep 30 && $HOME/dewey/src/dewey/core/crm/enrichment/run_enrichment.sh 