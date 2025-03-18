#!/bin/bash

# Script to recursively upload all data from the input_data directory to MotherDuck or local DuckDB

# Set paths
DEWEY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
DEFAULT_INPUT_DIR="/Users/srvo/input_data"
LOG_DIR="${DEWEY_DIR}/logs"
LOG_FILE="${LOG_DIR}/all_input_data_$(date +%Y%m%d).log"

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
INPUT_DIR="${DEFAULT_INPUT_DIR}"
CONTINUE_ON_ERROR=true
PROCESS_DUCKDB=true
PROCESS_SQLITE=true
PROCESS_CSV=true
PROCESS_JSON=true
MAX_FILES=0  # 0 means no limit

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
        --input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        --no-continue-on-error)
            CONTINUE_ON_ERROR=false
            shift
            ;;
        --skip-duckdb)
            PROCESS_DUCKDB=false
            shift
            ;;
        --skip-sqlite)
            PROCESS_SQLITE=false
            shift
            ;;
        --skip-csv)
            PROCESS_CSV=false
            shift
            ;;
        --skip-json)
            PROCESS_JSON=false
            shift
            ;;
        --max-files)
            MAX_FILES="$2"
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

# Check if input directory exists
if [ ! -d "${INPUT_DIR}" ]; then
    log_message "ERROR: Input directory not found at ${INPUT_DIR}"
    exit 1
fi

log_message "Starting recursive upload of all data from ${INPUT_DIR}"
log_message "Target database: ${DATABASE}"
log_message "Deduplication strategy: ${DEDUP_STRATEGY}"
log_message "Continue on error: ${CONTINUE_ON_ERROR}"
log_message "Process DuckDB files: ${PROCESS_DUCKDB}"
log_message "Process SQLite files: ${PROCESS_SQLITE}"
log_message "Process CSV files: ${PROCESS_CSV}"
log_message "Process JSON files: ${PROCESS_JSON}"
if [ ${MAX_FILES} -gt 0 ]; then
    log_message "Maximum files to process: ${MAX_FILES}"
fi

# Find all supported files in the input directory
log_message "Finding all supported files in ${INPUT_DIR}"

# Initialize arrays for each file type
DUCKDB_FILES=()
SQLITE_FILES=()
CSV_FILES=()
JSON_FILES=()

# Find files based on process flags
if [ "${PROCESS_DUCKDB}" = true ]; then
    while IFS= read -r file; do
        if [ -n "${file}" ]; then
            DUCKDB_FILES+=("${file}")
        fi
    done < <(find "${INPUT_DIR}" -type f -name "*.duckdb" 2>/dev/null)
fi

if [ "${PROCESS_SQLITE}" = true ]; then
    while IFS= read -r file; do
        if [ -n "${file}" ]; then
            SQLITE_FILES+=("${file}")
        fi
    done < <(find "${INPUT_DIR}" -type f \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) 2>/dev/null)
fi

if [ "${PROCESS_CSV}" = true ]; then
    while IFS= read -r file; do
        if [ -n "${file}" ]; then
            CSV_FILES+=("${file}")
        fi
    done < <(find "${INPUT_DIR}" -type f -name "*.csv" 2>/dev/null)
fi

if [ "${PROCESS_JSON}" = true ]; then
    while IFS= read -r file; do
        if [ -n "${file}" ]; then
            JSON_FILES+=("${file}")
        fi
    done < <(find "${INPUT_DIR}" -type f -name "*.json" 2>/dev/null)
fi

