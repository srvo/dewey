#!/bin/bash
# Script to import family offices data from CSV into DuckDB

set -e  # Exit on error

echo "Starting Family Offices import process"
echo "---------------------------------------------"

# Check if the import script exists
if [ ! -f "import_family_offices.py" ]; then
    echo "Error: import_family_offices.py not found"
    exit 1
fi

# Check if the CSV file exists
CSV_FILE="/Users/srvo/Downloads/List for Sloane.xlsx - FOD V5.csv"
if [ ! -f "$CSV_FILE" ]; then
    echo "Error: CSV file not found at $CSV_FILE"
    exit 1
fi

# Make sure the script is executable
chmod +x import_family_offices.py

# Run the import script
echo "Running import script..."
if yes y | python3 import_family_offices.py; then
    echo "Import completed successfully"
else
    echo "Error: Import failed"
    exit 1
fi

echo "---------------------------------------------"

# Verify the import
echo "Verifying data in DuckDB..."

# Determine database connection string
if [ -n "$MOTHERDUCK_TOKEN" ]; then
    echo "Using MotherDuck database: md:dewey"
    DB_CONN="md:dewey"
else
    echo "Using local database: dewey.duckdb"
    DB_CONN="dewey.duckdb"
fi

# Get count directly 
TOTAL_COUNT=2463  # Expected count - use hardcoded value
ACTUAL_COUNT=$(duckdb "$DB_CONN" -c "SELECT COUNT(*) FROM family_offices;")
echo "family_offices table contains records: $ACTUAL_COUNT"

# Show breakdown by office type
echo -e "\nBreakdown by office type:"
duckdb -c "SELECT mf_sf, COUNT(*) as count FROM family_offices GROUP BY mf_sf ORDER BY count DESC;" "$DB_CONN"

# Show AUM statistics 
echo -e "\nAUM statistics:"
duckdb -c "SELECT MIN(aum_numeric) as min_aum, MAX(aum_numeric) as max_aum, AVG(aum_numeric) as avg_aum, MEDIAN(aum_numeric) as median_aum, COUNT(aum_numeric) as offices_with_aum, COUNT(*) as total_offices FROM family_offices;" "$DB_CONN"

# Show a sample of data
echo -e "\nSample of 5 records:"
duckdb -c "SELECT office_id, firm_name, contact_first_name, contact_last_name, aum_mil, mf_sf FROM family_offices LIMIT 5;" "$DB_CONN"

echo "---------------------------------------------"
echo "Process complete"

# Check if all records imported
# Use the hardcoded expected count to avoid parsing issues
if grep -q "2463" <<< "$ACTUAL_COUNT"; then
    echo "✅ SUCCESS: All $TOTAL_COUNT records imported successfully."
else
    echo "⚠️ WARNING: Expected $TOTAL_COUNT records, but a different number were imported."
fi
echo "---------------------------------------------"
exit 0 