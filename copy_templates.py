#!/usr/bin/env python3
"""
Copy template assets to the site directory during MkDocs build.
"""
import os
import shutil
import sys
from pathlib import Path

def copy_templates():
    """Copy template assets to the site directory."""
    # Get the project root directory (where mkdocs.yml is located)
    root_dir = Path.cwd()
    
    # Source and destination paths
    templates_dir = root_dir / "templates"
    site_dir = root_dir / "site"
    
    # Create site directory if it doesn't exist
    os.makedirs(site_dir, exist_ok=True)
    
    # Copy assets directory
    assets_src = templates_dir / "assets"
    assets_dest = site_dir / "assets"
    
    if assets_src.exists():
        if assets_dest.exists():
            shutil.rmtree(assets_dest)
        shutil.copytree(assets_src, assets_dest)
        print(f"Copied assets from {assets_src} to {assets_dest}")
    
    # Copy partials directory
    partials_src = templates_dir / "partials"
    partials_dest = site_dir / "partials"
    
    if partials_src.exists():
        if partials_dest.exists():
            shutil.rmtree(partials_dest)
        shutil.copytree(partials_src, partials_dest)
        print(f"Copied partials from {partials_src} to {partials_dest}")
    
    return 0

if __name__ == "__main__":
    sys.exit(copy_templates()) 