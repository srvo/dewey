#!/usr/bin/env python3
"""Script to run the EthiFinX API server."""

import uvicorn
from ethifinx.api import app
from ethifinx.core.config import get_settings

def main():
    """Run the API server."""
    settings = get_settings()
    uvicorn.run(
        "ethifinx.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug_mode
    )

if __name__ == "__main__":
    main() 