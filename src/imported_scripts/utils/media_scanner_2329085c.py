import hashlib
import mimetypes
import os
from datetime import datetime
from pathlib import Path

import pandas as pd


def scan_media_files(root_dir="/Volumes/back_marx/portcloud/Meeting Recordings"):
    """Scan directory for media files and create inventory."""
    # Common media extensions
    MEDIA_EXTENSIONS = {
        "audio": [".mp3", ".wav", ".m4a", ".aac", ".wma", ".ogg", ".flac"],
        "video": [".mp4", ".mov", ".avi", ".wmv", ".flv", ".mkv", ".webm"],
        "text": [".txt", ".srt", ".vtt", ".doc", ".docx", ".pdf"],
        "other": [".json", ".csv", ".xml"],
    }

    files_data = []

    try:

        # Walk through directory
        for dirpath, _dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                file_path = Path(dirpath) / filename

                # Skip hidden files
                if filename.startswith("."):
                    continue

                # Get file info
                extension = file_path.suffix.lower()

                # Determine file type
                file_type = "unknown"
                for type_name, extensions in MEDIA_EXTENSIONS.items():
                    if extension in extensions:
                        file_type = type_name
                        break

                # Get file stats
                stats = file_path.stat()

                # Calculate file hash for uniqueness check
                try:
                    with open(file_path, "rb") as f:
                        file_hash = hashlib.md5(
                            f.read(8192),
                        ).hexdigest()  # Hash first 8KB only
                except Exception:
                    file_hash = None

                # Get mime type
                mime_type, _ = mimetypes.guess_type(file_path)

                files_data.append(
                    {
                        "filename": filename,
                        "path": str(file_path),
                        "type": file_type,
                        "extension": extension,
                        "mime_type": mime_type,
                        "size_bytes": stats.st_size,
                        "size_mb": round(stats.st_size / (1024 * 1024), 2),
                        "created": datetime.fromtimestamp(stats.st_ctime),
                        "modified": datetime.fromtimestamp(stats.st_mtime),
                        "hash": file_hash,
                        "relative_path": str(file_path.relative_to(root_dir)),
                    },
                )

        # Convert to DataFrame
        df = pd.DataFrame(files_data)

        # Print summary

        # Save to CSV
        output_file = "media_inventory.csv"
        df.to_csv(output_file, index=False)

        # Create DuckDB table
        con = duckdb.connect("media_inventory.duckdb")

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS media_files (
                filename VARCHAR,
                path VARCHAR,
                type VARCHAR,
                extension VARCHAR,
                mime_type VARCHAR,
                size_bytes BIGINT,
                size_mb DOUBLE,
                created TIMESTAMP,
                modified TIMESTAMP,
                hash VARCHAR,
                relative_path VARCHAR,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Insert data
        con.execute("DELETE FROM media_files")
        con.execute("INSERT INTO media_files SELECT *, CURRENT_TIMESTAMP FROM df")

        # Show sample of files found
        con.execute(
            """
            SELECT
                filename,
                type,
                size_mb,
                modified
            FROM media_files
            ORDER BY modified DESC
            LIMIT 5
        """,
        ).fetchdf()

        con.close()

        return df

    except Exception:
        return pd.DataFrame()


if __name__ == "__main__":
    df = scan_media_files()
