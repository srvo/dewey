# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Example Pydantic model update
from pydantic import BaseModel, Field


class Company(BaseModel):
    ticker: str = Field(..., description="Company ticker symbol", examples=["AAPL"])
    company: str
    tick: int

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "ticker": "AAPL",
                    "company": "Apple Inc.",
                    "tick": 0,
                },
            ],
        }
