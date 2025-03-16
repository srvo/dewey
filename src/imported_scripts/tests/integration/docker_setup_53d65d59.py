from __future__ import annotations

import os
import time

import psycopg2
import pytest
import redis
import requests


def get_service_url(service, port) -> str:
    """Get service URL from Docker environment."""
    host = os.getenv(f"{service.upper()}_HOST", "localhost")
    return f"http://{host}:{port}"


@pytest.fixture(scope="session")
def wait_for_services() -> bool | None:
    """Wait for all services to be ready."""
    retries = 30
    for _ in range(retries):
        try:
            # Check web service
            response = requests.get(get_service_url("web", 8000))
            if response.status_code == 200:
                # Check database
                conn = psycopg2.connect(
                    dbname="email_processing",
                    user="app_user",
                    password=os.getenv("DB_PASSWORD"),
                    host=os.getenv("DB_HOST", "localhost"),
                    port=5432,
                )
                conn.close()

                # Check Redis
                r = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=6379,
                    db=0,
                )
                r.ping()

                return True
        except Exception:
            time.sleep(1)
    pytest.fail("Services did not become ready in time")


@pytest.mark.integration
class TestDockerSetup:
    def test_nginx_static_files(self, wait_for_services) -> None:
        """Test that Nginx is serving static files correctly."""
        response = requests.get(f"{get_service_url('nginx', 80)}/static/css/main.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["Content-Type"]
        assert "public" in response.headers["Cache-Control"]

    def test_web_service_health(self, wait_for_services) -> None:
        """Test that the web service is healthy and responding."""
        response = requests.get(f"{get_service_url('web', 8000)}/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_database_connection(self, wait_for_services) -> None:
        """Test database connectivity and basic operations."""
        conn = psycopg2.connect(
            dbname="email_processing",
            user="app_user",
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "localhost"),
            port=5432,
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        assert result[0] == 1
        cur.close()
        conn.close()

    def test_redis_connection(self, wait_for_services) -> None:
        """Test Redis connectivity and basic operations."""
        r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0)
        r.set("test_key", "test_value")
        assert r.get("test_key") == b"test_value"
        r.delete("test_key")

    def test_nginx_proxy_headers(self, wait_for_services) -> None:
        """Test that Nginx is properly setting proxy headers."""
        response = requests.get(
            f"{get_service_url('nginx', 80)}/",
            headers={"Host": "test.com"},
        )
        assert response.status_code == 200
        # The actual headers will be processed by the web service
        # We're testing the connection works through the proxy

    def test_container_health_checks(self, wait_for_services) -> None:
        """Test that health checks are working for all services."""
        import docker

        client = docker.from_env()

        services = ["db", "redis", "web", "nginx"]
        for service in services:
            containers = client.containers.list(
                filters={"name": f"srvo_utils_{service}"},
            )
            assert len(containers) > 0
            container = containers[0]
            assert container.status == "running"

            # For services with health checks
            if service in ["db", "redis"]:
                assert container.attrs["State"]["Health"]["Status"] == "healthy"
