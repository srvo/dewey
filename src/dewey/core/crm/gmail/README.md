# Gmail Integration

This module provides functionality to import and process emails from Gmail.

## Features

- **Historical Import**: Import all emails from a specified time period
- **Regular Import**: Sync new emails every 5 minutes
- **MotherDuck Integration**: Sync local database to MotherDuck for improved concurrency
- **Email Enrichment**: Process and analyze emails for insights

## Setup

1. **Authentication**:
   - Place your `credentials.json` file in the project root directory (`~/dewey/credentials.json`)
   - The script supports OAuth credentials from the Google Cloud Console

2. **Database**:
   - Emails are stored in a DuckDB database at `~/dewey_emails.duckdb`
   - For improved concurrency, data is synced to MotherDuck every 15 minutes

3. **Cron Jobs**:
   - Run `./setup_cron.sh` to set up cron jobs for regular imports and MotherDuck sync
   - Gmail import runs every 5 minutes
   - MotherDuck sync runs every 15 minutes

## Usage

### Historical Import

To import historical emails:

```bash
./historical_import.sh
```

This will:
- Import emails in batches of 50
- Process up to 500 emails per run
- Automatically retry if interrupted
- Run in the background with nohup

### Regular Import

The regular import runs automatically via cron job every 5 minutes.

To manually trigger an import:

```bash
./run_import.sh
```

### MotherDuck Sync

The MotherDuck sync runs automatically via cron job every 15 minutes.

To manually trigger a sync:

```bash
./motherduck_sync.sh
```

### Monitoring

To check the progress of the historical import:

```bash
./check_progress.sh
```

To view logs:

```bash
# Gmail import logs
cat ~/dewey/logs/gmail_import.log

# MotherDuck sync logs
cat ~/dewey/logs/motherduck_sync.log
```

## Advanced Options

### Command-line Arguments

The `simple_import.py` script accepts several arguments:

- `--days N`: Import emails from the last N days
- `--max N`: Import at most N emails
- `--batch-size N`: Process emails in batches of N
- `--db-path PATH`: Specify a custom database path
- `--user-id EMAIL`: Specify the Gmail user ID (default: "me")
- `--historical`: Enable historical import mode

### MotherDuck Configuration

To use MotherDuck:

1. Sign up for a MotherDuck account at https://motherduck.com/
2. Get your MotherDuck token
3. Add the token to your environment:
   ```bash
   echo 'export MOTHERDUCK_TOKEN="your_token_here"' >> ~/.zshrc
   source ~/.zshrc
   ```
   Or add it to your `.env` file:
   ```
   MOTHERDUCK_TOKEN=your_token_here
   ```

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

### Authentication Issues

If you encounter authentication issues:

1. Verify your credentials file is correctly formatted
2. Check the logs for specific error messages
3. Try regenerating your credentials from the Google Cloud Console

## Development

### Adding New Features

When adding new features:

1. Update the database schema in `simple_import.py` if needed
2. Add appropriate logging
3. Update the README.md with documentation
4. Test thoroughly with small batches before running on your full inbox 