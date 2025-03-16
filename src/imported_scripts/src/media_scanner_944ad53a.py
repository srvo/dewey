import sys

try:
    import hashlib
    import mimetypes
    import os
    from datetime import datetime
    from pathlib import Path

    import duckdb
    import pandas as pd
except ImportError:
    sys.exit(1)


def scan_media_files(
    root_dir="/Volumes/back_marx/portcloud/Meeting Recordings",
) -> None:
    """Scan directory for media files and create inventory."""
    # ... rest of your code ...
