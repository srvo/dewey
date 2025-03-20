from dewey.core.base_script import BaseScript

# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""API server lifecycle management."""

import multiprocessing
import socket
import time
from contextlib import contextmanager

import requests
import uvicorn

from ..core.config import get_settings

    def run(self) -> None:
        """
        Run the script.
        """
        # TODO: Implement script logic here
        raise NotImplementedError("The run method must be implemented")


class APIServer(BaseScript):
    """API server manager."""

    def __init__(self) -> None:
        """Initialize the API server manager."""
        self.settings = get_settings()
        self.process = None

    def _is_port_in_use(self):
        """Check if the API port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", self.settings.api_port)) == 0

    def _wait_for_server(self, timeout=5) -> bool:
        """Wait for the server to start."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                requests.get(f"http://localhost:{self.settings.api_port}/api/docs")
                return True
            except requests.RequestException:
                time.sleep(0.1)
        return False

    def start(self):
        """Start the API server in a background process."""
        if self._is_port_in_use():
            # Server might already be running
            return True

        def run_server() -> None:
            """Run the uvicorn server."""
            config = uvicorn.Config(
                "ethifinx.api:app",
                host=self.settings.api_host,
                port=self.settings.api_port,
                reload=self.settings.debug_mode,
                log_level="error",
            )
            server = uvicorn.Server(config)
            server.run()

        self.process = multiprocessing.Process(target=run_server, daemon=True)
        self.process.start()

        # Wait for server to start
        return self._wait_for_server()

    def stop(self) -> None:
        """Stop the API server."""
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=5)
            self.process = None


@contextmanager
def managed_api_server():
    """Context manager for the API server."""
    server = APIServer()
    try:
        server.start()
        yield server
    finally:
        server.stop()
