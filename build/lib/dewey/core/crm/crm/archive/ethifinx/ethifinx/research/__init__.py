"""Research package for data analysis and workflows."""

from .workflow import Workflow, WorkflowPhase
from .engines.base import BaseEngine
from .engines.api_docs import APIDocEngine
from .engines.ddg import DuckDuckGoEngine
from .engines.deepseek import DeepSeekEngine

__all__ = [
    "Workflow",
    "WorkflowPhase",
    "BaseEngine",
    "APIDocEngine",
    "DuckDuckGoEngine",
    "DeepSeekEngine",
]
