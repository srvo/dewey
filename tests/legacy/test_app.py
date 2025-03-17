
# Refactored from: test_app
# Date: 2025-03-16T16:19:08.687672
# Refactor Version: 1.0
import os

from app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check() -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_supported_formats() -> None:
    """Test supported formats endpoint."""
    response = client.get("/supported-formats")
    assert response.status_code == 200
    data = response.json()
    assert "formats" in data
    assert isinstance(data["formats"], list)
    assert "pdf" in data["formats"]


def test_extract_text() -> None:
    """Test text extraction from a sample document."""
    # Create a sample text file
    sample_text = "This is a test document."
    with open("test.txt", "w") as f:
        f.write(sample_text)

    try:
        # Test file upload and extraction
        with open("test.txt", "rb") as f:
            response = client.post(
                "/extract",
                files={"file": ("test.txt", f, "text/plain")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert data["filename"] == "test.txt"
        assert "elements" in data
        assert len(data["elements"]) > 0
        assert any(sample_text in element["text"] for element in data["elements"])

    finally:
        # Clean up
        if os.path.exists("test.txt"):
            os.remove("test.txt")


def test_extract_invalid_file() -> None:
    """Test handling of invalid file upload."""
    response = client.post(
        "/extract",
        files={"file": ("test.txt", b"invalid binary data", "text/plain")},
    )
    assert response.status_code == 500


def test_environment_variables() -> None:
    """Test environment variable configuration."""
    assert int(os.getenv("PORT", "8000")) == 8000
    assert os.getenv("HOST", "0.0.0.0") == "0.0.0.0"
    assert os.getenv("LOG_LEVEL", "info") == "info"
