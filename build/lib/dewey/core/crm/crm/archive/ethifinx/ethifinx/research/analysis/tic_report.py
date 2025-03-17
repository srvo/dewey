"""TICK Score Analysis Report.

Retrieves and analyzes top companies by TICK score from the database.
"""

from typing import List, Dict, Any
from ...db.duckdb_store import get_connection


def get_top_companies_by_tick(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve top companies by TICK score.
    
    Args:
        limit: Maximum number of companies to retrieve
        
    Returns:
        List of company data dictionaries
    """
    with get_connection() as conn:
        # Get the latest TICK score for each company using window functions
        results = conn.execute("""
            WITH latest_ticks AS (
                SELECT 
                    ticker,
                    new_tick,
                    date,
                    note,
                    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
                FROM tick_history
            )
            SELECT 
                t.ticker,
                u.name as company_name,
                u.sector,
                t.new_tick as tick_score,
                t.date as analysis_date,
                t.note
            FROM latest_ticks t
            JOIN universe u ON t.ticker = u.ticker
            WHERE t.rn = 1
            ORDER BY t.new_tick DESC
            LIMIT ?
        """, [limit]).fetchall()
        
        return [{
            'ticker': row[0],
            'company_name': row[1],
            'sector': row[2],
            'tick_score': row[3],
            'analysis_date': row[4],
            'note': row[5]
        } for row in results]


def main():
    """Display top companies by TICK score."""
    try:
        top_companies = get_top_companies_by_tick(limit=10)
        
        if not top_companies:
            print("\nNo TICK scores found in the database.")
            return
            
        print("\nTop Companies by TICK Score:")
        print("-" * 80)
        
        for idx, company in enumerate(top_companies, 1):
            print(f"\n{idx}. {company['company_name']} ({company['ticker']})")
            print(f"   TICK Score: {company['tick_score']}")
            print(f"   Sector: {company['sector'] or 'N/A'}")
            print(f"   Analysis Date: {company['analysis_date']}")
            if company['note']:
                print(f"   Note: {company['note']}")
            
    except Exception as e:
        print(f"Error retrieving TICK scores: {str(e)}")
        raise  # Re-raise the exception to see the full traceback
        
        
if __name__ == "__main__":
    main() 