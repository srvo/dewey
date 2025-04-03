#!/bin/bash
# Sync local DuckDB database to MotherDuck for improved concurrency

# Set the path to the dewey directory
DEWEY_DIR="$HOME/dewey"
LOG_DIR="$DEWEY_DIR/logs"
LOG_FILE="$LOG_DIR/motherduck_sync_$(date +%Y%m%d).log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Check if another sync is already running
PID=$(pgrep -f "python.*email_sync.py")
if [ -n "$PID" ]; then
    echo "$(date): Another sync is already running (PID: $PID). Exiting." >> "$LOG_FILE"
    exit 0
fi

# Change to the dewey directory
cd "$DEWEY_DIR" || {
    echo "$(date): Failed to change to directory $DEWEY_DIR. Exiting." >> "$LOG_FILE"
    exit 1
}

# Check if MOTHERDUCK_TOKEN is set
if [ -z "$MOTHERDUCK_TOKEN" ]; then
    # Try to load from .env file
    if [ -f "$DEWEY_DIR/.env" ]; then
        source "$DEWEY_DIR/.env"
    fi

    # Check again
    if [ -z "$MOTHERDUCK_TOKEN" ]; then
        echo "$(date): MOTHERDUCK_TOKEN environment variable not set. Exiting." >> "$LOG_FILE"
        exit 1
    fi
fi

# Run the sync script
echo "$(date): Starting MotherDuck sync..." >> "$LOG_FILE"
nohup python src/dewey/core/crm/gmail/email_sync.py --dedup-strategy "update" >> "$LOG_FILE" 2>&1 &

# Wait for the sync to complete
wait $!
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): MotherDuck sync completed successfully." >> "$LOG_FILE"
else
    echo "$(date): MotherDuck sync failed with exit code $EXIT_CODE." >> "$LOG_FILE"
fi

exit $EXIT_CODE
