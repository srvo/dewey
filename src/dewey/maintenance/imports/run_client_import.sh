#!/bin/bash
# Script to run the client data import

# Set the directory to the script's location
cd "$(dirname "$0")"

echo "Starting Client Data Import Process"
echo "---------------------------------------------"

# Check if the SQL file exists
if [ ! -f "create_client_tables.sql" ]; then
    echo "ERROR: create_client_tables.sql not found!"
    exit 1
fi

# Check if the Python script exists
if [ ! -f "import_client_data.py" ]; then
    echo "ERROR: import_client_data.py not found!"
    exit 1
fi

# Check if CSV files exist
CSV_FILES=(
    "/Users/srvo/Downloads/Households - 20250319.csv"
    "/Users/srvo/Downloads/All Holdings - 20250319.csv"
    "/Users/srvo/Downloads/contributions-2025.csv"
    "/Users/srvo/Downloads/Open Accounts - 20250319.csv"
)

for file in "${CSV_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: CSV file not found at $file"
        exit 1
    fi
done

# Make sure Python script is executable
chmod +x import_client_data.py

# Run the import script
echo "Running import script..."
python3 import_client_data.py

# Check if the script completed successfully
if [ $? -eq 0 ]; then
    echo "---------------------------------------------"
    echo "Import completed successfully"
else
    echo "---------------------------------------------"
    echo "Import failed"
    exit 1
fi

# Verify the import
echo "Verifying data in DuckDB..."
CONN="md:dewey"  # Use MotherDuck connection string

# Check if MotherDuck token is set, otherwise use local DB
if [ -z "$MOTHERDUCK_TOKEN" ]; then
    CONN="dewey.duckdb"
    echo "Using local database: $CONN"
else
    echo "Using MotherDuck database: $CONN"
fi

# Get row counts
echo "Table record counts:"
for table in households holdings contributions open_accounts; do
    ROW_COUNT=$(duckdb "$CONN" "SELECT COUNT(*) FROM $table;")
    echo "- $table: $ROW_COUNT records"
done
echo ""

# Show sample data from each table
echo "Sample household data (3 records):"
duckdb "$CONN" "SELECT name, num_accounts, cash_percentage, balance FROM households LIMIT 3;" | column -t
echo ""

echo "Sample holdings data (3 records):"
duckdb "$CONN" "SELECT ticker, description, aum_percentage, price, value FROM holdings LIMIT 3;" | column -t
echo ""

echo "Sample contributions data (3 records):"
duckdb "$CONN" "SELECT account, household, maximum_contribution, ytd_contributions FROM contributions LIMIT 3;" | column -t
echo ""

echo "Sample open accounts data (3 records):"
duckdb "$CONN" "SELECT name, household, portfolio, balance FROM open_accounts LIMIT 3;" | column -t
echo ""

echo "---------------------------------------------"
echo "Process complete"
exit 0
