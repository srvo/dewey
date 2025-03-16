from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/config/integrations", tags=["integrations"])


class DataLakeConfig(BaseModel):
    connection_string: str
    access_key: str | None = None
    secret_key: str | None = None


class SECEdgarConfig(BaseModel):
    base_url: str
    rate_limit: str


class IntegrationConfig(BaseModel):
    data_lake: DataLakeConfig
    sec_edgar: SECEdgarConfig


@router.post("", response_model=IntegrationConfig)
async def update_integration_config(config: IntegrationConfig) -> None:
    """Update integration configurations."""
    # Implementation would go here


@router.get("", response_model=IntegrationConfig)
async def get_integration_config() -> None:
    """Get current integration configurations."""
    # Implementation would go here
