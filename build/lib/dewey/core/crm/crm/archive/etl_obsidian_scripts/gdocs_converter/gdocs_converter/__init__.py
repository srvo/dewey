"""Google Docs to Markdown converter package."""

from .auth_handler import GoogleAuthHandler
from .document_processor import DocumentProcessor, Document
from .config import Config
from .log_handler import LogflareHandler
from .core import main

__version__ = "0.1.0"
__all__ = [
    'GoogleAuthHandler',
    'DocumentProcessor',
    'Document',
    'Config',
    'LogflareHandler',
    'main'
] 