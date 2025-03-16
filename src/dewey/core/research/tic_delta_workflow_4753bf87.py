```python
"""TIC Delta Analysis Workflow.

Analyzes changes in TIC scores over time, focusing on material changes
that could affect our assessment of revenue-impact alignment.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..engines.deepseek import DeepSeekEngine
from ...db.models import CompanyAnalysis, ResearchResult
from ...db.session import get_db_session


@dataclass
class TICChange:
    """Represents a material change in TIC assessment."""

    old_tic: int
    new_tic: float  # Suggested new score
    change_date: datetime
    key_factors: List[str]
    confidence: float


@dataclass
class DeltaAnalysis:
    """Analysis of changes since last TIC assessment."""

    material_changes: List[Dict[str, Any]]
    revenue_impact_changes: List[Dict[str, Any]]
    market_position_changes: List[Dict[str, Any]]
    scaling_potential_changes: List[Dict[str, Any]]
    confidence: float


class TICDeltaWorkflow:
    """Workflow for analyzing changes in TIC assessments over time."""

    def __init__(self, engine: DeepSeekEngine) -> None:
        """Initialize the workflow.

        Args:
            engine: The DeepSeek engine to use for analysis.
        """
        self.engine = engine
        self._initialize_templates()

    def _initialize_templates(self) -> None:
        """Initialize specialized analysis templates."""
        self.engine.add_template(
            "delta_analyzer",
            [
                {
                    "role": "system",
                    "content": """You are a precise change analyst focused on identifying
                material changes that affect our assessment of how company growth drives
                positive impact. Focus on concrete evidence of changes in revenue-impact
                alignment, scaling dynamics, and market position.""",
                }
            ],
        )

    async def analyze_tic_history(self, company_id: str, lookback_days: int = 90) -> List[TICChange]:
        """Analyze historical TIC changes.

        Args:
            company_id: Company identifier.
            lookback_days: Days to look back.

        Returns:
            List of significant TIC changes.
        """
        with get_db_session() as session:
            return self._get_tic_changes(session, company_id, lookback_days)

    def _get_tic_changes(self, session: Session, company_id: str, lookback_days: int) -> List[TICChange]:
        """Helper function to retrieve and process TIC changes from the database."""
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        analyses = (
            session.query(CompanyAnalysis)
            .filter(
                CompanyAnalysis.company_id == company_id,
                CompanyAnalysis.timestamp >= cutoff_date,
            )
            .order_by(CompanyAnalysis.timestamp.desc())
            .all()
        )

        changes = []
        for i in range(len(analyses) - 1):
            current = analyses[i]
            previous = analyses[i + 1]

            current_tic = current.structured_data.get("tic")
            previous_tic = previous.structured_data.get("tic")

            if current_tic != previous_tic:
                changes.append(
                    TICChange(
                        old_tic=previous_tic,
                        new_tic=current_tic,
                        change_date=current.timestamp,
                        key_factors=current.structured_data.get("change_factors", []),
                        confidence=current.structured_data.get("confidence", 0.0),
                    )
                )

        return changes

    async def analyze_recent_changes(
        self, company_data: Dict[str, Any], last_analysis_date: datetime
    ) -> DeltaAnalysis:
        """Analyze changes since last TIC assessment.

        Args:
            company_data: Current company data.
            last_analysis_date: Date of last analysis.

        Returns:
            Analysis of material changes.
        """
        with get_db_session() as session:
            new_research = self._get_recent_research(session, company_data["id"], last_analysis_date)

        prompt = f"""Analyze material changes for {company_data['name']} since our last
        assessment on {last_analysis_date.isoformat()}.

        Previous Assessment:
        {company_data.get('last_analysis', 'No previous analysis available')}

        New Information:
        {new_research}

        Focus on changes in:
        1. Revenue-Impact Alignment:
           - How revenue drives positive impact
           - Evidence of impact
           - Measurement and verification

        2. Scaling Potential:
           - Growth trajectory
           - Impact at scale
           - Scaling risks

        3. Market Position:
           - Competitive dynamics
           - Market share
           - Industry trends

        Format your response as JSON with the following structure:
        {{
            "material_changes": [
                {{
                    "category": str,
                    "description": str,
                    "evidence": str,
                    "significance": float  # 0-1 rating
                }}
            ],
            "revenue_impact_changes": [
                {{
                    "aspect": str,
                    "change": str,
                    "implication": str
                }}
            ],
            "market_position_changes": [
                {{
                    "aspect": str,
                    "change": str,
                    "implication": str
                }}
            ],
            "scaling_potential_changes": [
                {{
                    "aspect": str,
                    "change": str,
                    "implication": str
                }}
            ],
            "confidence": float  # 0-1 rating in change assessment
        }}
        """

        result = await self.engine.analyze(
            prompt, template_name="delta_analyzer", response_format="json"
        )

        return DeltaAnalysis(**result)

    def _get_recent_research(self, session: Session, company_id: str, last_analysis_date: datetime) -> str:
        """Helper function to retrieve recent research results from the database."""
        recent_results = (
            session.query(ResearchResult)
            .filter(
                ResearchResult.company_id == company_id,
                ResearchResult.timestamp > last_analysis_date,
            )
            .order_by(ResearchResult.timestamp.asc())
            .all()
        )

        new_research = "\n\n".join(
            f"Source: {r.source}\nTimestamp: {r.timestamp}\n{r.content}" for r in recent_results
        )
        return new_research

    async def suggest_tic_adjustment(
        self, company_data: Dict[str, Any], delta_analysis: DeltaAnalysis, current_tic: int
    ) -> Dict[str, Any]:
        """Suggest TIC score adjustment based on changes.

        Args:
            company_data: Company data.
            delta_analysis: Analysis of changes.
            current_tic: Current TIC score.

        Returns:
            TIC adjustment recommendation.
        """
        prompt = f"""Based on material changes in {company_data['name']}, evaluate whether
        our current TIC score of {current_tic} needs adjustment.

        Material Changes:
        {json.dumps(delta_analysis.material_changes, indent=2)}

        Revenue-Impact Changes:
        {json.dumps(delta_analysis.revenue_impact_changes, indent=2)}

        Scaling Changes:
        {json.dumps(delta_analysis.scaling_potential_changes, indent=2)}

        Market Changes:
        {json.dumps(delta_analysis.market_position_changes, indent=2)}

        Key Question: Have these changes materially affected how positive it would be
        for the world if this company grew 100x?

        Format your response as JSON with the following structure:
        {{
            "adjustment_needed": bool,
            "suggested_tic": int,
            "adjustment_size": int,  # +/- change
            "confidence": float,
            "key_reasons": List[str],
            "urgency": int,  # 1-5 scale
            "scaling_impact": {{
                "growth_positive": bool,
                "confidence": float,
                "key_evidence": List[str]
            }}
        }}
        """

        result = await self.engine.analyze(
            prompt, template_name="delta_analyzer", response_format="json"
        )

        return result

    async def run_delta_analysis(self, company_id: str, lookback_days: int = 90) -> Dict[str, Any]:
        """Run complete delta analysis workflow.

        Args:
            company_id: Company identifier.
            lookback_days: Days to look back.

        Returns:
            Complete analysis results.
        """
        with get_db_session() as session:
            current_analysis, company_data = self._get_company_data(session, company_id)

        # Analyze historical changes
        tic_history = await self.analyze_tic_history(company_id, lookback_days=lookback_days)

        # Analyze recent changes
        delta_analysis = await self.analyze_recent_changes(company_data, current_analysis.timestamp)

        # Get TIC adjustment recommendation
        adjustment = await self.suggest_tic_adjustment(
            company_data, delta_analysis, company_data["current_tic"]
        )

        return {
            "company_id": company_id,
            "timestamp": datetime.now().isoformat(),
            "tic_history": [change.__dict__ for change in tic_history],
            "delta_analysis": delta_analysis.__dict__,
            "adjustment": adjustment,
            "metadata": {
                "lookback_days": lookback_days,
                "confidence": delta_analysis.confidence,
                "last_analysis_date": company_data["last_analysis_date"].isoformat(),
            },
        }

    def _get_company_data(self, session: Session, company_id: str) -> tuple[CompanyAnalysis, dict[str, Any]]:
        """Helper function to retrieve company data from the database."""
        current_analysis = (
            session.query(CompanyAnalysis)
            .filter(CompanyAnalysis.company_id == company_id)
            .order_by(CompanyAnalysis.timestamp.desc())
            .first()
        )

        if not current_analysis:
            raise ValueError(f"No analysis found for company {company_id}")

        company_data = {
            "id": company_id,
            "last_analysis": current_analysis.structured_data,
            "current_tic": current_analysis.structured_data.get("tic"),
            "last_analysis_date": current_analysis.timestamp,
        }
        return current_analysis, company_data
```
