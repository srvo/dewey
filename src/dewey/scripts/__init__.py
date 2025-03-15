# Package initialization for Dewey scripting utilities
from pathlib import Path

__all__ = [
    'code_consolidator',
    'duplicate_manager',
    'script_mover'
]

# Allow relative imports from other scripts
PACKAGE_ROOT = Path(__file__).parent
