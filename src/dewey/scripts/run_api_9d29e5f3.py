```python
#!/usr/bin/env python3
"""Script to run the EthiFinX API server."""

import uvicorn

from ethifinx.api import app
from ethifinx.core.config import Settings, get_settings


def run_uvicorn(settings: Settings) -> None:
    """Runs the Uvicorn server with the given settings.

    Args:
        settings: The application settings.
    """
    uvicorn.run(
        "ethifinx.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug_mode,
    )


def main() -> None:
    """Runs the API server."""
    settings: Settings = get_settings()
    run_uvicorn(settings)


if __name__ == "__main__":
    main()
```
