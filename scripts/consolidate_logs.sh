#!/bin/bash

# Create standard log directory structure
mkdir -p logs/email_imports
mkdir -p logs/services
mkdir -p logs/batch_jobs
mkdir -p logs/tests

# Move email import logs from src/logs to logs/email_imports
mv src/logs/gmail_import_*.log logs/email_imports/
mv src/logs/imap_import_*.log logs/email_imports/

# Move existing logs to appropriate directories
mv logs/service_deployment_*.log logs/services/
mv logs/test_output.txt logs/tests/
mv logs/batch_upload/* logs/batch_jobs/

# Move any remaining logs from src/logs to appropriate directories
if [ -d "src/logs" ]; then
    mv src/logs/* logs/
    rmdir src/logs
fi

# Create .gitignore if it doesn't exist
if [ ! -f "logs/.gitignore" ]; then
    echo "# Ignore all logs except .gitignore
*
!.gitignore
!.keep" > logs/.gitignore
fi

# Create .keep file to ensure directory is tracked
touch logs/.keep

echo "Log directory consolidation complete!" 