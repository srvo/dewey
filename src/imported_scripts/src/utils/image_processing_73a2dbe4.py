import shutil
from pathlib import Path

from PIL import Image


def get_image_sizes() -> list[tuple[str, tuple[int, int]]]:
    """Returns list of required image sizes."""
    return [
        ("original", None),  # Keep original size
        ("large", (1200, 1200)),
        ("medium", (800, 800)),
        ("small", (400, 400)),
    ]


def process_images(source_dir: Path, target_dir: Path) -> None:
    """Process images from source directory to target directory.

    Args:
        source_dir: Path to source images directory
        target_dir: Path to target images directory

    """
    target_dir.mkdir(parents=True, exist_ok=True)

    for img_path in source_dir.glob("*"):
        if img_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
            continue

        # Determine if this is a cover image
        is_cover = any(
            keyword in img_path.stem.lower() for keyword in ["cover", "title", "header"]
        )

        # Process image
        process_single_image(img_path, target_dir, is_cover)


def process_single_image(source_path: Path, target_dir: Path, is_cover: bool) -> None:
    """Process a single image file."""
    try:
        # Try to open the image
        try:
            img = Image.open(source_path)
        except Exception:
            # Copy the original file as fallback
            shutil.copy2(source_path, target_dir / source_path.name)
            return

        # Always process all sizes
        sizes = get_image_sizes()

        for size_name, dimensions in sizes:
            try:
                if size_name == "original":
                    # Just copy the original file
                    output_path = target_dir / source_path.name
                    shutil.copy2(source_path, output_path)
                else:
                    output_path = (
                        target_dir
                        / f"{source_path.stem}-{size_name}{source_path.suffix}"
                    )
                    resized_img = img.copy()
                    if dimensions:
                        resized_img.thumbnail(dimensions)
                    resized_img.save(output_path, optimize=True)
            except Exception:
                pass

    except Exception:
        pass
