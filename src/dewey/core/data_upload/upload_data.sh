#!/bin/bash

# Script to upload data to MotherDuck
# Usage: ./upload_data.sh [--input-dir DIR] [--database NAME] [--file FILE] [--dedup-strategy STRATEGY]

# Set the path to the Dewey directory
DEWEY_DIR="/Users/srvo/dewey"
LOG_DIR="${DEWEY_DIR}/logs"
LOG_FILE="${LOG_DIR}/data_upload_$(date +%Y%m%d_%H%M%S).log"

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
INPUT_DIR="/Users/srvo/input_data"
DATABASE="dewey"
FILE=""
RECURSIVE=true
DEDUP_STRATEGY="update"

while [[ $# -gt 0 ]]; do
    case $1 in
        --input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        --database)
            DATABASE="$2"
            shift 2
            ;;
        --file)
            FILE="$2"
            shift 2
            ;;
        --no-recursive)
            RECURSIVE=false
            shift
            ;;
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

# Build the command
CMD="python -m src.dewey.core.data_upload.motherduck_uploader"

if [ -n "${FILE}" ]; then
    CMD="${CMD} --file ${FILE}"
else
    CMD="${CMD} --input-dir ${INPUT_DIR}"
fi

CMD="${CMD} --database ${DATABASE}"

if [ "${RECURSIVE}" = false ]; then
    CMD="${CMD} --no-recursive"
fi

CMD="${CMD} --dedup-strategy ${DEDUP_STRATEGY}"

# Log the command
log "Running command: ${CMD}"

# Run the command
eval "${CMD}" 2>&1 | tee -a "${LOG_FILE}"

# Check the exit status
EXIT_CODE=${PIPESTATUS[0]}
if [ ${EXIT_CODE} -eq 0 ]; then
    log "Data upload completed successfully"
else
    log "Data upload failed with exit code ${EXIT_CODE}"
fi

exit ${EXIT_CODE} 