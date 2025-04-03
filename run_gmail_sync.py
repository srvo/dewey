#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add the project root to Python path
repo_root = Path(__file__).parent
sys.path.append(str(repo_root))

# Now import and run the main function
from src.dewey.core.crm.gmail.run_gmail_sync import main

if __name__ == "__main__":
    sys.exit(main()) 