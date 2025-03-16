#!/usr/bin/env python3
import os

import duckdb


def main() -> None:
    conn = duckdb.connect(f"md:port5?token={os.getenv('MOTHERDUCK_TOKEN')}")

    # Total count
    conn.execute("SELECT COUNT(*) as count FROM current_universe").fetchone()[0]

    # Missing fields
    missing = conn.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE ticker IS NULL) as missing_ticker,
            COUNT(*) FILTER (WHERE security_name IS NULL) as missing_name,
            COUNT(*) FILTER (WHERE workflow IS NULL) as missing_workflow,
            COUNT(*) FILTER (WHERE tick IS NULL) as missing_tick
        FROM current_universe
    """,
    ).fetchdf()
    for _col in missing.columns:
        pass

    # Workflow breakdown
    workflow = conn.execute(
        """
        SELECT
            workflow,
            COUNT(*) as count
        FROM current_universe
        WHERE workflow IS NOT NULL
        GROUP BY workflow
        ORDER BY count DESC
    """,
    ).fetchdf()
    for _, _row in workflow.iterrows():
        pass

    # Final filtered count
    conn.execute(
        """
        SELECT COUNT(*) as count
        FROM current_universe
        WHERE ticker IS NOT NULL
            AND security_name IS NOT NULL
            AND workflow IS NOT NULL
            AND workflow != 'excluded'
            AND workflow != 'ignore'
            AND tick IS NOT NULL
    """,
    ).fetchone()[0]


if __name__ == "__main__":
    main()
