try:
    import os
    from pathlib import Path
    import pandas as pd
    import duckdb
    from datetime import datetime
    import mimetypes
    import hashlib
except ImportError as e:
    print(f"\nError: Missing required package - {str(e)}")
    print("\nPlease install required packages using:")
    print("pip install pandas duckdb python-dotenv mimetypes-magic")
    exit(1)

def scan_media_files(root_dir='/Volumes/back_marx/portcloud/Meeting Recordings'):
    """Scan directory for media files and create inventory"""
    # ... rest of your code ... 