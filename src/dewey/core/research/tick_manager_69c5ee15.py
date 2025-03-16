```python
from typing import Optional


class ApiClient:
    """A mock API client for demonstration purposes."""

    async def check_connection(self) -> str:
        """Simulates checking the API connection."""
        return "connected"


class TickManagerApp:
    """
    A class to manage the tick data application.
    """

    def __init__(self) -> None:
        """
        Initializes the TickManagerApp with default values.
        """
        self.connection_status: str = "disconnected"
        self.api_client: ApiClient = ApiClient()

    async def run_test(self) -> "TickManagerApp":
        """
        Runs a test to check the API connection and update the connection status.

        Returns:
            TickManagerApp: The TickManagerApp instance with updated connection status.
        """
        self.connection_status = await self.api_client.check_connection()
        return self
```
