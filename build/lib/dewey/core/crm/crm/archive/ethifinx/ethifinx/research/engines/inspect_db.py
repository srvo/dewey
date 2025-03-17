import duckdb
import os
from pathlib import Path


def inspect_db():
    try:
        # Try multiple possible locations for the database
        possible_paths = [
            Path("research_results/research.db"),
            Path("jupyter/research/research_results/research.db"),
            Path(os.path.expanduser("~/notebooks/research_results/research.db")),
            Path(
                os.path.expanduser(
                    "~/notebooks/jupyter/research/research_results/research.db"
                )
            ),
            Path.cwd() / "research_results" / "research.db",
        ]

        db_path = None
        for path in possible_paths:
            if path.exists():
                db_path = path
                print(f"Found database at {path}")
                break

        if not db_path:
            print("Could not find research.db in any expected location")
            return

        # Connect to the database
        con = duckdb.connect(str(db_path))

        # List all tables
        print("\nTables in database:")
        tables = con.execute("SHOW TABLES").fetchall()
        print(tables)

        if tables:
            for table in tables:
                table_name = table[0]
                print(f"\nSchema for {table_name}:")
                schema = con.execute(f"DESCRIBE {table_name}").fetchall()
                for col in schema:
                    print(col)

                print(f"\nFirst few rows of {table_name}:")
                rows = con.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
                for row in rows:
                    print(row)
        else:
            print("No tables found in database")

    except Exception as e:
        print(f"Error inspecting database: {e}")
    finally:
        if "con" in locals():
            con.close()


if __name__ == "__main__":
    inspect_db()
