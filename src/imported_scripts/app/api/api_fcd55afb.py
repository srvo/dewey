from app.api.routers.extractor import extractor_router
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(extractor_router, prefix="/api/extractor")
