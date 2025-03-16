"""Main application file for the FastAPI application."""

import logging
import os
from typing import Any

import uvicorn
from app.api.routers import api_router
from app.config import DATA_DIR
from app.observability import init_observability
from app.settings import init_settings
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

logger = logging.getLogger("uvicorn")

app = FastAPI()


def configure_app(app: FastAPI) -> None:
    """Configures the FastAPI application.

    Args:
    ----
        app: The FastAPI application instance.

    """
    init_settings()
    init_observability()
    configure_cors(app)
    mount_static_files(app)
    app.include_router(api_router, prefix="/api")


def configure_cors(app: FastAPI) -> None:
    """Configures CORS settings for the FastAPI application.

    Args:
    ----
        app: The FastAPI application instance.

    """
    environment = os.getenv("ENVIRONMENT", "dev")
    if environment == "dev":
        logger.warning("Running in development mode - allowing CORS for all origins")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/")
        async def redirect_to_docs() -> Any:
            """Redirects the user to the documentation page."""
            return RedirectResponse(url="/docs")


def mount_static_files(app: FastAPI) -> None:
    """Mounts static file directories to the FastAPI application.

    Args:
    ----
        app: The FastAPI application instance.

    """
    _mount_static_file_directory(app, DATA_DIR, "/api/files/data")
    _mount_static_file_directory(app, "output", "/api/files/output")


def _mount_static_file_directory(app: FastAPI, directory: str, path: str) -> None:
    """Mounts a single static file directory to the FastAPI application.

    Args:
    ----
        app: The FastAPI application instance.
        directory: The directory to mount.
        path: The path to mount the directory at.

    """
    if os.path.exists(directory):
        logger.info(f"Mounting static files '{directory}' at '{path}'")
        app.mount(
            path,
            StaticFiles(directory=directory, check_dir=False),
            name=f"{directory}-static",
        )


configure_app(app)


if __name__ == "__main__":
    app_host = os.getenv("APP_HOST", "0.0.0.0")
    app_port = int(os.getenv("APP_PORT", "8000"))
    environment = os.getenv("ENVIRONMENT", "dev")
    reload = environment == "dev"

    uvicorn.run(app="main:app", host=app_host, port=app_port, reload=reload)
