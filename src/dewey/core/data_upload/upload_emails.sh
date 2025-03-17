#!/bin/bash

# Script to upload emails data to MotherDuck
# This script specifically uploads the emails data from the nov_30_crm_data directory

# Set the path to the Dewey directory
DEWEY_DIR="/Users/srvo/dewey"
LOG_DIR="${DEWEY_DIR}/logs"
LOG_FILE="${LOG_DIR}/emails_upload_$(date +%Y%m%d_%H%M%S).log"

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

# Define the emails file path
EMAILS_FILE="/Users/srvo/input_data/nov_30_crm_data/crm/emails/emails.duckdb"

# Check if the emails file exists
if [ ! -f "${EMAILS_FILE}" ]; then
    log "ERROR: Emails file not found at ${EMAILS_FILE}"
    exit 1
fi

# Log the start of the upload
log "Starting upload of emails data from ${EMAILS_FILE}"
log "This may take some time as the file is large (88MB)"

# Run the uploader for the emails file
python -m src.dewey.core.data_upload.motherduck_uploader --file "${EMAILS_FILE}" --database "dewey" --dedup-strategy "${DEDUP_STRATEGY}" 2>&1 | tee -a "${LOG_FILE}"

# Check the exit status
EXIT_CODE=${PIPESTATUS[0]}
if [ ${EXIT_CODE} -ne 0 ]; then
    log "Failed to upload emails data from ${EMAILS_FILE}"
    exit ${EXIT_CODE}
fi

log "Emails data upload completed successfully"
exit 0 