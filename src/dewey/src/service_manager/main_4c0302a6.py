#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path

from service_manager.service_manager import ServiceManager
from service_manager.ui import ServiceManagerApp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Service Manager")
    parser.add_argument(
        "--remote",
        required=True,
        help="Remote host to connect to (e.g., user@host)",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Path to workspace directory (default: current directory)",
    )

    args = parser.parse_args()

    # Create service manager instance
    service_manager = ServiceManager(args.remote, args.workspace)

    # Create and run Textual UI app
    app = ServiceManagerApp(service_manager)
    app.run()


if __name__ == "__main__":
    main()
