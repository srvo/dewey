#!/bin/bash
# Consolidated Gmail Sync Cron Script
# This script handles:
# 1. Email syncing (every 5 minutes)
# 2. Email enrichment (after successful sync)
# 3. MotherDuck sync (every 15 minutes)
# 4. Consistency checks (every hour)
# 5. Historical import if needed

# Set the path to the dewey directory
DEWEY_DIR="$HOME/dewey"
LOG_DIR="$DEWEY_DIR/logs"
SYNC_LOG="$LOG_DIR/gmail_sync_$(date +%Y%m%d).log"
LOCK_FILE="/tmp/gmail_sync.lock"
DB_PATH="$HOME/dewey_emails.duckdb"
HISTORICAL_FLAG_FILE="$LOG_DIR/.historical_import_complete"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "$(date): $1" >> "$SYNC_LOG"
    echo "$(date): $1"
}

# Function to check if another sync is running
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        PID=$(cat "$LOCK_FILE")
        if ps -p $PID > /dev/null; then
            log_message "Another sync is running (PID: $PID). Exiting."
            exit 0
        else
            # Lock file exists but process is not running
            rm -f "$LOCK_FILE"
        fi
    fi
    # Create lock file
    echo $$ > "$LOCK_FILE"
}

# Function to clean up
cleanup() {
    rm -f "$LOCK_FILE"
}

# Set up trap to clean up on exit
trap cleanup EXIT

# Check if we're already running
check_lock

# Change to the dewey directory
cd "$DEWEY_DIR" || {
    log_message "Failed to change to directory $DEWEY_DIR. Exiting."
    exit 1
}

# Set up Python environment
if [ -f "$DEWEY_DIR/.venv/bin/activate" ]; then
    source "$DEWEY_DIR/.venv/bin/activate"
elif [ -f "$DEWEY_DIR/venv/bin/activate" ]; then
    source "$DEWEY_DIR/venv/bin/activate"
else
    log_message "No virtual environment found. Exiting."
    exit 1
fi

# Add project root to PYTHONPATH
export PYTHONPATH="$DEWEY_DIR:$PYTHONPATH"

# Load environment variables if .env exists
if [ -f "$DEWEY_DIR/.env" ]; then
    set -a
    source "$DEWEY_DIR/.env"
    set +a
fi

# Function to check if we need historical import
need_historical_import() {
    # Check if historical import has been completed
    if [ -f "$HISTORICAL_FLAG_FILE" ]; then
        return 1
    fi
    
    # Check if database exists and has emails
    if [ -f "$DB_PATH" ]; then
        EMAIL_COUNT=$(duckdb "$DB_PATH" "SELECT COUNT(*) FROM emails;" 2>/dev/null || echo "0")
        if [ "$EMAIL_COUNT" -gt "1000" ]; then
            # If we have significant emails, mark historical as complete
            touch "$HISTORICAL_FLAG_FILE"
            return 1
        fi
    fi
    
    return 0
}

# Function to run historical import
run_historical_import() {
    log_message "Starting historical email import..."
    
    # Import all emails from the last 10 years
    python src/dewey/core/crm/gmail/simple_import.py \
        --historical \
        --days 3650 \
        --max 1000000 \
        --batch-size 100 \
        --db "md:dewey" \
        >> "$SYNC_LOG" 2>&1
    
    HIST_STATUS=$?
    if [ $HIST_STATUS -eq 0 ]; then
        log_message "Historical import completed successfully"
        touch "$HISTORICAL_FLAG_FILE"
        return 0
    else
        log_message "Historical import failed with status $HIST_STATUS"
        return 1
    fi
}

# Function to run email sync
run_email_sync() {
    log_message "Running incremental sync..."
    python src/dewey/core/crm/gmail/simple_import.py \
        --days 1 \
        --max 1000 \
        --batch-size 100 \
        --db "md:dewey" \
        >> "$SYNC_LOG" 2>&1
    
    return $?
}

# Function to run email enrichment
run_enrichment() {
    log_message "Running email enrichment..."
    python src/dewey/core/crm/enrichment/run_enrichment.py \
        --batch-size 50 \
        --max-emails 100 \
        >> "$SYNC_LOG" 2>&1
    
    return $?
}

# Function to run MotherDuck sync
run_motherduck_sync() {
    log_message "Running MotherDuck sync..."
    python src/dewey/core/crm/gmail/email_sync.py \
        --local-db "$DB_PATH" \
        --dedup-strategy "update" \
        >> "$SYNC_LOG" 2>&1
    
    return $?
}

# Function to run consistency check
run_consistency_check() {
    log_message "Running consistency check..."
    python src/dewey/core/crm/gmail/simple_import.py \
        --days 7 \
        --batch-size 100 \
        --db "md:dewey" \
        >> "$SYNC_LOG" 2>&1
    
    return $?
}

# Check if we need to do historical import
if need_historical_import; then
    log_message "No historical import found. Starting historical import..."
    run_historical_import
    
    if [ $? -ne 0 ]; then
        log_message "Historical import failed. Will try again next time."
        cleanup
        exit 1
    fi
fi

# Check if this is an hourly run (for consistency check)
CURRENT_MIN=$(date +%M)
if [ "$CURRENT_MIN" = "00" ]; then
    run_consistency_check
    CHECK_STATUS=$?
    if [ $CHECK_STATUS -ne 0 ]; then
        log_message "Consistency check failed with status $CHECK_STATUS"
    fi
fi

# Run email sync
run_email_sync
SYNC_STATUS=$?

if [ $SYNC_STATUS -eq 0 ]; then
    log_message "Email sync completed successfully"
    
    # Run enrichment after successful sync
    run_enrichment
    ENRICH_STATUS=$?
    
    if [ $ENRICH_STATUS -eq 0 ]; then
        log_message "Email enrichment completed successfully"
    else
        log_message "Email enrichment failed with status $ENRICH_STATUS"
    fi
    
    # Check if we should run MotherDuck sync (every 15 minutes)
    if [ $(($(date +%M) % 15)) -eq 0 ]; then
        run_motherduck_sync
        MD_STATUS=$?
        
        if [ $MD_STATUS -eq 0 ]; then
            log_message "MotherDuck sync completed successfully"
        else
            log_message "MotherDuck sync failed with status $MD_STATUS"
        fi
    fi
else
    log_message "Email sync failed with status $SYNC_STATUS"
fi

# Final cleanup
cleanup
log_message "Script completed"

# Example crontab entries:
# Run sync every 5 minutes
# */5 * * * * $HOME/dewey/src/dewey/core/crm/gmail/sync_cron.sh
#
# To install cron jobs:
# crontab -e
# Add the above line 