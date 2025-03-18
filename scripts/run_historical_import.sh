#!/bin/bash

# Script to run historical Gmail import
# This script imports all historical emails

# Change to the project directory
cd ~/dewey

# Set up Python environment
export PYTHONPATH=~/dewey:$PYTHONPATH

# Load environment variables if .env exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Log file
LOG_FILE="logs/gmail_historical_import.log"
mkdir -p logs

# Log start time
echo "$(date): Starting historical Gmail import" >> "$LOG_FILE"

# Run the import script with historical flag
nohup python -m dewey.core.crm.gmail.simple_import \
    --historical \
    --max 10000 \
    --checkpoint \
    --batch-size 50 \
    >> "$LOG_FILE" 2>&1 &

# Log the PID
echo "$(date): Historical Gmail import started with PID $! in background" >> "$LOG_FILE" 