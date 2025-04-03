#!/usr/bin/env python3

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

from src.dewey.core.crm.gmail.unified_email_processor import main

if __name__ == "__main__":
    main() 