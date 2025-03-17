"""
Custom logging handler for Logflare integration.
"""
import json
import logging
import requests
from datetime import datetime

class LogflareHandler(logging.Handler):
    """A custom logging handler that sends logs to Logflare."""
    
    def __init__(self, source_id, api_key):
        """Initialize the handler with Logflare credentials."""
        super().__init__()
        self.source_id = source_id
        self.api_key = api_key
        self.endpoint = "https://api.logflare.app/logs"
        
    def format_record(self, record):
        """Format the log record into Logflare's expected structure."""
        # Get the message and any extra fields
        message = self.format(record) if self.formatter else record.getMessage()
        extra = record.__dict__.get('extra', {})
        
        # Build the metadata
        metadata = {
            "level": record.levelname,
            "logger_name": record.name,
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "process_id": record.process,
            "thread_id": record.thread,
            "file": record.filename,
            "line_number": record.lineno,
            "function": record.funcName,
            **extra  # Include any extra fields passed in the log
        }
        
        if record.exc_info:
            metadata['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
            
        return {
            "message": message,
            "metadata": metadata
        }
        
    def emit(self, record):
        """Send the log record to Logflare."""
        try:
            # Format the record
            log_entry = self.format_record(record)
            
            # Prepare the request
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": self.api_key
            }
            
            payload = {
                "source": self.source_id,
                "log_entry": log_entry
            }
            
            # Send to Logflare
            response = requests.post(
                self.endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=5  # 5 second timeout
            )
            
            # Raise for bad responses
            response.raise_for_status()
            
        except Exception as e:
            # Never raise exceptions in a logging handler
            # Instead, we'll use sys.stderr to report the error
            import sys
            print(f"Error sending log to Logflare: {str(e)}", file=sys.stderr) 