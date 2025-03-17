#!/usr/bin/env python3

import os
import shutil
from pathlib import Path

def create_directory_structure():
    """Create the directory structure for the gdocs_converter package."""
    base_dir = Path("gdocs_converter")
    directories = [
        base_dir,
        base_dir / "gdocs_converter",
        base_dir / "tests",
        base_dir / "config",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").touch()
    
    return base_dir

def create_main_module(base_dir: Path):
    """Create the main module file."""
    content = '''#!/usr/bin/env python3
"""
Google Docs to Markdown Converter

This script converts Google Docs to Markdown format and organizes them in Obsidian.
"""
import os
import io
import shutil
from pathlib import Path
import html2text
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from .auth_handler import GoogleAuthHandler
from .document_processor import DocumentProcessor
from .config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Google Docs to Markdown converter."""
    try:
        # Load configuration
        config = Config()
        
        # Initialize components
        auth_handler = GoogleAuthHandler(config)
        service = auth_handler.authenticate()
        
        doc_processor = DocumentProcessor(service, config)
        
        # Process documents
        logger.info("Starting document processing")
        doc_processor.process_all_documents()
        logger.info("Document processing completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to process documents: {str(e)}")
        raise

if __name__ == "__main__":
    main()
'''
    with open(base_dir / "gdocs_converter" / "gdocs_converter.py", "w") as f:
        f.write(content)

def create_auth_handler(base_dir: Path):
    """Create the authentication handler module."""
    content = '''"""Handle Google Drive authentication."""
import os
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import Any
import logging

logger = logging.getLogger(__name__)

class GoogleAuthHandler:
    """Handle Google Drive authentication and service creation."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config
        self.credentials_path = Path(config.credentials_path)
        self.token_path = Path(config.token_path)
    
    def authenticate(self) -> Any:
        """Authenticate and return the Drive API service."""
        creds = None
        if self.token_path.exists():
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), 
                    self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                
            # Save credentials
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
'''
    with open(base_dir / "gdocs_converter" / "auth_handler.py", "w") as f:
        f.write(content)

def create_document_processor(base_dir: Path):
    """Create the document processor module."""
    content = '''"""Process Google Docs documents."""
import io
import os
import shutil
from pathlib import Path
import html2text
from googleapiclient.http import MediaIoBaseDownload
import logging
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Document:
    """Represent a Google Doc document."""
    id: str
    name: str
    content: str = ""

class DocumentProcessor:
    """Handle Google Doc processing and conversion."""
    
    def __init__(self, service, config):
        """Initialize with Drive service and configuration."""
        self.service = service
        self.config = config
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        
    def list_documents(self) -> List[Document]:
        """List all Google Docs files from Drive."""
        files = []
        page_token = None
        query = "mimeType='application/vnd.google-apps.document'"
        
        while True:
            try:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name)',
                    pageToken=page_token
                ).execute()
                
                files.extend([
                    Document(id=f['id'], name=f['name'])
                    for f in response.get('files', [])
                ])
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                logger.error(f"Failed to list documents: {str(e)}")
                raise
                
        return files
    
    def export_document(self, doc: Document) -> str:
        """Export a Google Doc as HTML and convert to Markdown."""
        try:
            request = self.service.files().export_media(
                fileId=doc.id,
                mimeType='text/html'
            )
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                
            html_content = fh.getvalue().decode('utf-8')
            return self.html_converter.handle(html_content)
            
        except Exception as e:
            logger.error(f"Failed to export document {doc.name}: {str(e)}")
            raise
    
    def save_document(self, doc: Document, content: str):
        """Save document to appropriate directories."""
        try:
            # Save to staging
            staging_path = Path(self.config.staging_dir) / f"{doc.name}.md"
            with open(staging_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            # Move to Obsidian
            dest_path = Path(self.config.obsidian_dir) / f"{doc.name}.md"
            shutil.move(staging_path, dest_path)
            
            logger.info(f"Successfully processed {doc.name}")
            
        except Exception as e:
            logger.error(f"Failed to save document {doc.name}: {str(e)}")
            raise
    
    def process_all_documents(self):
        """Process all Google Docs documents."""
        docs = self.list_documents()
        logger.info(f"Found {len(docs)} documents to process")
        
        for doc in docs:
            try:
                content = self.export_document(doc)
                self.save_document(doc, content)
            except Exception as e:
                logger.error(f"Failed to process {doc.name}: {str(e)}")
                continue
'''
    with open(base_dir / "gdocs_converter" / "document_processor.py", "w") as f:
        f.write(content)

def create_config(base_dir: Path):
    """Create the configuration module."""
    content = '''"""Configuration management."""
import os
from pathlib import Path
from typing import Dict
import yaml

class Config:
    """Manage configuration settings."""
    
    def __init__(self):
        """Initialize configuration."""
        self.base_dir = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents"
        
        # Directories
        self.staging_dir = self.base_dir / "~/staging"
        self.obsidian_dir = self.base_dir / "~/to obsidian"
        
        # Credentials
        self.credentials_path = self.base_dir / "dev/credentials/google_credentials.json"
        self.token_path = Path("token.pickle")
        
        # Ensure directories exist
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.obsidian_dir.mkdir(parents=True, exist_ok=True)
'''
    with open(base_dir / "gdocs_converter" / "config.py", "w") as f:
        f.write(content)

def create_tests(base_dir: Path):
    """Create test files."""
    test_content = '''"""Test the Google Docs converter."""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from gdocs_converter.document_processor import Document, DocumentProcessor
from gdocs_converter.config import Config

@pytest.fixture
def config():
    """Provide test configuration."""
    return Config()

@pytest.fixture
def mock_service():
    """Provide mock Google Drive service."""
    return Mock()

@pytest.fixture
def processor(mock_service, config):
    """Provide document processor with mocks."""
    return DocumentProcessor(mock_service, config)

def test_list_documents(processor, mock_service):
    """Test listing documents."""
    mock_service.files().list().execute.return_value = {
        'files': [
            {'id': '1', 'name': 'Test Doc 1'},
            {'id': '2', 'name': 'Test Doc 2'}
        ]
    }
    
    docs = processor.list_documents()
    assert len(docs) == 2
    assert docs[0].name == 'Test Doc 1'
    assert docs[1].id == '2'

# Add more tests as needed
'''
    with open(base_dir / "tests" / "test_gdocs_converter.py", "w") as f:
        f.write(test_content)

def create_readme(base_dir: Path):
    """Create README.md file."""
    content = '''# Google Docs to Markdown Converter

Convert Google Docs to Markdown format and organize them in Obsidian.

## Features
- Authenticate with Google Drive
- List all Google Docs
- Convert docs to Markdown format
- Organize in Obsidian vault
- Progress tracking and error handling

## Setup
1. Install dependencies:
   ```bash
   poetry install
   ```

2. Configure Google Drive credentials:
   - Place `google_credentials.json` in the appropriate credentials directory
   - Run the script to authenticate and generate token

3. Configure Obsidian directories in `config.py`

## Usage
```bash
poetry run python -m gdocs_converter
```

## Development
- Run tests: `poetry run pytest`
- Format code: `poetry run black .`
- Type checking: `poetry run mypy .`
'''
    with open(base_dir / "README.md", "w") as f:
        f.write(content)

def create_pyproject_toml(base_dir: Path):
    """Create pyproject.toml file."""
    content = '''[tool.poetry]
name = "gdocs_converter"
version = "0.1.0"
description = "Convert Google Docs to Markdown for Obsidian"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
google-auth-oauthlib = "*"
google-api-python-client = "*"
html2text = "*"
pyyaml = "*"

[tool.poetry.dev-dependencies]
pytest = "*"
pytest-cov = "*"
black = "*"
mypy = "*"
flake8 = "*"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
'''
    with open(base_dir / "pyproject.toml", "w") as f:
        f.write(content)

def main():
    """Set up the gdocs_converter project structure."""
    print("Creating gdocs_converter project structure...")
    
    # Create base directory structure
    base_dir = create_directory_structure()
    
    # Create package files
    create_main_module(base_dir)
    create_auth_handler(base_dir)
    create_document_processor(base_dir)
    create_config(base_dir)
    
    # Create tests
    create_tests(base_dir)
    
    # Create project files
    create_readme(base_dir)
    create_pyproject_toml(base_dir)
    
    print(f"""
Project structure created successfully!

Next steps:
1. cd {base_dir}
2. poetry install
3. Configure credentials in config.py
4. Run tests: poetry run pytest
5. Run converter: poetry run python -m gdocs_converter
""")

if __name__ == "__main__":
    main() 