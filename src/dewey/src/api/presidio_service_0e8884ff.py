from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from pydantic import BaseModel

# Get configuration from environment variables
PORT = int(os.getenv("PORT", "8001"))
HOST = os.getenv("HOST", "0.0.0.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# Initialize Presidio engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

app = FastAPI(
    title="Presidio Service",
    description="Service for detecting and anonymizing PII using Microsoft Presidio",
    version="1.0.0",
)


class TextRequest(BaseModel):
    text: str
    language: str = "en"
    entities: list[str] | None = None


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_text(request: TextRequest) -> dict:
    """Analyze text for PII entities."""
    try:
        # Analyze text
        results = analyzer.analyze(
            text=request.text,
            language=request.language,
            entities=request.entities,
        )

        return {"results": [result.to_dict() for result in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/anonymize")
async def anonymize_text(request: TextRequest) -> dict:
    """Analyze and anonymize text containing PII."""
    try:
        # First analyze the text
        analyzer_results = analyzer.analyze(
            text=request.text,
            language=request.language,
            entities=request.entities,
        )

        # Then anonymize the findings
        anonymized_text = anonymizer.anonymize(
            text=request.text,
            analyzer_results=analyzer_results,
        )

        return {
            "original_text": request.text,
            "anonymized_text": anonymized_text.text,
            "entities": [result.to_dict() for result in analyzer_results],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/supported-entities")
async def get_supported_entities() -> dict[str, list[str]]:
    """Get list of supported PII entity types."""
    return {
        "entities": [
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "CRYPTO",
            "DOMAIN_NAME",
            "IP_ADDRESS",
            "US_SSN",
            "US_BANK_NUMBER",
            "LOCATION",
            "DATE_TIME",
            "NRP",
            "MEDICAL_LICENSE",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL)
