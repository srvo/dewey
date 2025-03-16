import subprocess
import sys


def setup_environment() -> bool:
    """Setup the Python environment with required packages."""
    required_packages = ["pandas", "duckdb", "python-dotenv", "mimetypes-magic"]

    for package in required_packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError:
            return False

    return True


if __name__ == "__main__":
    setup_environment()
