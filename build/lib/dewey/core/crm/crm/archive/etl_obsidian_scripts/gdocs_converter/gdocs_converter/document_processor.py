"""
Process Google Docs documents and convert them to Markdown.
"""
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

@dataclass
class Document:
    """Represents a Google Doc document."""
    id: str
    name: str
    mime_type: str

class DocumentProcessor:
    """Handles the processing of Google Docs documents."""

    def __init__(self, service, config):
        """Initialize the document processor."""
        self.service = service
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.logger.info("Document processor initialized", extra={
            "component": "processor",
            "action": "initialize",
            "config": {
                "output_dir": config.output_dir,
                "credentials_path": config.credentials_path
            }
        })

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for all filesystems."""
        # Replace problematic characters with underscores
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove any leading/trailing periods or spaces
        safe_name = safe_name.strip('. ')
        # Ensure the filename isn't empty
        if not safe_name:
            safe_name = 'unnamed_document'
        return safe_name

    def list_documents(self) -> List[Document]:
        """List all Google Docs documents in the Drive."""
        try:
            self.logger.info("Listing Google Docs documents", extra={
                "component": "processor",
                "action": "list_documents"
            })
            
            documents = []
            page_token = None
            
            while True:
                # Get a page of documents
                results = self.service.files().list(
                    q="mimeType='application/vnd.google-apps.document'",
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                    pageSize=1000  # Maximum allowed by the API
                ).execute()
                
                # Add documents from this page
                documents.extend([
                    Document(
                        id=item['id'],
                        name=item['name'],
                        mime_type=item['mimeType']
                    )
                    for item in results.get('files', [])
                ])
                
                # Get the next page token
                page_token = results.get('nextPageToken')
                
                # If no more pages, break
                if not page_token:
                    break
            
            self.logger.info(
                f"Found {len(documents)} documents",
                extra={
                    "component": "processor",
                    "action": "list_documents",
                    "document_count": len(documents)
                }
            )
            return documents
            
        except Exception as e:
            self.logger.error(
                f"Failed to list documents: {str(e)}",
                extra={
                    "component": "processor",
                    "action": "list_documents",
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                }
            )
            raise

    def export_document(self, doc: Document) -> Optional[str]:
        """Export a Google Doc to plain text."""
        try:
            self.logger.info(
                f"Exporting document: {doc.name}",
                extra={
                    "component": "processor",
                    "action": "export_document",
                    "document_id": doc.id,
                    "document_name": doc.name
                }
            )
            
            try:
                result = self.service.files().export(
                    fileId=doc.id,
                    mimeType='text/plain'
                ).execute()
            except Exception as export_error:
                if 'cannotExportFile' in str(export_error):
                    self.logger.warning(
                        f"Document {doc.name} cannot be exported due to permissions",
                        extra={
                            "component": "processor",
                            "action": "export_document",
                            "status": "skipped",
                            "document_id": doc.id,
                            "document_name": doc.name,
                            "reason": "permissions"
                        }
                    )
                    return None
                raise
            
            if result:
                self.logger.info(
                    f"Successfully exported document: {doc.name}",
                    extra={
                        "component": "processor",
                        "action": "export_document",
                        "status": "success",
                        "document_id": doc.id,
                        "document_name": doc.name,
                        "content_length": len(result)
                    }
                )
                return result.decode('utf-8')
            return None
            
        except Exception as e:
            self.logger.error(
                f"Failed to export document {doc.name}: {str(e)}",
                extra={
                    "component": "processor",
                    "action": "export_document",
                    "status": "error",
                    "document_id": doc.id,
                    "document_name": doc.name,
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                }
            )
            return None

    def save_document(self, doc: Document, content: str) -> bool:
        """Save the document content to a file."""
        try:
            # Create sanitized filename
            safe_name = self.sanitize_filename(doc.name)
            filename = f"{safe_name}.md"
            
            # Create output path using pathlib for better path handling
            output_path = Path(self.config.output_dir)
            filepath = output_path / filename
            
            self.logger.info(
                f"Saving document: {doc.name}",
                extra={
                    "component": "processor",
                    "action": "save_document",
                    "document_id": doc.id,
                    "document_name": doc.name,
                    "output_path": str(filepath)
                }
            )
            
            # Ensure output directory exists
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            filepath.write_text(content, encoding='utf-8')
            
            self.logger.info(
                f"Successfully saved document: {doc.name}",
                extra={
                    "component": "processor",
                    "action": "save_document",
                    "status": "success",
                    "document_id": doc.id,
                    "document_name": doc.name,
                    "output_path": str(filepath),
                    "content_length": len(content)
                }
            )
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to save document {doc.name}: {str(e)}",
                extra={
                    "component": "processor",
                    "action": "save_document",
                    "status": "error",
                    "document_id": doc.id,
                    "document_name": doc.name,
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                }
            )
            return False

    def process_all_documents(self):
        """Process all Google Docs documents."""
        try:
            self.logger.info(
                "Starting batch document processing",
                extra={
                    "component": "processor",
                    "action": "process_all",
                    "status": "starting"
                }
            )
            
            # List all documents
            documents = self.list_documents()
            
            # Process each document
            successful = 0
            failed = 0
            skipped = 0
            
            for doc in documents:
                try:
                    content = self.export_document(doc)
                    if content is None:
                        skipped += 1
                        continue
                        
                    if self.save_document(doc, content):
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    self.logger.error(
                        f"Failed to process document {doc.name}: {str(e)}",
                        extra={
                            "component": "processor",
                            "action": "process_document",
                            "status": "error",
                            "document_id": doc.id,
                            "document_name": doc.name,
                            "error_type": type(e).__name__,
                            "error_details": str(e)
                        }
                    )
                    failed += 1
            
            self.logger.info(
                "Completed batch document processing",
                extra={
                    "component": "processor",
                    "action": "process_all",
                    "status": "complete",
                    "stats": {
                        "total": len(documents),
                        "successful": successful,
                        "failed": failed,
                        "skipped": skipped
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to process documents batch",
                extra={
                    "component": "processor",
                    "action": "process_all",
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                }
            )
            raise 