#!/bin/bash
# Gmail Import Progress Checker
# This script checks the progress of the Gmail import

# Set the path to the dewey directory
DEWEY_DIR="$HOME/dewey"
DB_PATH="$HOME/dewey_emails.duckdb"
LOG_FILE="$DEWEY_DIR/logs/gmail_historical_import.log"

# Create logs directory if it doesn't exist
mkdir -p "$DEWEY_DIR/logs"

# Activate virtual environment if it exists
if [ -f "$DEWEY_DIR/.venv/bin/activate" ]; then
    source "$DEWEY_DIR/.venv/bin/activate"
fi

# Check if the import process is running
PID=$(pgrep -f "python.*simple_import.py.*--historical")
if [ -n "$PID" ]; then
    echo "Import process is running with PID $PID"
    ps -p $PID -o %cpu,%mem,etime
    
    # Extract progress from log file
    if [ -f "$LOG_FILE" ]; then
        echo ""
        echo "Current progress from log file:"
        echo "------------------------------"
        
        # Get the latest message count
        LATEST_COUNT=$(grep "Fetched .* messages, total:" "$LOG_FILE" | tail -n 1)
        if [ -n "$LATEST_COUNT" ]; then
            echo "Messages fetched: $LATEST_COUNT"
        fi
        
        # Get the latest batch processing info
        LATEST_BATCH=$(grep "Processing batch of .* emails" "$LOG_FILE" | tail -n 1)
        if [ -n "$LATEST_BATCH" ]; then
            echo "Current batch: $LATEST_BATCH"
        fi
        
        # Get the latest import count
        LATEST_IMPORT=$(grep "Imported .* emails in current batch" "$LOG_FILE" | tail -n 1)
        if [ -n "$LATEST_IMPORT" ]; then
            echo "Import progress: $LATEST_IMPORT"
        fi
        
        # Get the latest checkpoint
        LATEST_CHECKPOINT=$(grep "Updated checkpoint: processed up to index" "$LOG_FILE" | tail -n 1)
        if [ -n "$LATEST_CHECKPOINT" ]; then
            echo "Latest checkpoint: $LATEST_CHECKPOINT"
        fi
        
        echo ""
        echo "Last 10 lines of the log:"
        echo "------------------------"
        tail -n 10 "$LOG_FILE"
    else
        echo "Import log not found at $LOG_FILE"
    fi
else
    echo "Import process is not running"
    
    # If the process is not running, we can safely check the database
    if [ -f "$DB_PATH" ]; then
        # Count the number of emails in the database
        EMAIL_COUNT=$(duckdb "$DB_PATH" "SELECT COUNT(*) FROM emails;")
        echo "Total emails imported: $EMAIL_COUNT"
        
        # Check if the checkpoint table exists
        CHECKPOINT_EXISTS=$(duckdb "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='import_checkpoints';")
        if [ -n "$CHECKPOINT_EXISTS" ]; then
            # Check the last checkpoint
            CHECKPOINT=$(duckdb "$DB_PATH" "SELECT * FROM import_checkpoints ORDER BY id DESC LIMIT 1;" 2>/dev/null)
            if [ -n "$CHECKPOINT" ]; then
                echo "Last checkpoint: $CHECKPOINT"
            fi
        else
            echo "No checkpoint table found. Import may not have started yet."
        fi
        
        # Check the last 10 imported emails
        echo "Last 10 imported emails:"
        duckdb "$DB_PATH" "SELECT id, from_email, to_email, subject, date FROM emails ORDER BY date DESC LIMIT 10;"
    else
        echo "Database file not found at $DB_PATH"
    fi
    
    # Check the import log
    if [ -f "$LOG_FILE" ]; then
        echo "Last 20 lines of the import log:"
        tail -n 20 "$LOG_FILE"
    else
        echo "Import log not found at $LOG_FILE"
    fi
fi 