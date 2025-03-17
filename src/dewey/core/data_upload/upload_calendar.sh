#!/bin/bash

# Script to upload calendar data to MotherDuck
# This script specifically uploads the calendar data from the nov_30_crm_data directory

# Set the path to the Dewey directory
DEWEY_DIR="/Users/srvo/dewey"
LOG_DIR="${DEWEY_DIR}/logs"
LOG_FILE="${LOG_DIR}/calendar_upload_$(date +%Y%m%d_%H%M%S).log"

# Create logs directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# Change to the Dewey directory
cd "${DEWEY_DIR}" || {
    log "ERROR: Failed to change to directory ${DEWEY_DIR}"
    exit 1
}

# Check if MOTHERDUCK_TOKEN is set
if [ -z "${MOTHERDUCK_TOKEN}" ]; then
    log "WARNING: MOTHERDUCK_TOKEN environment variable not set"
    log "Will use local DuckDB database instead"
fi

# Parse command line arguments
DEDUP_STRATEGY="update"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dedup-strategy)
            DEDUP_STRATEGY="$2"
            shift 2
            ;;
        *)
            log "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate deduplication strategy
if [[ ! "$DEDUP_STRATEGY" =~ ^(update|skip|replace|version)$ ]]; then
    log "ERROR: Invalid deduplication strategy: ${DEDUP_STRATEGY}"
    log "Valid options are: update, skip, replace, version"
    exit 1
fi

log "Using deduplication strategy: ${DEDUP_STRATEGY}"

# Define the calendar file paths
CALENDAR_DUCKDB="/Users/srvo/input_data/nov_30_crm_data/crm/calendar/calendar.duckdb"
CALENDAR_SQLITE="/Users/srvo/input_data/nov_30_crm_data/crm/calendar/calendar_data.db"

# Check if at least one of the calendar files exists
if [ ! -f "${CALENDAR_DUCKDB}" ] && [ ! -f "${CALENDAR_SQLITE}" ]; then
    log "ERROR: No calendar files found at expected locations"
    exit 1
fi

# Upload the DuckDB file if it exists
if [ -f "${CALENDAR_DUCKDB}" ]; then
    log "Starting upload of calendar data from ${CALENDAR_DUCKDB}"
    
    # Run the uploader for the calendar DuckDB file
    python -m src.dewey.core.data_upload.motherduck_uploader --file "${CALENDAR_DUCKDB}" --database "dewey" --dedup-strategy "${DEDUP_STRATEGY}" 2>&1 | tee -a "${LOG_FILE}"
    
    # Check the exit status
    EXIT_CODE=${PIPESTATUS[0]}
    if [ ${EXIT_CODE} -ne 0 ]; then
        log "Failed to upload calendar data from ${CALENDAR_DUCKDB}"
        exit ${EXIT_CODE}
    fi
fi

# Upload the SQLite file if it exists
if [ -f "${CALENDAR_SQLITE}" ]; then
    log "Found SQLite calendar data at ${CALENDAR_SQLITE}"
    
    # Validate SQLite file
    if [ ! -s "${CALENDAR_SQLITE}" ]; then
        log "WARNING: SQLite file is empty, skipping"
    else
        # Check SQLite file header
        HEADER=$(hexdump -n 16 -e '16/1 "%02x"' "${CALENDAR_SQLITE}")
        if [[ ! $HEADER =~ ^53514c69746520666f726d6174203300 ]]; then
            log "WARNING: Not a valid SQLite database file, skipping"
        else
            log "Starting upload of SQLite calendar data"
            
            # Run the uploader for the calendar SQLite file
            python -m src.dewey.core.data_upload.motherduck_uploader --file "${CALENDAR_SQLITE}" --database "dewey" --dedup-strategy "${DEDUP_STRATEGY}" 2>&1 | tee -a "${LOG_FILE}"
            
            # Check the exit status
            EXIT_CODE=${PIPESTATUS[0]}
            if [ ${EXIT_CODE} -ne 0 ]; then
                log "Failed to upload calendar data from ${CALENDAR_SQLITE}"
                log "This might be due to a corrupted SQLite file"
                log "Continuing with the next steps..."
            fi
        fi
    fi
fi

log "Calendar data upload completed successfully"
exit 0 