"""Data analysis and schema recommendation agent."""
from pathlib import Path
from typing import Any

import pandas as pd
import structlog
from pydantic import BaseModel, Field

from .data_ingestion_agent import DataIngestionAgent

logger = structlog.get_logger(__name__)

async def analyze_data(
    data: Any,
    context: str | None = None,
) -> list[Any]:
    """Analyze data structure and content."""
    agent = DataIngestionAgent()
    return await agent.analyze_data(data, context)
