import os
from datetime import datetime

import duckdb


def analyze_data_types(conn, table):
    """Analyze data types and determine appropriate SQL data types."""
    schema = conn.execute(f"DESCRIBE {table}").fetchdf()
    sample = conn.execute(f"SELECT * FROM {table} LIMIT 100").fetchdf()

    data_types = {}
    for col in sample.columns:
        if col not in data_types:
            data_types[col] = schema[schema["column_name"] == col]["column_type"].iloc[
                0
            ]

    return data_types


def identify_potential_relationships(conn, tables):
    """Identify potential relationships between tables based on column names."""
    relationships = []

    # Get schemas for all tables
    schemas = {}
    for table in tables:
        schemas[table] = conn.execute(f"DESCRIBE {table}").fetchdf()

    # Common primary key patterns
    id_patterns = ["_id", "id", "code", "key", "symbol", "ticker"]

    # Find potential relationships
    for table1 in tables:
        cols1 = schemas[table1]["column_name"].tolist()

        for table2 in tables:
            if table1 == table2:
                continue

            cols2 = schemas[table2]["column_name"].tolist()

            # Check for columns that might be related
            for col1 in cols1:
                for col2 in cols2:
                    # Same name suggests a relationship
                    if col1 == col2:
                        # Check if it's a likely key column
                        is_likely_key = any(
                            pattern in col1.lower() for pattern in id_patterns
                        )
                        if is_likely_key or col1.lower() in [
                            "symbol",
                            "ticker",
                            "email",
                        ]:
                            relationships.append(
                                {
                                    "table1": table1,
                                    "column1": col1,
                                    "table2": table2,
                                    "column2": col2,
                                    "relationship_type": "potential_join",
                                    "confidence": "high" if is_likely_key else "medium",
                                }
                            )

    return relationships


def generate_documentation(output_file="database_documentation.md"):
    """Generate comprehensive database documentation with table relationships."""
    # Connect to MotherDuck
    conn = duckdb.connect(f"md:dewey?motherduck_token={os.environ['MOTHERDUCK_TOKEN']}")

    # Get all tables
    tables = conn.execute("SHOW TABLES").fetchdf()["name"].tolist()

    # Get table information
    table_info = {}
    for table in tables:
        try:
            # Get schema
            schema = conn.execute(f"DESCRIBE {table}").fetchdf()

            # Get row count
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

            # Get sample data
            sample = conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchdf()

            # Get data types
            data_types = analyze_data_types(conn, table)

            table_info[table] = {
                "row_count": count,
                "schema": schema.to_dict("records"),
                "sample": sample.to_dict("records") if not sample.empty else [],
                "data_types": data_types,
            }
        except Exception as e:
            print(f"Error analyzing table {table}: {str(e)}")
            table_info[table] = {"error": str(e)}

    # Identify potential relationships
    relationships = identify_potential_relationships(conn, tables)

    # Group tables by category
    table_categories = {
        "Portfolio Tables": [
            "growth_sheets",
            "income_sheets",
            "diversification_sheets",
        ],
        "Reference Tables": ["universe_sheets", "exclude_sheets", "preferreds_sheets"],
        "History Tables": ["tick_history_sheets", "weighting_history_sheets"],
        "Core System Tables": ["contacts", "emails", "email_analyses"],
        "Other Tables": [
            t
            for t in tables
            if t
            not in [
                "growth_sheets",
                "income_sheets",
                "diversification_sheets",
                "universe_sheets",
                "exclude_sheets",
                "preferreds_sheets",
                "tick_history_sheets",
                "weighting_history_sheets",
                "contacts",
                "emails",
                "email_analyses",
            ]
        ],
    }

    # Generate documentation
    with open(output_file, "w") as f:
        # Header
        f.write("# Database Documentation - MotherDuck:dewey\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total tables: {len(tables)}\n\n")

        # Table of Contents
        f.write("## Table of Contents\n\n")
        for category, category_tables in table_categories.items():
            f.write(f"- [{category}](#{category.lower().replace(' ', '-')})\n")
            for table in category_tables:
                if table in tables:
                    f.write(f"  - [{table}](#{table.lower()})\n")

        f.write("- [Table Relationships](#table-relationships)\n\n")

        # Tables by Category
        for category, category_tables in table_categories.items():
            f.write(f"## {category}\n\n")

            relevant_tables = [t for t in category_tables if t in tables]
            if not relevant_tables:
                f.write("No tables in this category.\n\n")
                continue

            for table in relevant_tables:
                f.write(f"### {table}\n\n")

                info = table_info.get(table, {})
                if "error" in info:
                    f.write(f"Error analyzing table: {info['error']}\n\n")
                    continue

                f.write(f"**Row count:** {info.get('row_count', 'Unknown')}\n\n")

                # Table schema
                f.write("#### Schema\n\n")
                f.write("| Column | Type | Description |\n")
                f.write("|--------|------|-------------|\n")

                schema = info.get("schema", [])
                for col in schema:
                    col_name = col.get("column_name", "")
                    col_type = col.get("column_type", "")

                    # Generate description based on column name
                    description = ""
                    lower_name = col_name.lower()
                    if "id" == lower_name or lower_name.endswith("_id"):
                        description = "Unique identifier"
                    elif "name" in lower_name:
                        description = "Name/description"
                    elif "date" in lower_name:
                        description = "Date/timestamp"
                    elif "email" in lower_name:
                        description = "Email address"
                    elif "symbol" in lower_name or "ticker" in lower_name:
                        description = "Stock symbol/ticker"
                    elif "price" in lower_name:
                        description = "Price value"
                    elif "yield" in lower_name:
                        description = "Yield percentage"
                    elif "weight" in lower_name:
                        description = "Weighting percentage"

                    f.write(f"| {col_name} | {col_type} | {description} |\n")

                f.write("\n")

                # Sample data
                f.write("#### Sample Data\n\n")

                sample = info.get("sample", [])
                if sample:
                    columns = list(sample[0].keys())
                    f.write("| " + " | ".join(columns) + " |\n")
                    f.write("| " + " | ".join(["---"] * len(columns)) + " |\n")

                    for row in sample:
                        f.write(
                            "| "
                            + " | ".join(
                                [
                                    str(row.get(col, "")).replace("\n", "<br>")
                                    for col in columns
                                ]
                            )
                            + " |\n"
                        )
                else:
                    f.write("No sample data available.\n")

                f.write("\n")

        # Table Relationships
        f.write("## Table Relationships\n\n")
        f.write(
            "| Table 1 | Column 1 | Table 2 | Column 2 | Relationship Type | Confidence |\n"
        )
        f.write(
            "|---------|----------|---------|----------|-------------------|------------|\n"
        )

        for rel in sorted(relationships, key=lambda x: (x["table1"], x["table2"])):
            f.write(
                f"| {rel['table1']} | {rel['column1']} | {rel['table2']} | {rel['column2']} | {rel['relationship_type']} | {rel['confidence']} |\n"
            )

    conn.close()
    print(f"Documentation generated: {output_file}")


if __name__ == "__main__":
    generate_documentation()
