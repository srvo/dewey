"""Research Module

This module provides tools for company research and analysis.
"""

from src.ui.ethifinx.research.engines.deepseek import DeepSeekEngine
from src.ui.ethifinx.research.search_flow import (
    ResearchWorkflow,
    get_company_by_ticker,
    get_research_status,
    get_top_companies,
)
from src.ui.ethifinx.research.workflows.analysis_tagger import AnalysisTaggingWorkflow

__all__ = [
    "get_top_companies",
    "get_company_by_ticker",
    "get_research_status",
    "ResearchWorkflow",
    "AnalysisTaggingWorkflow",
    "DeepSeekEngine",
]
