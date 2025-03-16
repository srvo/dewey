import re
from pathlib import Path


def update_markdown_links(source_path: Path, target_path: Path) -> None:
    """Update markdown content with new image links and any other necessary changes.

    Args:
    ----
        source_path: Path to source markdown file
        target_path: Path to target markdown file

    """
    with open(source_path, encoding="utf-8") as f:
        content = f.read()

    # Split content into frontmatter and body
    parts = content.split("---", 2)
    if len(parts) >= 3:
        frontmatter = parts[1]
        body = parts[2]
    else:
        frontmatter = ""
        body = content

    # Update image links in body
    body = update_image_links(body)

    # Write updated content
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(frontmatter.strip())
        f.write("\n---\n")
        f.write(body.strip())


def update_image_links(content: str) -> str:
    """Update image links in markdown content."""
    # Update markdown image links
    return re.sub(
        r"!\[(.*?)\]\((.*?)\)",
        lambda m: update_image_link(m.group(1), m.group(2)),
        content,
    )


def update_image_link(alt_text: str, image_path: str) -> str:
    """Update a single image link."""
    # Extract image name and update path
    image_name = Path(image_path).name
    return f"![{alt_text}](/images/{image_name})"
