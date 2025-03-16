from pathlib import Path

# Base directory
BASE_DIR = Path("/Users/srvo/ethicic.com")

# Source and target directories
SOURCE_DIR = BASE_DIR / "content/post"
TARGET_DIR = BASE_DIR / "content/new-posts"

# Image processing settings
MAX_IMAGE_WIDTH = 1200
MAX_IMAGE_HEIGHT = 1200
IMAGE_QUALITY = 85

# Supported image formats
SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png']
