from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Source(BaseModel):
    id: str
    name: str
    url: Optional[str] = None
    type: str  # e.g., SEC, news, research paper
    reliability_score: float = 1.0

class ResearchQuestion(BaseModel):
    id: str
    text: str
    related_companies: List[str] = []
    related_questions: List[str] = []
    priority: int = 5
    last_updated: datetime = datetime.now()

class CompanyEvaluation(BaseModel):
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
    question_id: str
    company_ids: List[str]
    insights: List[str] = []
    sources: List[Source] = []