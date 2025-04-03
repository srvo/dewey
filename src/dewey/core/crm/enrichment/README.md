# Email Enrichment Module

This module provides functionality to enrich email data with additional metadata, extract contact information, detect business opportunities, and prioritize emails.

## Features

- **Email Content Enrichment**: Fetches full message bodies from Gmail
- **Contact Information Extraction**: Extracts contact details from email content
- **Business Opportunity Detection**: Identifies potential business opportunities
- **Email Prioritization**: Scores emails based on importance and relevance

## Setup

1. **Database**:
   - Emails are stored in a DuckDB database at `~/dewey_emails.duckdb`
   - For improved concurrency, data is synced to MotherDuck every 15 minutes

2. **Cron Jobs**:
   - Run `../gmail/setup_cron.sh` to set up cron jobs for:
     - Gmail import (every 5 minutes)
     - MotherDuck sync (every 15 minutes)
     - Email enrichment (every 10 minutes)

3. **Configuration**:
   - Regex patterns for contact extraction and opportunity detection are defined in `config/dewey.yaml`
   - Email prioritization rules are defined in the `EmailPrioritizer` class

## Usage

### Running the Enrichment Pipeline

To run the complete enrichment pipeline:

```bash
./run_enrichment.sh
```

This will:
- Enrich email content (fetch full message bodies)
- Detect business opportunities
- Extract and enrich contact information
- Prioritize emails based on content and sender

### Command-line Arguments

The `run_enrichment.sh` script accepts several arguments:

- `--batch-size N`: Process emails in batches of N (default: 50)
- `--max-emails N`: Process at most N emails (default: 100)

Example:

```bash
./run_enrichment.sh --batch-size 20 --max-emails 50
```

### Monitoring

To view logs:

```bash
cat ~/dewey/logs/enrichment.log
```

## Architecture

The enrichment pipeline consists of several components:

1. **Email Enrichment Service** (`email_enrichment_service.py`):
   - Fetches full message bodies from Gmail
   - Extracts plain text and HTML content
   - Scores emails based on priority

2. **Opportunity Detection** (`opportunity_detection.py`):
   - Analyzes email content for business opportunities
   - Uses regex patterns to identify opportunities
   - Updates contact records with opportunity flags

3. **Contact Enrichment** (`contact_enrichment.py`):
   - Extracts contact information from emails
   - Identifies names, companies, job titles, phone numbers, etc.
   - Maintains a contacts database with enriched information

4. **Main Orchestrator** (`run_enrichment.py`):
   - Coordinates the enrichment pipeline
   - Handles batch processing and error recovery
   - Logs enrichment statistics

## Troubleshooting

### Database Locks

If you encounter database lock errors:

1. Check if another process is using the database:
   ```bash
   ps aux | grep dewey_emails.duckdb
   ```

2. Use MotherDuck for concurrent access:
   ```bash
   # Connect to MotherDuck in Python
   import duckdb
   conn = duckdb.connect("md:dewey_emails?motherduck_token=$MOTHERDUCK_TOKEN")
   ```

### Process Already Running

If you see "Another enrichment process is already running" message:

1. Check if the process is actually running:
   ```bash
   ps aux | grep run_enrichment.py
   ```

2. If the process is stuck, you can kill it:
   ```bash
   pkill -f "python.*run_enrichment.py"
   ```

## Development

### Adding New Features

When adding new features:

1. Update the database schema if needed
2. Add appropriate logging
3. Update the README.md with documentation
4. Test thoroughly with small batches before running on your full dataset

### Testing

To run tests:

```bash
./test.sh
```

This will:
- Test database connections
- Test module imports
- Verify basic functionality
