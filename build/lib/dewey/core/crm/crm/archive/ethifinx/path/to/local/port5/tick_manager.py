class TickManagerApp:
    def __init__(self):
        self.connection_status = "disconnected"
        self.api_client = ApiClient()

    async def run_test(self):
        self.connection_status = await self.api_client.check_connection()
        return self 