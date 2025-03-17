from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/v1/config/processing", tags=["processing"])

class FileSpecs(BaseModel):
    allowed_formats: List[str]
    max_size_mb: int
    required_columns: List[str]

class QualityMetrics(BaseModel):
    null_threshold: float
    duplicate_threshold: float
    freshness_hours: int

class ProcessingConfig(BaseModel):
    file_specs: FileSpecs
    quality_metrics: QualityMetrics

@router.post("", response_model=ProcessingConfig)
async def update_processing_config(config: ProcessingConfig):
    """Update data processing configuration"""
    # Implementation would go here
    pass

@router.get("", response_model=ProcessingConfig)
async def get_processing_config():
    """Get current processing configuration"""
    # Implementation would go here
    pass
