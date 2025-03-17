import psycopg2
from datetime import datetime, timezone

# Connect to database
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="password",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

print("\nChecking database contents:")

# Get total counts
cur.execute("SELECT COUNT(*) FROM stock_analysis")
total_records = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM stock_analysis WHERE market_insights IS NOT NULL AND market_insights != ''")
records_with_insights = cur.fetchone()[0]

print(f"\nTotal analysis records: {total_records}")
print(f"Records with market insights: {records_with_insights}")

# Get most recent analyses with insights
print("\nMost recent analyses with insights:")
cur.execute("""
    SELECT 
        ts.symbol,
        ts.name,
        sa.timestamp,
        sa.price,
        sa.industry,
        sa.market_insights
    FROM stock_analysis sa
    JOIN tracked_stocks ts ON sa.stock_id = ts.id
    WHERE sa.market_insights IS NOT NULL 
    AND sa.market_insights != ''
    ORDER BY sa.timestamp DESC
    LIMIT 5
""")

for row in cur.fetchall():
    symbol, name, timestamp, price, industry, insights = row
    print(f"\n{symbol} ({name}):")
    print(f"  Timestamp: {timestamp}")
    print(f"  Price: ${price:.2f}")
    print(f"  Industry: {industry}")
    print(f"  Insights: {insights[:500]}...")

# Close database connection
cur.close()
conn.close() 