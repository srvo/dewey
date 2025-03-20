import pandas as pd

# Configuration
DATABASE_FILE = "/Users/srvo/dewey/data/merged.duckdb"
UNIVERSE_FILE = "/Users/srvo/dewey/data/universe.csv"
OUTPUT_FILE = "/Users/srvo/dewey/data/universe_breakdown.csv"

# Load universe
universe = pd.read_csv(UNIVERSE_FILE)

# Connect to the database
con = duckdb.connect(DATABASE_FILE)

# Get sector breakdown
sector_breakdown = con.execute(f"""
SELECT sector, COUNT(*) AS count
FROM read_csv_auto('{UNIVERSE_FILE}')
GROUP BY sector
ORDER BY count DESC
""").df()

# Get industry breakdown
industry_breakdown = con.execute(f"""
SELECT industry, COUNT(*) AS count
FROM read_csv_auto('{UNIVERSE_FILE}')
GROUP BY industry
ORDER BY count DESC
""").df()

# Get country breakdown
country_breakdown = con.execute(f"""
SELECT country, COUNT(*) AS count
FROM read_csv_auto('{UNIVERSE_FILE}')
GROUP BY country
ORDER BY count DESC
""").df()

# Print sector breakdown
print("Sector Breakdown:")
print(sector_breakdown)

# Print industry breakdown
print("Industry Breakdown:")
print(industry_breakdown)

# Print country breakdown
print("Country Breakdown:")
print(country_breakdown)

# Save sector breakdown to CSV
sector_breakdown.to_csv("sector_breakdown.csv", index=False)

# Save industry breakdown to CSV
industry_breakdown.to_csv("industry_breakdown.csv", index=False)

# Save country breakdown to CSV
country_breakdown.to_csv("country_breakdown.csv", index=False)

# Disconnect
con.close()
