# Institutional Prospects Import

This directory contains files to create and populate the `institutional_prospects` table in DuckDB with data from the "RIA Schwab.xlsx - Standard Template.csv" file.

## Files

1. `create_institutional_prospects_table.sql` - SQL script that defines the structure of the institutional_prospects table, including:
   - All fields from the CSV file with appropriate data types
   - Created_at and updated_at timestamp fields
   - Indexes on key fields
   - A trigger to automatically update the updated_at timestamp when records are modified

2. `import_institutional_prospects.py` - Python script to import the CSV data into the institutional_prospects table:
   - Cleans and normalizes column names
   - Handles data type conversions (dates, numeric values)
   - Creates the table using the SQL definition if it doesn't exist
   - Provides options to truncate or append to existing data
   - Verifies the import by counting rows

## Usage

1. Ensure both files are in the same directory
2. Run the import script:

```
python import_institutional_prospects.py
```

3. The script will:
   - Connect to DuckDB (MotherDuck if token available, otherwise local)
   - Create the table if it doesn't exist
   - Read and process the CSV file
   - Ask for confirmation before truncating existing data
   - Import the data and display a summary

## Data Fields

The institutional_prospects table includes these key fields:

- `ria_firm_crd`: Unique identifier (CRD number)
- `ria_firm_name`: Name of the RIA firm
- `main_office_*`: Address and contact information
- `num_*`: Staff counts (advisory reps, insurance licensed reps, etc.)
- `total_assets_mil`: Assets under management in millions
- `aum_growth_rate_*`: Growth rates over 1 and 5 years
- `custodian_assets_mil_*`: Assets held at different custodians
- `q4_total_assets_mil_*`: Historical asset data by year
- Various other fields for social media, websites, etc.

## Notes

- The CSV file is expected to be located at: `/Users/srvo/input_data/csv_files/RIA Schwab.xlsx - Standard Template.csv`
- To use with MotherDuck, set the `MOTHERDUCK_TOKEN` environment variable
- The table structure includes additional fields for record management (created_at, updated_at) 