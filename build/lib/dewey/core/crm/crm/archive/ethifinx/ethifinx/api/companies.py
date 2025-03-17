"""Companies API router for EthiFinX."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from fastapi import APIRouter, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field, validator

from ..db.data_store import DataStore
from ..core.config import get_settings

router = APIRouter()

class SortOrder(str, Enum):
    """Sort order enumeration."""
    ASC = "asc"
    DESC = "desc"

class SortField(str, Enum):
    """Available sort fields."""
    TICKER = "ticker"
    COMPANY = "company"
    TICK = "tick"
    LAST_UPDATED = "last_updated"

class TickUpdate(BaseModel):
    """Model for tick value updates."""
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Company ticker symbol",
        example="AAPL"
    )
    new_tick: int = Field(
        ...,
        ge=-100,
        le=100,
        description="New tick value",
        example=42
    )
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="Update note",
        example="Increased due to positive ethical assessment"
    )

    @validator("ticker")
    def validate_ticker(cls, v):
        """Validate ticker format."""
        if not v.isalnum():
            raise ValueError("Ticker must be alphanumeric")
        return v.upper()

class Company(BaseModel):
    """Base company model."""
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Company ticker symbol",
        example="AAPL"
    )
    company: str = Field(
        ...,
        min_length=1,
        description="Company name",
        example="Apple Inc."
    )
    tick: int = Field(
        ...,
        ge=-100,
        le=100,
        description="Current tick value",
        example=42
    )

    class Config:
        schema_extra = {
            "example": {
                "ticker": "AAPL",
                "company": "Apple Inc.",
                "tick": 42
            }
        }

class CompanyDetail(Company):
    """Detailed company model including history metadata."""
    last_updated: datetime = Field(
        ...,
        description="Last tick update timestamp",
        example="2024-01-07T12:34:56Z"
    )
    last_note: Optional[str] = Field(
        None,
        description="Last update note",
        example="Updated based on environmental report"
    )
    history_count: int = Field(
        ...,
        ge=0,
        description="Number of historical tick changes",
        example=5
    )

    class Config:
        schema_extra = {
            "example": {
                "ticker": "AAPL",
                "company": "Apple Inc.",
                "tick": 42,
                "last_updated": "2024-01-07T12:34:56Z",
                "last_note": "Updated based on environmental report",
                "history_count": 5
            }
        }

class HistoryEntry(BaseModel):
    """Model for tick history entries."""
    timestamp: datetime
    old_tick: int = Field(..., ge=-100, le=100)
    new_tick: int = Field(..., ge=-100, le=100)
    note: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "timestamp": "2024-01-07T12:34:56Z",
                "old_tick": 38,
                "new_tick": 42,
                "note": "Increased due to improved sustainability metrics"
            }
        }

class PaginatedCompanies(BaseModel):
    """Paginated response for companies list."""
    items: List[Company]
    total: int = Field(..., description="Total number of items", example=100)
    page: int = Field(..., description="Current page number", example=1)
    per_page: int = Field(..., description="Items per page", example=20)
    total_pages: int = Field(..., description="Total number of pages", example=5)

    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "ticker": "AAPL",
                        "company": "Apple Inc.",
                        "tick": 42
                    },
                    {
                        "ticker": "MSFT",
                        "company": "Microsoft Corporation",
                        "tick": 38
                    }
                ],
                "total": 100,
                "page": 1,
                "per_page": 20,
                "total_pages": 5
            }
        }

@router.get("/companies", response_model=PaginatedCompanies)
async def get_companies(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: SortField = Query(SortField.TICKER, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.ASC, description="Sort order")
):
    """Get paginated list of companies.
    
    This endpoint supports:
    * Pagination
    * Sorting by multiple fields
    * Customizable page size
    """
    db = DataStore()
    try:
        companies = db.get_companies(
            page=page,
            per_page=per_page,
            sort_by=sort_by.value,
            sort_order=sort_order.value
        )
        total = db.get_company_count()
        total_pages = (total + per_page - 1) // per_page
        
        return PaginatedCompanies(
            items=companies,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/companies/{ticker}", response_model=CompanyDetail)
async def get_company(
    ticker: str = Path(..., description="Company ticker symbol", example="AAPL")
):
    """Get detailed information for a specific company."""
    db = DataStore()
    try:
        company = db.get_company_detail(ticker)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {ticker} not found")
        return company
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/companies/{ticker}/tick", response_model=CompanyDetail)
async def update_tick(
    ticker: str = Path(..., description="Company ticker symbol", example="AAPL"),
    update: TickUpdate = Body(..., description="Tick update data")
):
    """Update tick value for a company.
    
    This endpoint allows:
    * Updating tick values within range [-100, 100]
    * Adding optional notes for the update
    * Automatic timestamp recording
    """
    db = DataStore()
    try:
        company = db.update_tick_value(
            ticker=ticker,
            new_tick=update.new_tick,
            note=update.note
        )
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {ticker} not found")
        return company
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/companies/{ticker}/history", response_model=List[HistoryEntry])
async def get_tick_history(
    ticker: str = Path(..., description="Company ticker symbol", example="AAPL"),
    limit: int = Query(20, ge=1, le=100, description="Number of history entries to return")
):
    """Get tick value history for a company.
    
    Returns the most recent tick value changes, ordered by timestamp descending.
    """
    db = DataStore()
    try:
        history = db.get_tick_history(ticker, limit=limit)
        if history is None:
            raise HTTPException(status_code=404, detail=f"Company {ticker} not found")
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 