# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""API package for EthiFinX.

This package provides FastAPI-based endpoints for serving data to the TUI interface.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="EthiFinX API",
    description="API for EthiFinX TUI interface",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="EthiFinX API",
        version="0.1.0",
        description="""
        EthiFinX API provides endpoints for ethical financial analysis and portfolio management.

        Key Features:
        * Company information and tick values
        * Historical data tracking
        * Pagination and sorting support
        * Real-time updates
        """,
        routes=app.routes,
    )

    # Add additional schema information
    openapi_schema["info"]["x-logo"] = {
        "url": "https://ethifinx.com/logo.png",  # Replace with actual logo URL
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from .companies import router as companies_router

app.include_router(companies_router, prefix="/api/v1", tags=["companies"])