# Count files
DUCKDB_COUNT=${#DUCKDB_FILES[@]}
SQLITE_COUNT=${#SQLITE_FILES[@]}
CSV_COUNT=${#CSV_FILES[@]}
JSON_COUNT=${#JSON_FILES[@]}
TOTAL_COUNT=$((DUCKDB_COUNT + SQLITE_COUNT + CSV_COUNT + JSON_COUNT))

log_message "Found ${DUCKDB_COUNT} DuckDB files, ${SQLITE_COUNT} SQLite files, ${CSV_COUNT} CSV files, and ${JSON_COUNT} JSON files"
log_message "Total files to process: ${TOTAL_COUNT}"

# Apply max files limit if specified
if [ ${MAX_FILES} -gt 0 ] && [ ${TOTAL_COUNT} -gt ${MAX_FILES} ]; then
    log_message "Limiting to ${MAX_FILES} files as specified"
    
    # Calculate how many files of each type to process
    TOTAL_TYPES=0
    if [ ${DUCKDB_COUNT} -gt 0 ]; then ((TOTAL_TYPES++)); fi
    if [ ${SQLITE_COUNT} -gt 0 ]; then ((TOTAL_TYPES++)); fi
    if [ ${CSV_COUNT} -gt 0 ]; then ((TOTAL_TYPES++)); fi
    if [ ${JSON_COUNT} -gt 0 ]; then ((TOTAL_TYPES++)); fi
    
    FILES_PER_TYPE=$((MAX_FILES / TOTAL_TYPES))
    
    # Limit each file type
    if [ ${DUCKDB_COUNT} -gt ${FILES_PER_TYPE} ]; then DUCKDB_COUNT=${FILES_PER_TYPE}; fi
    if [ ${SQLITE_COUNT} -gt ${FILES_PER_TYPE} ]; then SQLITE_COUNT=${FILES_PER_TYPE}; fi
    if [ ${CSV_COUNT} -gt ${FILES_PER_TYPE} ]; then CSV_COUNT=${FILES_PER_TYPE}; fi
    if [ ${JSON_COUNT} -gt ${FILES_PER_TYPE} ]; then JSON_COUNT=${FILES_PER_TYPE}; fi
    
    log_message "Processing up to ${DUCKDB_COUNT} DuckDB files, ${SQLITE_COUNT} SQLite files, ${CSV_COUNT} CSV files, and ${JSON_COUNT} JSON files"
fi

# Initialize counters
PROCESSED=0
SUCCESS=0
FILES_LIMIT_REACHED=false

# Process DuckDB files
if [ "${PROCESS_DUCKDB}" = true ] && [ ${DUCKDB_COUNT} -gt 0 ]; then
    log_message "Processing DuckDB files..."
    for ((i=0; i<DUCKDB_COUNT; i++)); do
        file="${DUCKDB_FILES[i]}"
        if [ -n "${file}" ]; then
            log_message "Uploading DuckDB file: ${file}"
            python -m dewey.core.data_upload.upload \
                --file "${file}" \
                --target_db "${DATABASE}" \
                --dedup_strategy "${DEDUP_STRATEGY}"
            
            if [ $? -eq 0 ]; then
                log_message "Successfully uploaded ${file}"
                SUCCESS=$((SUCCESS + 1))
            else
                log_message "ERROR: Failed to upload ${file}"
                if [ "${CONTINUE_ON_ERROR}" = false ]; then
                    log_message "Stopping due to error"
                    exit 1
                fi
            fi
            PROCESSED=$((PROCESSED + 1))
            
            # Check if we've reached the max files limit
            if [ ${MAX_FILES} -gt 0 ] && [ ${PROCESSED} -ge ${MAX_FILES} ]; then
                log_message "Reached maximum files limit (${MAX_FILES})"
                FILES_LIMIT_REACHED=true
                break
            fi
        fi
    done
    
    if [ "${FILES_LIMIT_REACHED}" = true ]; then
        log_message "Upload process completed (reached maximum files limit)"
        log_message "Processed ${PROCESSED} files, ${SUCCESS} successful, $((PROCESSED - SUCCESS)) failed"
        exit 0
    fi
fi

# Process SQLite files
if [ "${PROCESS_SQLITE}" = true ] && [ ${SQLITE_COUNT} -gt 0 ]; then
    log_message "Processing SQLite files..."
    for ((i=0; i<SQLITE_COUNT; i++)); do
        file="${SQLITE_FILES[i]}"
        if [ -n "${file}" ]; then
            log_message "Uploading SQLite file: ${file}"
            python -m dewey.core.data_upload.upload \
                --file "${file}" \
                --target_db "${DATABASE}" \
                --dedup_strategy "${DEDUP_STRATEGY}"
            
            if [ $? -eq 0 ]; then
                log_message "Successfully uploaded ${file}"
                SUCCESS=$((SUCCESS + 1))
            else
                log_message "ERROR: Failed to upload ${file}"
                if [ "${CONTINUE_ON_ERROR}" = false ]; then
                    log_message "Stopping due to error"
                    exit 1
                fi
            fi
            PROCESSED=$((PROCESSED + 1))
            
            # Check if we've reached the max files limit
            if [ ${MAX_FILES} -gt 0 ] && [ ${PROCESSED} -ge ${MAX_FILES} ]; then
                log_message "Reached maximum files limit (${MAX_FILES})"
                FILES_LIMIT_REACHED=true
                break
            fi
        fi
    done
    
    if [ "${FILES_LIMIT_REACHED}" = true ]; then
        log_message "Upload process completed (reached maximum files limit)"
        log_message "Processed ${PROCESSED} files, ${SUCCESS} successful, $((PROCESSED - SUCCESS)) failed"
        exit 0
    fi
fi

# Process CSV files
if [ "${PROCESS_CSV}" = true ] && [ ${CSV_COUNT} -gt 0 ]; then
    log_message "Processing CSV files..."
    for ((i=0; i<CSV_COUNT; i++)); do
        file="${CSV_FILES[i]}"
        if [ -n "${file}" ]; then
            log_message "Uploading CSV file: ${file}"
            python -m dewey.core.data_upload.upload \
                --file "${file}" \
                --target_db "${DATABASE}" \
                --dedup_strategy "${DEDUP_STRATEGY}"
            
            if [ $? -eq 0 ]; then
                log_message "Successfully uploaded ${file}"
                SUCCESS=$((SUCCESS + 1))
            else
                log_message "ERROR: Failed to upload ${file}"
                if [ "${CONTINUE_ON_ERROR}" = false ]; then
                    log_message "Stopping due to error"
                    exit 1
                fi
            fi
            PROCESSED=$((PROCESSED + 1))
            
            # Check if we've reached the max files limit
            if [ ${MAX_FILES} -gt 0 ] && [ ${PROCESSED} -ge ${MAX_FILES} ]; then
                log_message "Reached maximum files limit (${MAX_FILES})"
                FILES_LIMIT_REACHED=true
                break
            fi
        fi
    done
    
    if [ "${FILES_LIMIT_REACHED}" = true ]; then
        log_message "Upload process completed (reached maximum files limit)"
        log_message "Processed ${PROCESSED} files, ${SUCCESS} successful, $((PROCESSED - SUCCESS)) failed"
        exit 0
    fi
fi

# Process JSON files
if [ "${PROCESS_JSON}" = true ] && [ ${JSON_COUNT} -gt 0 ]; then
    log_message "Processing JSON files..."
    for ((i=0; i<JSON_COUNT; i++)); do
        file="${JSON_FILES[i]}"
        if [ -n "${file}" ]; then
            log_message "Uploading JSON file: ${file}"
            python -m dewey.core.data_upload.upload \
                --file "${file}" \
                --target_db "${DATABASE}" \
                --dedup_strategy "${DEDUP_STRATEGY}"
            
            if [ $? -eq 0 ]; then
                log_message "Successfully uploaded ${file}"
                SUCCESS=$((SUCCESS + 1))
            else
                log_message "ERROR: Failed to upload ${file}"
                if [ "${CONTINUE_ON_ERROR}" = false ]; then
                    log_message "Stopping due to error"
                    exit 1
                fi
            fi
            PROCESSED=$((PROCESSED + 1))
            
            # Check if we've reached the max files limit
            if [ ${MAX_FILES} -gt 0 ] && [ ${PROCESSED} -ge ${MAX_FILES} ]; then
                log_message "Reached maximum files limit (${MAX_FILES})"
                FILES_LIMIT_REACHED=true
                break
            fi
        fi
    done
fi

# Summary
log_message "Upload process completed"
log_message "Processed ${PROCESSED} files, ${SUCCESS} successful, $((PROCESSED - SUCCESS)) failed"

if [ ${SUCCESS} -eq ${PROCESSED} ]; then
    log_message "All files were uploaded successfully"
    exit 0
else
    log_message "Some files failed to upload"
    exit 1
fi 