#!/bin/bash
# Script to run the institutional prospects import

# Set the directory to the script's location
cd "$(dirname "$0")"

echo "Starting Institutional Prospects import process"
echo "---------------------------------------------"

# Check if the SQL file exists
if [ ! -f "create_institutional_prospects_table.sql" ]; then
    echo "ERROR: create_institutional_prospects_table.sql not found!"
    exit 1
fi

# Check if the Python script exists
if [ ! -f "import_institutional_prospects.py" ]; then
    echo "ERROR: import_institutional_prospects.py not found!"
    exit 1
fi

# Check if the CSV file exists
CSV_FILE="/Users/srvo/input_data/csv_files/RIA Schwab.xlsx - Standard Template.csv"
if [ ! -f "$CSV_FILE" ]; then
    echo "ERROR: CSV file not found at $CSV_FILE"
    exit 1
fi

# Make sure Python script is executable
chmod +x import_institutional_prospects.py

# Run the import script
echo "Running import script..."
python3 import_institutional_prospects.py

# Check exit status
if [ $? -eq 0 ]; then
    echo "Import completed successfully"
    echo "---------------------------------------------"
    
    # Verify the table exists and has data
    echo "Verifying data in DuckDB..."
    python3 -c "
import duckdb
import os

if os.environ.get('MOTHERDUCK_TOKEN'):
    conn = duckdb.connect('md:dewey')
else:
    conn = duckdb.connect('dewey.duckdb')

# Get row count
count = conn.execute('SELECT COUNT(*) FROM institutional_prospects').fetchone()[0]
print(f'institutional_prospects table contains {count} rows')

# Get sample of data
print('\\nSample of 5 records:')
sample = conn.execute('SELECT ria_firm_crd, ria_firm_name, total_assets_mil, average_account_size FROM institutional_prospects LIMIT 5').fetchdf()
print(sample)

conn.close()
"
else
    echo "Import failed"
    exit 1
fi

echo "---------------------------------------------"
echo "Process complete" 