#!/bin/bash
# Set up crontab entries for Gmail import, MotherDuck sync, and email enrichment

# Set the path to the dewey directory
DEWEY_DIR="$HOME/dewey"

# Change to the dewey directory
cd "$DEWEY_DIR" || {
    echo "Failed to change to directory $DEWEY_DIR. Exiting."
    exit 1
}

# Make sure the scripts are executable
chmod +x src/dewey/core/crm/gmail/run_import.sh
chmod +x src/dewey/core/crm/gmail/motherduck_sync.sh
chmod +x src/dewey/core/crm/enrichment/run_enrichment.sh

# Create a temporary file with the current crontab
crontab -l > /tmp/current_crontab 2>/dev/null || echo "" > /tmp/current_crontab

# Check if the Gmail import entry already exists
if ! grep -q "run_import.sh" /tmp/current_crontab; then
    # Add the Gmail import entry (every 5 minutes)
    echo "*/5 * * * * $DEWEY_DIR/src/dewey/core/crm/gmail/run_import.sh" >> /tmp/current_crontab
    echo "Added Gmail import cron job (every 5 minutes)"
else
    echo "Gmail import cron job already exists"
fi

# Check if the MotherDuck sync entry already exists
if ! grep -q "motherduck_sync.sh" /tmp/current_crontab; then
    # Add the MotherDuck sync entry (every 15 minutes)
    echo "*/15 * * * * $DEWEY_DIR/src/dewey/core/crm/gmail/motherduck_sync.sh" >> /tmp/current_crontab
    echo "Added MotherDuck sync cron job (every 15 minutes)"
else
    echo "MotherDuck sync cron job already exists"
fi

# Check if the email enrichment entry already exists
if ! grep -q "run_enrichment.sh" /tmp/current_crontab; then
    # Add the email enrichment entry (every 10 minutes)
    echo "*/10 * * * * $DEWEY_DIR/src/dewey/core/crm/enrichment/run_enrichment.sh --batch-size 50 --max-emails 100" >> /tmp/current_crontab
    echo "Added email enrichment cron job (every 10 minutes)"
else
    echo "Email enrichment cron job already exists"
fi

# Install the new crontab
crontab /tmp/current_crontab
echo "Crontab updated"

# Clean up
rm /tmp/current_crontab

# Show the current crontab
echo "Current crontab:"
crontab -l 