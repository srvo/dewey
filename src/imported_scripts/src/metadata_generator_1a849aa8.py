from datetime import datetime
from pathlib import Path

import yaml


def generate_metadata(source_dir: Path, target_dir: Path) -> None:
    """Generate metadata for the post.

    Args:
        source_dir: Path to source post directory
        target_dir: Path to target post directory

    """
    # Read existing metadata
    source_md = source_dir / "index.md"
    with open(source_md, encoding="utf-8") as f:
        content = f.read()

    # Extract and update metadata
    metadata = extract_metadata(content)
    updated_metadata = update_metadata(metadata, source_dir)

    # Write updated metadata
    write_metadata(updated_metadata, target_dir / "index.md")


def extract_metadata(content: str) -> dict:
    """Extract metadata from markdown content."""
    if content.startswith("---"):
        parts = content.split("---", 2)[1:]
        if len(parts) >= 1:
            try:
                return yaml.safe_load(parts[0])
            except yaml.YAMLError:
                return {}
    return {}


def update_metadata(metadata: dict, source_dir: Path) -> dict:
    """Update metadata with new fields."""
    # Add or update required fields
    metadata.update(
        {
            "date": datetime.strptime(source_dir.name[:10], "%Y-%m-%d"),
            "slug": source_dir.name[11:],
            "type": "post",
        },
    )
    return metadata


def write_metadata(metadata: dict, target_path: Path) -> None:
    """Write metadata to target file."""
    with open(target_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(metadata, f, allow_unicode=True, sort_keys=False)
        f.write("---\n")
