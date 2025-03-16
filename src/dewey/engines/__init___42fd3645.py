```python
"""Research Engines Package

Collection of search and analysis engines for the EthiFinX platform.

Available Engines:
---------------
- DuckDuckGoEngine: Web search using DuckDuckGo
- DeepSeekEngine: Content analysis using DeepSeek
- SearchEngine: Base class for search engines
- AnalysisEngine: Base class for analysis engines
"""

from .base import AnalysisEngine
from .base import BaseEngine
from .base import SearchEngine
from .ddg import DuckDuckGoEngine
from .deepseek import DeepSeekEngine

__all__ = [
    "BaseEngine",
    "SearchEngine",
    "AnalysisEngine",
    "DuckDuckGoEngine",
    "DeepSeekEngine",
]
```
