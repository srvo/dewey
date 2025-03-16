# Package initialization for Dewey scripting utilities
from pathlib import Path
from .prd_builder import app as prd_app, PRDManager

__all__ = ["code_consolidator", "duplicate_manager", "script_mover", "prd_app", "PRDManager"]

# Allow relative imports from other scripts
PACKAGE_ROOT = Path(__file__).parent
