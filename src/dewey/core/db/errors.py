"""Database error handling module.

This module provides centralized error handling for database operations.
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base exception for database errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()

class ConnectionError(DatabaseError):
    """Connection-related errors."""
    pass

class SyncError(DatabaseError):
    """Synchronization-related errors."""
    pass

class SchemaError(DatabaseError):
    """Schema-related errors."""
    pass

class BackupError(DatabaseError):
    """Backup-related errors."""
    pass

def handle_error(error: Exception, context: Dict[str, Any]) -> str:
    """Handle and log an error with context.
    
    Args:
        error: The exception that occurred
        context: Dictionary containing error context
        
    Returns:
        Unique error ID for tracking
    """
    error_id = str(uuid.uuid4())
    
    error_details = {
        'error_id': error_id,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.now().isoformat(),
        'context': context
    }
    
    if isinstance(error, DatabaseError):
        error_details.update(error.details)
        
    logger.error(f"Database error: {error_id}", 
                exc_info=error,
                extra=error_details)
                
    return error_id

def log_operation(operation: str, details: Dict[str, Any]):
    """Log a database operation.
    
    Args:
        operation: Name of the operation
        details: Operation details
    """
    logger.info(f"Database operation: {operation}",
                extra={'operation': operation, 'details': details}) 