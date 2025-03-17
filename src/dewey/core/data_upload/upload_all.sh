#!/bin/bash

# Master script to upload all data to MotherDuck or local DuckDB

# Set paths
DEWEY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
INPUT_DIR="/Users/srvo/input_data"
LOG_DIR="${DEWEY_DIR}/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/all_data_upload_${TIMESTAMP}.log"

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
CONTINUE_ON_ERROR=true
OVERALL_SUCCESS=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dedup-strategy)
            DEDUP_STRATEGY="$2"
            shift 2
            ;;
        --no-continue-on-error)
            CONTINUE_ON_ERROR=false
            shift
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

log_message "Starting master upload with deduplication strategy: ${DEDUP_STRATEGY}"
log_message "Continue on error: ${CONTINUE_ON_ERROR}"

# Function to run an upload script and handle errors
run_upload_script() {
    local script_name="$1"
    local script_path="${DEWEY_DIR}/src/dewey/core/data_upload/${script_name}"
    
    if [ -f "${script_path}" ]; then
        log_message "Running ${script_name}..."
        "${script_path}" --dedup-strategy "${DEDUP_STRATEGY}"
        
        if [ $? -eq 0 ]; then
            log_message "${script_name} completed successfully"
            return 0
        else
            log_message "ERROR: ${script_name} failed"
            if [ "${CONTINUE_ON_ERROR}" = false ]; then
                log_message "Stopping due to error (--no-continue-on-error flag)"
                exit 1
            else
                OVERALL_SUCCESS=false
                log_message "Continuing with next script..."
                return 1
            fi
        fi
    else
        log_message "WARNING: Script ${script_name} not found at ${script_path}"
        return 1
    fi
}

# Run all upload scripts
log_message "Running all upload scripts..."

# Upload calendar data
run_upload_script "upload_calendar.sh"

# Upload email data
run_upload_script "upload_emails.sh"

# Upload contacts data
run_upload_script "upload_contacts.sh"

# Upload domain stats data
run_upload_script "upload_domain_stats.sh"

# Final status
if [ "${OVERALL_SUCCESS}" = true ]; then
    log_message "All upload scripts completed successfully"
    exit 0
else
    log_message "Some upload scripts failed"
    exit 1
fi 