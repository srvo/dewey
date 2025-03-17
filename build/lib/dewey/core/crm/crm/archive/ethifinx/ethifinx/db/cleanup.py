"""Database cleanup operations module."""

import os
import logging
import time
from datetime import datetime, timedelta
from typing import List, Set, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from .models import ResearchResults, CompanyContext, ResearchIteration


logger = logging.getLogger(__name__)


class DatabaseCleaner:
    """Transactional cleanup operations with safety checks."""
    
    SAFETY_CHECKS = {
        "max_delete_rows": 1000,
        "min_retention_days": 7,
        "lock_timeout": 300  # 5 minutes
    }

    def __init__(self):
        self.temp_file_patterns: Set[str] = {
            ".DS_Store", ".tmp", "~$", ".bak", "Thumbs.db", "desktop.ini"
        }

    def cleanup_temp_files(self, directory: str, days_old: int = 1) -> int:
        """Safe temp file cleanup with lock checking."""
        cleaned = 0
        start_time = time.time()
        
        for root, _, files in os.walk(directory):
            for file in files:
                if self._is_stale_temp_file(os.path.join(root, file), days_old):
                    try:
                        if self._safe_to_delete(file_path):
                            os.remove(file_path)
                            cleaned += 1
                    except Exception as e:
                        logger.warning(f"Cleanup skipped {file}: {str(e)}")
                        
                # Check timeout safety
                if time.time() - start_time > self.SAFETY_CHECKS["lock_timeout"]:
                    logger.error("Cleanup timeout reached, aborting")
                    return cleaned
                    
        return cleaned

    def _is_stale_temp_file(self, path: str, days_old: int) -> bool:
        """Check if file matches patterns and age threshold."""
        if not any(p in path for p in self.temp_file_patterns):
            return False
            
        file_time = datetime.fromtimestamp(os.path.getmtime(path))
        return (datetime.now() - file_time) > timedelta(days=days_old)

    def _safe_to_delete(self, path: str) -> bool:
        """Check file is not in use by another process."""
        try:
            # Attempt exclusive open to check lock status
            with open(path, 'r+') as f:
                return True
        except IOError:
            return False

    def cleanup_duplicate_checkpoints(self, session: Session) -> int:
        """Transactional deduplication with row limits."""
        cleaned = 0
        session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
        
        try:
            companies = session.query(ResearchIteration.company_ticker).distinct().all()
            for (ticker,) in companies:
                # Get IDs of non-latest checkpoints
                to_delete = session.query(ResearchIteration.id).filter(
                    ResearchIteration.company_ticker == ticker
                ).order_by(ResearchIteration.created_at.desc()).offset(1).subquery()

                # Safety check
                delete_count = session.query(ResearchIteration.id).filter(
                    ResearchIteration.id.in_(to_delete)
                ).count()
                
                if delete_count > self.SAFETY_CHECKS["max_delete_rows"]:
                    logger.error(f"Skipping {ticker}: delete count {delete_count} exceeds safety limit")
                    continue

                # Perform deletion
                deleted = session.query(ResearchIteration).filter(
                    ResearchIteration.id.in_(to_delete)
                ).delete(synchronize_session=False)
                
                cleaned += deleted
                session.commit()
                
        except Exception as e:
            session.rollback()
            logger.error(f"Deduplication failed: {str(e)}")
            raise
            
        return cleaned

    # Remaining methods with transaction awareness
