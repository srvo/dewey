#!/usr/bin/env python3
"""Manage and maintain links to API documentation used in the repository."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

API_DOCS_FILE = Path("api_documentation.json")

def load_docs() -> Dict[str, str]:
    """Load API documentation links from JSON file."""
    try:
        data = json.loads(API_DOCS_FILE.read_text())
        # Handle both formats - old flat and new structured
        # Handle either structured format or legacy flat format
        return data.get("links", data)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_docs(api_links: Dict[str, str]) -> None:
    """Save API documentation links to JSON file with timestamps."""
    api_links_with_metadata = {
        "last_updated": datetime.utcnow().isoformat(),
        "links": api_links
    }
    API_DOCS_FILE.write_text(json.dumps(api_links_with_metadata, indent=2))

def add_api_doc(api_name: str, doc_url: str) -> str:
    """Add or update an API documentation link.
    
    Args:
        api_name: Official name of the API/service
        doc_url: Full URL to the API documentation
        
    Returns:
        Operation result message
        
    Raises:
        ValueError: If doc_url is not a valid URL
    """
    from urllib.parse import urlparse
    if not urlparse(doc_url).scheme:
        raise ValueError(f"Invalid URL '{doc_url}'")
    api_links = load_docs()
    existed = api_name in api_links
    api_links[api_name] = doc_url
    save_docs(api_links)
    return f"Updated '{api_name}' documentation" if existed else f"Added '{api_name}' documentation"

def remove_api_doc(api_name: str) -> str:
    """Remove an API documentation link.
    
    Args:
        api_name: Name of the API to remove
        
    Returns:
        Operation result message
    """
    api_links = load_docs()
    try:
        del api_links[api_name]
        save_docs(api_links)
        return f"Removed '{api_name}' documentation"
    except KeyError:
        return f"API '{api_name}' not found"

def list_api_docs() -> Dict[str, str]:
    """List all registered API documentation links."""
    return load_docs()

def main() -> None:
    """Command line interface for managing API documentation links."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage API documentation links")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add command
    add_parser = subparsers.add_parser("add", help="Add/update an API documentation link")
    add_parser.add_argument("name", 
        help="Official API/service name (use quotes if contains spaces)")
    add_parser.add_argument("url", 
        help="Full documentation URL (wrap in quotes if contains special characters)")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove an API documentation link")
    remove_parser.add_argument("name", help="API/service name to remove")

    # List command
    subparsers.add_parser("list", help="List all documentation links")

    args = parser.parse_args()
    
    if args.command == "add":
        print(add_api_doc(args.name, args.url))
    elif args.command == "remove":
        print(remove_api_doc(args.name))
    elif args.command == "list":
        docs = list_api_docs()
        for name, url in docs.items():
            print(f"{name}: {url}")

if __name__ == "__main__":
    main()
