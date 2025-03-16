```python
"""Research package for data analysis and workflows."""

from .engines.api_docs import APIDocEngine
from .engines.base import BaseEngine
from .engines.ddg import DuckDuckGoEngine
from .engines.deepseek import DeepSeekEngine
from .workflow import Workflow, WorkflowPhase

__all__ = [
    "Workflow",
    "WorkflowPhase",
    "BaseEngine",
    "APIDocEngine",
    "DuckDuckGoEngine",
    "DeepSeekEngine",
]
```
