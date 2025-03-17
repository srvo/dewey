import duckdb

# Connect to the database
conn = duckdb.connect('/Users/srvo/input_data/port.duckdb')

# Get the list of tables
tables = conn.execute('SHOW TABLES').fetchall()

# Print the tables
print('Tables in port.duckdb:')
for table in tables:
    print(table[0])
    
    # Get row count for each table
    count = conn.execute(f'SELECT COUNT(*) FROM {table[0]}').fetchone()[0]
    print(f'  - {count} rows')

# Close the connection
conn.close() 