```python
#!/usr/bin/env python3
"""Script to run the EthiFinX API server."""

import uvicorn

from ethifinx.api import app
from ethifinx.core.config import get_settings


def run_api_server(host: str, port: int, reload: bool) -> None:
    """Runs the Uvicorn server for the EthiFinX API.

    Args:
        host: The host address to bind to.
        port: The port to listen on.
        reload: Whether to enable auto-reloading.
    """
    uvicorn.run(
        "ethifinx.api:app",
        host=host,
        port=port,
        reload=reload
    )


def main() -> None:
    """Main function to start the EthiFinX API server."""
    settings = get_settings()
    run_api_server(settings.api_host, settings.api_port, settings.debug_mode)


if __name__ == "__main__":
    main()
```
