import duckdb

# Assuming the previous cell created a DataFrame with the data
# Extract domain from email addresses
df["domain"] = df["email"].str.split("@").str[1]

# Initialize DuckDB connection
con = duckdb.connect("contacts.db")

# Create contacts table if it doesn't exist
con.execute(
    """
    CREATE TABLE IF NOT EXISTS contacts (
        name VARCHAR,
        email VARCHAR UNIQUE,
        domain VARCHAR
    )
""",
)

# Insert data into DuckDB
con.execute("INSERT OR REPLACE INTO contacts SELECT * FROM df")

# Verify the data
result = con.execute(
    """
    SELECT
        COUNT(*) as total_contacts,
        COUNT(DISTINCT domain) as unique_domains,
        COUNT(DISTINCT email) as unique_emails
    FROM contacts
""",
).fetchdf()

# Sample verification query
domain_counts = con.execute(
    """
    SELECT
        domain,
        COUNT(*) as count
    FROM contacts
    GROUP BY domain
    ORDER BY count DESC
    LIMIT 5
""",
).fetchdf()

# Close connection
con.close()

# Display the DataFrame

# Optional: Save to CSV if needed
# df.to_csv('contacts.csv', index=False)
