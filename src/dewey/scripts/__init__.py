# Package initialization for Dewey scripting utilities
from pathlib import Path

# Import scripts
from . import prd_builder

# Export version
__version__ = "0.1.0"

__all__ = [
    "PRDManager",
    "code_consolidator",
    "duplicate_manager",
    "script_mover",
]

# Allow relative imports from other scripts
PACKAGE_ROOT = Path(__file__).parent
