from __future__ import annotations

from typing import TYPE_CHECKING

from .image_handler import process_images

if TYPE_CHECKING:
    from pathlib import Path


def validate_directory_structure(source_dir: Path) -> bool:
    """Validate directory structure. Accepts either:
    1. Directory with index.md and images/
    2. Directory with just index.md.
    """
    # Check if index.md exists
    if not (source_dir / "index.md").exists():
        return False

    # If images directory exists, it must be a directory
    images_dir = source_dir / "images"
    return not (images_dir.exists() and not images_dir.is_dir())


def process_post(source_dir: Path, target_dir: Path) -> Exception | None:
    """Process a single content directory."""
    try:
        # 1. Read and validate source
        if not validate_directory_structure(source_dir):
            msg = f"Invalid directory structure in {source_dir}"
            raise ValueError(msg)

        # 2. Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # 3. Process images if they exist
        source_images = source_dir / "images"
        if source_images.exists() and source_images.is_dir():
            process_images(source_images, target_dir)

        # 4. Update markdown content
        source_md = source_dir / "index.md"
        target_md = target_dir / "index.md"

        with open(source_md, encoding="utf-8") as f:
            content = f.read()

        # Split content into frontmatter and body
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2]

            # Clean up any extra frontmatter markers in the body
            body = body.replace("---\n", "").strip()
        else:
            frontmatter = content
            body = ""

        # Write updated content
        with open(target_md, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(frontmatter.strip())
            f.write("\n---\n")
            f.write(body)
            f.write("\n")

        return None
    except Exception as e:
        return e
