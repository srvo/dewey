from pathlib import Path
import duckdb
import json
from datetime import datetime

def examine_port_data():
    """Examine Port database tables in detail"""
    PORT_DB = Path("/Users/srvo/notebooks/data/port.duckdb")
    
    if not PORT_DB.exists():
        print(f"Port database not found at: {PORT_DB}")
        return
    
    print(f"Reading from: {PORT_DB}")
    conn = duckdb.connect(str(PORT_DB), read_only=True)
    
    try:
        # Look at all available columns
        print("\nEntity Analytics Schema:")
        schema = conn.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'entity_analytics'
            ORDER BY ordinal_position
        """).fetchall()
        
        for col, dtype in schema:
            print(f"- {col}: {dtype}")
        
        # Get some interesting metrics
        print("\nEntity Metrics:")
        metrics = conn.execute("""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT entity_id) as unique_entities,
                COUNT(DISTINCT category) as categories,
                COUNT(DISTINCT subcategory) as subcategories,
                COUNT(DISTINCT CASE WHEN tick IS NOT NULL THEN entity_id END) as entities_with_tick
            FROM entity_analytics
        """).fetchone()
        
        print(f"Total Rows: {metrics[0]}")
        print(f"Unique Entities: {metrics[1]}")
        print(f"Categories: {metrics[2]}")
        print(f"Subcategories: {metrics[3]}")
        print(f"Entities with Tick: {metrics[4]}")
        
        # Look at some high-priority companies (those with ticks)
        print("\nSample Companies with Ticks:")
        companies = conn.execute("""
            SELECT DISTINCT
                entity_id,
                tick,
                category,
                subcategory,
                -- Add any other relevant columns here
                COUNT(*) OVER (PARTITION BY entity_id) as mention_count
            FROM entity_analytics
            WHERE tick IS NOT NULL
            ORDER BY mention_count DESC
            LIMIT 10
        """).fetchall()
        
        for company in companies:
            print(f"\nCompany ID: {company[0]}")
            print(f"  Tick: {company[1]}")
            print(f"  Category: {company[2]} > {company[3]}")
            print(f"  Mentions: {company[4]}")
        
        # Save findings to a JSON file
        output = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "database": str(PORT_DB),
                "total_entities": metrics[1],
                "entities_with_tick": metrics[4]
            },
            "schema": {col: dtype for col, dtype in schema},
            "sample_companies": [
                {
                    "entity_id": c[0],
                    "tick": c[1],
                    "category": c[2],
                    "subcategory": c[3],
                    "mentions": c[4]
                }
                for c in companies
            ]
        }
        
        with open('port_analysis.json', 'w') as f:
            json.dump(output, f, indent=2)
            print("\nAnalysis saved to port_analysis.json")
        
    finally:
        conn.close()

if __name__ == "__main__":
    examine_port_data() 