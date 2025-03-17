"""Test script for database safety features."""

from ethifinx.db.duckdb_store import get_connection

def test_safety():
    """Test the safety confirmation for destructive operations."""
    with get_connection() as conn:
        # Try a destructive operation
        print("\nTesting DROP operation...")
        conn.execute('DROP TABLE IF EXISTS test_table')
        
        # Try a safe operation
        print("\nTesting SELECT operation...")
        conn.execute('SELECT COUNT(*) FROM research_sources')

if __name__ == "__main__":
    test_safety() 