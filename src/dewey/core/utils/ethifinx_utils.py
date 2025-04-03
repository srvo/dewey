"""Utility functions for Ethifinx research platform."""

import socket
import time
from contextlib import contextmanager
import requests


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def wait_for_server(port: int, timeout: float = 5.0) -> bool:
    """Wait for a server to start on the given port."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(f"http://localhost:{port}/health")
            return True
        except requests.RequestException:
            time.sleep(0.1)
    return False


@contextmanager
def temp_server(port: int, start_cmd: callable, stop_cmd: callable):
    """Context manager for temporary servers."""
    try:
        start_cmd()
        yield
    finally:
        stop_cmd()
