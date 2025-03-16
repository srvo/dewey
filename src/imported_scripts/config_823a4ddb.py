from pathlib import Path

# Base directory
BASE_DIR = Path("/Users/srvo/ethicic.com")

# Source directories
POST_SOURCE_DIR = BASE_DIR / "content/post"
PAGE_SOURCE_DIR = BASE_DIR / "content/page"

# Target directories
POST_TARGET_DIR = BASE_DIR / "content/posts"  # Hugo's default posts directory
PAGE_TARGET_DIR = BASE_DIR / "content/pages"  # Hugo's default pages directory

# Image processing settings
MAX_IMAGE_WIDTH = 1200
MAX_IMAGE_HEIGHT = 1200
IMAGE_QUALITY = 85

# Supported image formats
SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png"]
