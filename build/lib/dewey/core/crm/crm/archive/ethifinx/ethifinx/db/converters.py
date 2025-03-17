"""
Database Format Converters
======================

Handles conversion between workflow outputs and database formats.
Ensures consistent data structure and safe database operations.

This module is specifically for converting between different data formats
and the database schema. It works in conjunction with data_processing.py
which handles the general data processing pipeline.
"""

from typing import Dict, Any, Optional, TypedDict
from datetime import datetime
from ..research.workflows.analysis_tagger import AnalysisTags, AnalysisSummary
from ..core.logger import setup_logger

logger = setup_logger("db_converters", "logs/db_converters.log")


class DatabaseAnalysis(TypedDict):
    """
    Database-ready analysis format.
    Maps directly to database schema defined in models.py.
    """

    structured_data: Dict[str, Any]  # Maps to research_results.structured_data
    raw_results: Dict[str, Any]  # Maps to research_results.raw_results
    summary: str  # Maps to research_results.summary
    risk_score: int  # Maps to research_results.risk_score
    confidence_score: int  # Maps to research_results.confidence_score
    recommendation: str  # Maps to research_results.recommendation
    source_categories: Dict[str, Any]  # Maps to research_results.source_categories
    metadata: Dict[str, Any]  # Maps to research_results.metadata


def workflow_to_database(
    workflow_output: Dict[str, Any], existing_data: Optional[Dict[str, Any]] = None
) -> DatabaseAnalysis:
    """
    Convert workflow output to database format.

    Args:
        workflow_output: Raw output from analysis workflow
        existing_data: Optional existing database data to merge with

    Returns:
        Database-ready format

    Raises:
        KeyError: If required workflow data is missing
        ValueError: If data validation fails
    """
    try:
        logger.debug("Converting workflow data to database format")
        tags: AnalysisTags = workflow_output["tags"]
        summary: AnalysisSummary = workflow_output["summary"]

        # Build structured data
        structured_data = {
            "concern_level": tags["concern_level"],
            "opportunity_score": tags["opportunity_score"],
            "interest_level": tags["interest_level"],
            "source_reliability": tags["source_reliability"],
            "key_concerns": tags["key_concerns"],
            "key_opportunities": tags["key_opportunities"],
            "confidence_score": tags["confidence_score"],
            "primary_themes": tags["primary_themes"],
        }

        # Merge with existing data if available
        if existing_data and "structured_data" in existing_data:
            logger.info("Merging with existing data")
            structured_data["history"] = existing_data["structured_data"].get(
                "history", []
            )
            structured_data["history"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "previous_data": existing_data["structured_data"],
                }
            )

        result = DatabaseAnalysis(
            structured_data=structured_data,
            raw_results={
                "workflow_output": workflow_output,
                "timestamp": datetime.now().isoformat(),
            },
            summary=summary["key_findings"],
            risk_score=_calculate_risk_score(tags),
            confidence_score=int(tags["confidence_score"] * 100),
            recommendation=summary["recommendation"],
            source_categories={
                "reliability_scores": [tags["source_reliability"]],
                "themes": tags["primary_themes"],
            },
            metadata={
                "last_processed": datetime.now().isoformat(),
                "workflow_version": workflow_output.get("metadata", {}).get(
                    "processing_version", "1.0"
                ),
                "original_metrics": workflow_output.get("metadata", {}),
            },
        )

        logger.info("Successfully converted workflow data to database format")
        return result

    except KeyError as e:
        logger.error("Missing required workflow data: %s", str(e))
        raise
    except Exception as e:
        logger.error("Error converting workflow data: %s", str(e), exc_info=True)
        raise


def database_to_workflow(database_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert database format back to workflow format.
    Useful for reprocessing or updating existing analyses.

    Args:
        database_data: Data from database

    Returns:
        Workflow-compatible format

    Raises:
        KeyError: If required database fields are missing
        ValueError: If data validation fails
    """
    try:
        logger.debug("Converting database data to workflow format")
        structured_data = database_data["structured_data"]

        tags = AnalysisTags(
            concern_level=structured_data["concern_level"],
            opportunity_score=structured_data["opportunity_score"],
            interest_level=structured_data["interest_level"],
            source_reliability=structured_data["source_reliability"],
            key_concerns=structured_data["key_concerns"],
            key_opportunities=structured_data["key_opportunities"],
            confidence_score=structured_data["confidence_score"] / 100,
            primary_themes=structured_data["primary_themes"],
        )

        summary = AnalysisSummary(
            key_findings=database_data["summary"],
            main_risks=_extract_risks(database_data),
            main_opportunities=_extract_opportunities(database_data),
            recommendation=database_data["recommendation"],
            next_steps=_extract_next_steps(database_data),
        )

        result = {
            "analysis_id": str(database_data.get("id", "unknown")),
            "timestamp": database_data.get(
                "last_updated_at", datetime.now()
            ).isoformat(),
            "tags": tags,
            "summary": summary,
            "metadata": database_data.get("metadata", {}),
        }

        logger.info("Successfully converted database data to workflow format")
        return result

    except KeyError as e:
        logger.error("Missing required database field: %s", str(e))
        raise
    except Exception as e:
        logger.error("Error converting database data: %s", str(e), exc_info=True)
        raise


def _calculate_risk_score(tags: AnalysisTags) -> int:
    """Calculate overall risk score from tags."""
    weights = {
        "concern_level": 0.4,
        "opportunity_score": -0.2,  # Higher opportunities reduce risk
        "source_reliability": -0.2,  # Higher reliability reduces risk
        "confidence_score": -0.2,  # Higher confidence reduces risk
    }

    score = sum(tags[key] * weight for key, weight in weights.items() if key in tags)

    return max(1, min(5, round(score * 5)))


def _extract_risks(data: Dict[str, Any]) -> str:
    """Extract risk information from database format."""
    structured_data = data["structured_data"]
    risks = structured_data.get("key_concerns", [])
    return "\n".join(f"- {risk}" for risk in risks)


def _extract_opportunities(data: Dict[str, Any]) -> str:
    """Extract opportunity information from database format."""
    structured_data = data["structured_data"]
    opportunities = structured_data.get("key_opportunities", [])
    return "\n".join(f"- {opp}" for opp in opportunities)


def _extract_next_steps(data: Dict[str, Any]) -> str:
    """Generate next steps based on database data."""
    structured_data = data["structured_data"]
    confidence = structured_data.get("confidence_score", 0)

    steps = []
    if confidence < 0.7:
        steps.append("Gather additional data to increase confidence")
    if structured_data.get("key_concerns"):
        steps.append("Investigate top concerns in detail")
    if structured_data.get("key_opportunities"):
        steps.append("Evaluate feasibility of identified opportunities")

    return "\n".join(f"- {step}" for step in steps)
