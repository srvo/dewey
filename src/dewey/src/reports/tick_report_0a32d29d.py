```python
"""TICK Score Analysis Report.

Retrieves and analyzes top companies by TICK score from the database.
"""

from typing import Any, Dict, List

from sqlalchemy import desc

from ...db import get_db_session
from ...db.models import CompanyAnalysis


def get_top_companies_by_tick(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve top companies by TICK score.

    Args:
        limit: Maximum number of companies to retrieve.

    Returns:
        List of company data dictionaries.
    """
    with get_db_session() as session:
        results = (
            session.query(CompanyAnalysis)
            .order_by(
                desc(CompanyAnalysis.structured_data["tick"].astext.cast(float))
            )
            .limit(limit)
            .all()
        )

        return [_format_company_data(result) for result in results]


def _format_company_data(result: CompanyAnalysis) -> Dict[str, Any]:
    """Format company analysis result into a dictionary.

    Args:
        result: The CompanyAnalysis object.

    Returns:
        A dictionary containing formatted company data.
    """
    return {
        "company_id": result.company_id,
        "tick_score": result.structured_data.get("tick"),
        "analysis_date": result.timestamp,
        "key_factors": result.structured_data.get("key_factors", []),
        "confidence": result.structured_data.get("confidence", 0.0),
    }


def display_top_companies(top_companies: List[Dict[str, Any]]) -> None:
    """Display top companies by TICK score.

    Args:
        top_companies: A list of dictionaries containing company data.
    """
    print("\nTop Companies by TICK Score:")
    print("-" * 80)

    for idx, company in enumerate(top_companies, 1):
        print(f"\n{idx}. Company ID: {company['company_id']}")
        print(f"   TICK Score: {company['tick_score']}")
        print(f"   Analysis Date: {company['analysis_date']}")
        print(f"   Confidence: {company['confidence']:.2f}")
        print(f"   Key Factors: {', '.join(company['key_factors'])}")


def main() -> None:
    """Main function to retrieve and display top companies by TICK score."""
    try:
        top_companies = get_top_companies_by_tick(limit=10)
        display_top_companies(top_companies)

    except Exception as e:
        print(f"Error retrieving TICK scores: {str(e)}")


if __name__ == "__main__":
    main()
```
