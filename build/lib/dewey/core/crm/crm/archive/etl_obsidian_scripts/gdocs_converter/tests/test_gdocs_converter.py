"""Test the Google Docs converter."""
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
