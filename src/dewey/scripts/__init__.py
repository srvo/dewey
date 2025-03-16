# Package initialization for Dewey scripting utilities
from pathlib import Path

from .prd_builder import PRDManager
from .prd_builder import app as prd_app

__all__ = [
    "PRDManager",
    "code_consolidator",
    "duplicate_manager",
    "prd_app",
    "script_mover",
]

# Allow relative imports from other scripts
PACKAGE_ROOT = Path(__file__).parent
