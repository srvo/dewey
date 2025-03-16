import logging

from app.api.models import RequestData
from app.services.extractor import ExtractorService
from fastapi import APIRouter

extractor_router = r = APIRouter()

logger = logging.getLogger("uvicorn")


@r.post("/query")
async def query_request(data: RequestData):
    return await ExtractorService.extract(query=data.query, model_code=data.code)
