#!/bin/bash

# Script to upload domain stats data to MotherDuck or local DuckDB

# Set paths
DEWEY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
INPUT_DIR="/Users/srvo/input_data"
DOMAIN_STATS_DB="${INPUT_DIR}/domain_stats.db"
LOG_DIR="${DEWEY_DIR}/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/domain_stats_upload_${TIMESTAMP}.log"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Function to log messages
log_message() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "${timestamp} - $1" | tee -a "${LOG_FILE}"
}

# Change to the Dewey directory
cd "${DEWEY_DIR}" || { log_message "ERROR: Could not change to Dewey directory"; exit 1; }

# Check if MOTHERDUCK_TOKEN is set
if [ -z "${MOTHERDUCK_TOKEN}" ]; then
    log_message "WARNING: MOTHERDUCK_TOKEN is not set. Will use local DuckDB."
fi

# Default values
DEDUP_STRATEGY="update"
DATABASE="dewey"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dedup-strategy)
            DEDUP_STRATEGY="$2"
            shift 2
            ;;
        --database)
            DATABASE="$2"
            shift 2
            ;;
        *)
            log_message "ERROR: Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate deduplication strategy
if [[ "${DEDUP_STRATEGY}" != "update" && "${DEDUP_STRATEGY}" != "skip" && "${DEDUP_STRATEGY}" != "replace" && "${DEDUP_STRATEGY}" != "version" ]]; then
    log_message "ERROR: Invalid deduplication strategy: ${DEDUP_STRATEGY}"
    log_message "Valid strategies are: update, skip, replace, version"
    exit 1
fi

log_message "Starting domain stats upload with deduplication strategy: ${DEDUP_STRATEGY}"
log_message "Target database: ${DATABASE}"

# Check if domain stats DB exists
if [ ! -f "${DOMAIN_STATS_DB}" ]; then
    log_message "ERROR: Domain stats database not found at ${DOMAIN_STATS_DB}"
    exit 1
fi

# Upload domain stats data
log_message "Uploading domain stats data from ${DOMAIN_STATS_DB}"
python -m dewey.core.data_upload.motherduck_uploader \
    --file "${DOMAIN_STATS_DB}" \
    --database "${DATABASE}" \
    --dedup-strategy "${DEDUP_STRATEGY}"

if [ $? -eq 0 ]; then
    log_message "Domain stats upload completed successfully"
else
    log_message "ERROR: Domain stats upload failed"
    exit 1
fi

log_message "Domain stats upload process completed"
exit 0 