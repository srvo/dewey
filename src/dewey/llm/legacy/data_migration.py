
# Refactored from: data_migration
# Date: 2025-03-16T16:19:08.442884
# Refactor Version: 1.0
# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash rate limited. Cooling down for 5 minutes.

import json

import duckdb


def import_markdown_to_research() -> None:
    # Connect to both databases
    research_conn = duckdb.connect("data/research.duckdb")
    port_conn = duckdb.connect("data/port.duckdb")

    try:
        # Begin transaction
        research_conn.execute("BEGIN TRANSACTION")

        # Get markdown sections from port database
        sections = port_conn.execute(
            """
            SELECT
                title,
                content,
                section_type,
                source_file,
                created_at,
                word_count,
                sentiment,
                has_pii,
                readability,
                avg_sentence_length
            FROM markdown_sections
        """,
        ).fetchall()

        # Insert each section into research_iterations
        for section in sections:
            # Extract company ticker from content if possible
            content = section[1]
            ticker = None
            # Simple ticker extraction - can be enhanced
            if "**" in content:
                ticker_start = content.find("**") + 2
                ticker_end = content.find("**", ticker_start)
                if ticker_end > ticker_start:
                    potential_ticker = content[ticker_start:ticker_end].strip()
                    if "(" in potential_ticker and ")" in potential_ticker:
                        ticker = potential_ticker[
                            potential_ticker.find("(") + 1 : potential_ticker.find(")")
                        ]

            if not ticker:
                continue  # Skip if no ticker found

            # Prepare metrics
            confidence_metrics = {
                "readability_score": section[8],  # readability
                "avg_sentence_length": section[9],
                "word_count": section[5],
            }

            # Map sentiment to risk factors
            risk_factors = []
            if section[6] == "negative 📉":
                risk_factors.append(
                    {"type": "sentiment", "level": "high", "source": section[3]},
                )
            elif section[6] == "neutral ➖":
                risk_factors.append(
                    {"type": "sentiment", "level": "medium", "source": section[3]},
                )

            research_conn.execute(
                """
                INSERT INTO research_iterations (
                    company_ticker,
                    iteration_type,
                    source_count,
                    summary,
                    confidence_metrics,
                    risk_factors,
                    status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    ticker,
                    section[2],  # section_type as iteration_type
                    1,  # single source
                    content,
                    json.dumps(confidence_metrics),
                    json.dumps(risk_factors),
                    "imported",
                    section[4],  # created_at
                ),
            )

        # Commit transaction
        research_conn.execute("COMMIT")

    except Exception:
        research_conn.execute("ROLLBACK")
        raise
    finally:
        research_conn.close()
        port_conn.close()


if __name__ == "__main__":
    import_markdown_to_research()
