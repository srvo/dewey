import psycopg2

# Connect to database
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="password",
    host="localhost",
    port="5432",
)
cur = conn.cursor()


# Get total counts
cur.execute("SELECT COUNT(*) FROM stock_analysis")
total_records = cur.fetchone()[0]

cur.execute(
    "SELECT COUNT(*) FROM stock_analysis WHERE market_insights IS NOT NULL AND market_insights != ''",
)
records_with_insights = cur.fetchone()[0]


# Get most recent analyses with insights
cur.execute(
    """
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
""",
)

for row in cur.fetchall():
    symbol, name, timestamp, price, industry, insights = row

# Close database connection
cur.close()
conn.close()
