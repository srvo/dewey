#!/bin/bash

# Remove empty log files
find logs -type f -name "*.log" -size 0 -delete

# Move email-related logs to email_imports
mv logs/gmail_*.log logs/email_imports/
mv logs/imap_*.log logs/email_imports/
mv logs/gmail_import.pid logs/email_imports/
mv logs/imap_import.out logs/email_imports/

# Clean up empty directories
rmdir logs/batch_upload 2>/dev/null || true

echo "Log cleanup complete!"
