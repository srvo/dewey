from pathlib import Path

import duckdb

from db import get_connection


def check_schemas():
    """Check and compare schemas of both databases"""
    PORT_DB = Path("/Users/srvo/notebooks/data/port.duckdb")

    if not PORT_DB.exists():
        print(f"Port database not found at: {PORT_DB}")
        return

    print("Checking Port database schema...")
    port_conn = duckdb.connect(str(PORT_DB), read_only=True)

    try:
        # First, list all tables in Port database
        print("\nTables in Port database:")
        tables = port_conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
        """
        ).fetchall()

        for (table,) in tables:
            print(f"- {table}")

            # Show schema for each table
            print("\nSchema:")
            table_schema = port_conn.execute(
                f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """
            ).fetchall()

            for col, dtype, nullable in table_schema:
                print(f"  {col}: {dtype} {'(nullable)' if nullable == 'YES' else ''}")

            # Show sample data
            print("\nSample data:")
            sample = port_conn.execute(
                f"""
                SELECT *
                FROM "{table}"
                LIMIT 1
            """
            ).fetchall()

            if sample:
                columns = port_conn.execute(
                    f"SELECT * FROM {table} LIMIT 0"
                ).description
                for col, val in zip([desc[0] for desc in columns], sample[0]):
                    print(f"  {col}: {val}")
            print("\n" + "-" * 50)

        # Check our research database schema
        print("\nResearch Database Schema:")
        with get_connection() as conn:
            research_schema = conn.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'companies'
                ORDER BY ordinal_position
            """
            ).fetchall()

            for col, dtype, nullable in research_schema:
                print(f"{col}: {dtype} {'(nullable)' if nullable == 'YES' else ''}")

    except Exception as e:
        print(f"Error checking schemas: {str(e)}")
        raise e
    finally:
        port_conn.close()


if __name__ == "__main__":
    check_schemas()
