from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List

router = APIRouter(prefix="/api/v1/validation/rules", tags=["validation"])

class ValueRange(BaseModel):
    min: float
    max: float

class FinancialDataRules(BaseModel):
    required_fields: List[str]
    value_ranges: Dict[str, ValueRange]

class MarketDataRules(BaseModel):
    price_change_thresholds: Dict[str, float]

class ValidationRules(BaseModel):
    financial_data: FinancialDataRules
    market_data: MarketDataRules

@router.post("", response_model=ValidationRules)
async def update_validation_rules(rules: ValidationRules):
    """Update validation rules"""
    # Implementation would go here
    pass

@router.get("", response_model=ValidationRules)
async def get_validation_rules():
    """Get current validation rules"""
    # Implementation would go here
    pass
