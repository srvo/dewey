import logging
from pathlib import Path

from config import PAGE_SOURCE_DIR, PAGE_TARGET_DIR, POST_SOURCE_DIR, POST_TARGET_DIR
from src.processor import process_post

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_directory(source_dir: Path, target_dir: Path, content_type: str) -> None:
    """Process all content in a directory."""
    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Process nested year/month structure
    for year_dir in source_dir.iterdir():
        if not year_dir.is_dir():
            continue

        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir():
                continue

            for content_dir in month_dir.iterdir():
                if not content_dir.is_dir():
                    continue

                logger.info(f"Processing {content_type}: {content_dir.name}")
                target_content_dir = target_dir / content_dir.name
                error = process_post(content_dir, target_content_dir)
                if error:
                    logger.error(f"Error processing {content_dir.name}: {error}")


def main() -> None:
    """Main conversion script."""
    # Process posts
    logger.info("Processing posts...")
    process_directory(POST_SOURCE_DIR, POST_TARGET_DIR, "post")

    # Process pages
    logger.info("Processing pages...")
    process_directory(PAGE_SOURCE_DIR, PAGE_TARGET_DIR, "page")


if __name__ == "__main__":
    main()
