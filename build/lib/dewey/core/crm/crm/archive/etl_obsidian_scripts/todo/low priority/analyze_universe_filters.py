#!/usr/bin/env python3
import duckdb
import os

def main():
    conn = duckdb.connect(f"md:port5?token={os.getenv('MOTHERDUCK_TOKEN')}")

    print('=== Universe Size Breakdown ===')

    # Total count
    total = conn.execute('SELECT COUNT(*) as count FROM current_universe').fetchone()[0]
    print(f'\nTotal rows: {total}')

    # Missing fields
    missing = conn.execute('''
        SELECT 
            COUNT(*) FILTER (WHERE ticker IS NULL) as missing_ticker,
            COUNT(*) FILTER (WHERE security_name IS NULL) as missing_name,
            COUNT(*) FILTER (WHERE workflow IS NULL) as missing_workflow,
            COUNT(*) FILTER (WHERE tick IS NULL) as missing_tick
        FROM current_universe
    ''').fetchdf()
    print('\nMissing Fields:')
    for col in missing.columns:
        print(f'{col}: {missing[col].iloc[0]}')

    # Workflow breakdown
    workflow = conn.execute('''
        SELECT 
            workflow,
            COUNT(*) as count
        FROM current_universe
        WHERE workflow IS NOT NULL
        GROUP BY workflow
        ORDER BY count DESC
    ''').fetchdf()
    print('\nWorkflow Distribution:')
    for _, row in workflow.iterrows():
        print(f'{row["workflow"]}: {row["count"]}')

    # Final filtered count
    filtered = conn.execute('''
        SELECT COUNT(*) as count
        FROM current_universe 
        WHERE ticker IS NOT NULL
            AND security_name IS NOT NULL
            AND workflow IS NOT NULL
            AND workflow != 'excluded'
            AND workflow != 'ignore'
            AND tick IS NOT NULL
    ''').fetchone()[0]
    print(f'\nFinal filtered count: {filtered}')

if __name__ == "__main__":
    main() 