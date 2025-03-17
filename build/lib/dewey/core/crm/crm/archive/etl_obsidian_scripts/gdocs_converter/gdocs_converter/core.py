"""
Core functionality for the Google Docs to Markdown converter.
"""
import logging
import sys
from .config import Config
from .auth_handler import GoogleAuthHandler
from .document_processor import DocumentProcessor
from .log_handler import LogflareHandler

# Logflare configuration
LOGFLARE_SOURCE_ID = "59ffe249-8b9a-43f0-bc1d-3f83b7228eaf"
LOGFLARE_API_KEY = "Mxl4W0Ll_En-"

def setup_logging():
    """Set up logging with both console and Logflare handlers."""
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Logflare handler
    logflare_handler = LogflareHandler(LOGFLARE_SOURCE_ID, LOGFLARE_API_KEY)
    logflare_handler.setLevel(logging.INFO)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    root_logger.handlers = []
    
    # Add our handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(logflare_handler)
    
    # Test logging
    root_logger.info("Logging system initialized", extra={
        "component": "main",
        "action": "logging_setup"
    })

def main():
    """Main entry point for the Google Docs to Markdown converter."""
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("Starting Google Docs to Markdown converter", extra={
            "component": "main",
            "action": "startup"
        })
        
        # Load configuration
        logger.info("Loading configuration", extra={
            "component": "main",
            "action": "config_load"
        })
        cfg = Config()
        
        # Validate configuration
        logger.info("Validating configuration", extra={
            "component": "main",
            "action": "config_validate"
        })
        cfg.validate()
        
        # Initialize components
        logger.info("Authenticating with Google Drive", extra={
            "component": "auth",
            "action": "authenticate"
        })
        auth = GoogleAuthHandler(cfg)
        service = auth.authenticate()
        
        logger.info("Initializing document processor", extra={
            "component": "processor",
            "action": "initialize"
        })
        doc_processor = DocumentProcessor(service, cfg)
        
        # Process documents
        logger.info("Starting document processing", extra={
            "component": "processor",
            "action": "start_processing"
        })
        doc_processor.process_all_documents()
        logger.info("Document processing completed successfully", extra={
            "component": "processor",
            "action": "complete"
        })
        
    except Exception as e:
        logger.error(f"Failed to process documents: {str(e)}", extra={
            "component": "main",
            "action": "error",
            "error_type": type(e).__name__,
            "error_details": str(e)
        })
        raise 