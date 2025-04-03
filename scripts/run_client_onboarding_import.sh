#!/bin/bash

# Script to import client onboarding data from CSV files into DuckDB
# This script should be located in the same directory as the import_client_onboarding.py file

# Change to the directory where this script is located
cd "$(dirname "$0")"

echo "Starting Client Onboarding Data Import Process"
echo "---------------------------------------------"

# Check if the required SQL file exists
if [ ! -f "create_consolidated_client_tables.sql" ]; then
    echo "ERROR: SQL file 'create_consolidated_client_tables.sql' not found in the current directory."
    exit 1
fi

# Check if the Python script exists
if [ ! -f "import_client_onboarding.py" ]; then
    echo "ERROR: Python script 'import_client_onboarding.py' not found in the current directory."
    exit 1
fi

# Check if the required CSV files exist
CSV_FILES=(
    "/Users/srvo/input_data/csv_files/Client Intake Questionnaire (Responses) - Form Responses 1.csv"
    "/Users/srvo/input_data/csv_files/onboarding_responses.csv"
    "/Users/srvo/input_data/csv_files/forminator-onboarding-form-241114090152.csv"
    "/Users/srvo/input_data/csv_files/legitimate_onboarding_form_responses.csv"
)

for file in "${CSV_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "WARNING: CSV file '$file' not found. Import may be partial."
    fi
done

# Make the Python script executable
chmod +x import_client_onboarding.py

# Run the Python script
echo "Running import script..."
./import_client_onboarding.py

# Check if the script completed successfully
if [ $? -eq 0 ]; then
    echo "---------------------------------------------"
    echo "Import completed successfully"
    echo "Verifying data in DuckDB..."

    # Connect to DuckDB and get some stats
    # Use MotherDuck if token exists, otherwise use local DB
    if [ -n "$MOTHERDUCK_TOKEN" ]; then
        DB_CONNECTION="md:dewey"
        echo "Using MotherDuck database: $DB_CONNECTION"
    else
        DB_CONNECTION="dewey.duckdb"
        echo "Using local database: $DB_CONNECTION"
    fi

    # Count records in tables
    echo "Table record counts:"
    echo "- client_profiles: $(duckdb "$DB_CONNECTION" -csv -c "SELECT COUNT(*) FROM client_profiles") records"
    echo "- client_data_sources: $(duckdb "$DB_CONNECTION" -csv -c "SELECT COUNT(*) FROM client_data_sources") records"

    # Show sample client profile data
    echo ""
    echo "Sample client profile data (3 records):"
    duckdb "$DB_CONNECTION" -c "SELECT name, email, phone, preferred_investment_amount, risk_tolerance, primary_data_source FROM client_profiles LIMIT 3"

    # Show data source distribution
    echo ""
    echo "Data sources distribution:"
    duckdb "$DB_CONNECTION" -c "SELECT SPLIT(primary_data_source, ',')[1] as main_source, COUNT(*) FROM client_profiles GROUP BY main_source ORDER BY COUNT(*) DESC"

    # Show household linking stats
    echo ""
    echo "Household linking stats:"
    duckdb "$DB_CONNECTION" -c "SELECT COUNT(*) as linked_profiles FROM client_profiles WHERE household_id IS NOT NULL"

    echo "---------------------------------------------"
    echo "Process complete"
    exit 0
else
    echo "---------------------------------------------"
    echo "ERROR: Import process failed. Check the output above for details."
    exit 1
fi
