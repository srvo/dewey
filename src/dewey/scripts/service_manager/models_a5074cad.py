from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Container:
    """Container information."""

    name: str
    status: str
    image: str
    health: str | None
    started_at: str


@dataclass
class Service:
    """Service information."""

    name: str
    path: Path
    containers: list[Container]
    config_path: Path
    description: str | None = None
    version: str | None = None
    maintainer: str | None = None
    dependencies: list[str] = field(default_factory=list)
    environment: dict = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    ports: list[str] = field(default_factory=list)
    healthcheck: dict = field(default_factory=dict)
