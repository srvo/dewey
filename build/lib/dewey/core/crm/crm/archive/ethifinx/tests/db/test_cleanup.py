"""Tests for database cleanup operations."""

import pytest
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ethifinx.db.models import ResearchResults, CompanyContext, ResearchIteration
from ethifinx.db.cleanup import DatabaseCleaner


@pytest.fixture
def db_cleaner():
    """Database cleaner instance."""
    return DatabaseCleaner()


@pytest.fixture
def incomplete_analysis(db_session: Session):
    """Create incomplete analysis data for testing."""
    analysis = ResearchResults(
        company_ticker="INCOMPLETE_TEST",
        structured_data={},
        summary="",
        recommendation="Test recommendation",
        last_updated_at=datetime.now()
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


@pytest.fixture
def stale_checkpoint(db_session: Session):
    """Create stale checkpoint data."""
    old_date = datetime.now() - timedelta(days=7)
    checkpoint = ResearchIteration(
        company_ticker="STALE_TEST",
        iteration_type="daily_update",
        created_at=old_date,
        confidence_metrics={
            "processed_results": 0,
            "token_metrics": {"total_tokens": 0}
        }
    )
    db_session.add(checkpoint)
    db_session.commit()
    return checkpoint


def test_log_incomplete_analyses(
    db_session: Session,
    db_cleaner,
    incomplete_analysis,
    caplog
):
    """Test logging of incomplete analyses."""
    caplog.set_level(logging.WARNING)
    
    # Run incomplete analysis check
    results = db_cleaner.log_incomplete_analyses(db_session)
    
    # Verify results structure
    assert results["total_incomplete"] == 1
    assert len(results["details"]) == 1
    assert results["details"][0]["company_id"] == "INCOMPLETE_TEST"
    assert len(results["details"][0]["missing_fields"]) == 2
    assert "structured_data" in results["details"][0]["missing_fields"]
    assert "summary" in results["details"][0]["missing_fields"]
    
    # Verify logging
    assert "Incomplete analysis found for company INCOMPLETE_TEST" in caplog.text
    assert "Missing fields: structured_data, summary" in caplog.text
    
    # Verify analysis still exists
    analysis = db_session.query(ResearchResults).filter_by(
        company_ticker="INCOMPLETE_TEST"
    ).first()
    assert analysis is not None


def test_cleanup_temp_files(caplog):
    """Test cleanup of temporary files."""
    caplog.set_level(logging.INFO)
    
    # Create temp test files
    temp_dir = "ethifinx/data/temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    test_files = [
        "test_old.tmp",
        "test_recent.tmp",
        ".DS_Store",  # Common temp file
        "Thumbs.db"   # Common temp file
    ]
    
    old_date = datetime.now() - timedelta(days=2)
    for file in test_files:
        path = os.path.join(temp_dir, file)
        with open(path, "w") as f:
            f.write("test")
        
        # Make first file appear old
        if file == "test_old.tmp":
            os.utime(path, (old_date.timestamp(), old_date.timestamp()))
    
    # Run cleanup
    db_cleaner = DatabaseCleaner()
    cleaned = db_cleaner.cleanup_temp_files(temp_dir, days_old=1)
    
    # Verify old and system temp files were removed
    assert not os.path.exists(os.path.join(temp_dir, "test_old.tmp"))
    assert not os.path.exists(os.path.join(temp_dir, ".DS_Store"))
    assert not os.path.exists(os.path.join(temp_dir, "Thumbs.db"))
    
    # Verify recent file remains
    assert os.path.exists(os.path.join(temp_dir, "test_recent.tmp"))
    
    # Verify cleanup count
    assert cleaned == 3
    
    # Verify logging
    assert "Removed temporary file:" in caplog.text
    assert ".DS_Store" in caplog.text
    assert "Thumbs.db" in caplog.text
    
    # Cleanup test directory
    os.remove(os.path.join(temp_dir, "test_recent.tmp"))
    os.rmdir(temp_dir)


def test_cleanup_duplicate_checkpoints(
    db_session: Session,
    db_cleaner,
    caplog
):
    """Test cleanup of duplicate checkpoints."""
    caplog.set_level(logging.INFO)
    
    # Create duplicate checkpoints
    checkpoints = []
    for i in range(3):
        checkpoint = ResearchIteration(
            company_ticker="DUP_TEST",
            iteration_type="daily_update",
            created_at=datetime.now() - timedelta(minutes=i),
            confidence_metrics={
                "processed_results": i,
                "token_metrics": {"total_tokens": i * 100}
            }
        )
        checkpoints.append(checkpoint)
        db_session.add(checkpoint)
    db_session.commit()
    
    # Run cleanup (keep most recent)
    cleaned = db_cleaner.cleanup_duplicate_checkpoints(db_session)
    
    # Verify only one checkpoint remains
    remaining = db_session.query(ResearchIteration).filter_by(
        company_ticker="DUP_TEST"
    ).all()
    assert len(remaining) == 1
    assert remaining[0].confidence_metrics["processed_results"] == 0  # Most recent
    
    # Verify cleanup count
    assert cleaned == 2
    
    # Verify logging
    assert "Found 3 checkpoints for company DUP_TEST" in caplog.text
    assert "keeping most recent from" in caplog.text


def test_run_maintenance(
    db_session: Session,
    db_cleaner,
    incomplete_analysis,
    caplog
):
    """Test running all maintenance operations."""
    caplog.set_level(logging.INFO)
    
    # Create temp directory and files
    temp_dir = "ethifinx/data/temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, "test.tmp")
    with open(temp_file, "w") as f:
        f.write("test")
    
    # Run maintenance
    results = db_cleaner.run_maintenance(
        db_session,
        temp_dir,
        temp_days=1
    )
    
    # Verify results
    assert "incomplete_analyses" in results
    assert results["incomplete_analyses"]["total_incomplete"] == 1
    assert results["temp_files"] == 1
    assert results["duplicate_checkpoints"] == 0
    
    # Verify logging
    assert "Starting maintenance operations" in caplog.text
    assert "Maintenance completed" in caplog.text
    assert "1 incomplete analyses logged" in caplog.text
    
    # Cleanup
    os.rmdir(temp_dir) 