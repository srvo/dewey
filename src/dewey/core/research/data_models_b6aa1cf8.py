```python
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Source(BaseModel):
    """Represents a source of information."""

    id: str
    name: str
    url: Optional[str] = None
    type: str  # e.g., SEC, news, research paper
    reliability_score: float = 1.0


class ResearchQuestion(BaseModel):
    """Represents a research question."""

    id: str
    text: str
    related_companies: List[str] = []
    related_questions: List[str] = []
    priority: int = 5
    last_updated: datetime = datetime.now()


class CompanyEvaluation(BaseModel):
    """Represents an evaluation of a company."""

    ticker: str
    name: str
    research_questions: List[ResearchQuestion] = []
    sources: List[Source] = []
    key_people: List[str] = []
    key_events: List[str] = []
    tick_value: int = 0
    last_updated: datetime = datetime.now()
    tags: List[str] = []


class CrossCompanyLink(BaseModel):
    """Represents a link between companies based on a research question."""

    question_id: str
    company_ids: List[str]
    insights: List[str] = []
    sources: List[Source] = []
```
