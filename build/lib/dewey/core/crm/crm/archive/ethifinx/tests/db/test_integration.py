"""Integration tests for database operations."""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from ethifinx.db.data_processing import DataProcessor
from ethifinx.db.converters import workflow_to_database
from ethifinx.db.models import ResearchResults, CompanyContext, ResearchIteration
from ethifinx.research.workflows.analysis_tagger import AnalysisTaggingWorkflow


@pytest.fixture
def processor():
    """Data processor instance."""
    return DataProcessor()


@pytest.fixture
def sample_company_data(db_session: Session):
    """Create sample company data in database."""
    research_data = ResearchResults(
        company_ticker="TEST001",
        summary="Test research content",
        source_categories={"Annual Report": 1},
        last_updated_at=datetime.now()
    )
    db_session.add(research_data)
    db_session.commit()
    return research_data


@pytest.fixture
def sample_analysis_data(db_session: Session):
    """Create sample analysis data in database."""
    analysis = ResearchResults(
        company_ticker="TEST001",
        structured_data={
            "concern_level": 3,
            "opportunity_score": 4,
            "key_concerns": ["Test concern"]
        },
        summary="Test summary",
        recommendation="Test recommendation",
        last_updated_at=datetime.now()
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


def test_workflow_database_integration(
    db_session: Session,
    processor: DataProcessor,
    sample_workflow_data,
    mock_engine
):
    """Test workflow integration with database."""
    # Process workflow data
    processed_data = processor.process(sample_workflow_data)
    
    # Convert to database format
    db_format = workflow_to_database(processed_data)
    
    # Create database record
    analysis = ResearchResults(
        company_ticker="TEST001",
        **db_format
    )
    db_session.add(analysis)
    db_session.commit()
    
    # Verify database record
    saved_analysis = db_session.query(ResearchResults).filter_by(
        company_ticker="TEST001"
    ).first()
    
    assert saved_analysis is not None
    assert saved_analysis.structured_data["concern_level"] == processed_data["structured_data"]["concern_level"]
    assert saved_analysis.summary == processed_data["summary"]


def test_research_checkpoint_tracking(
    db_session: Session,
    processor: DataProcessor,
    sample_company_data
):
    """Test research checkpoint creation and tracking."""
    # Create checkpoint
    checkpoint = ResearchIteration(
        company_ticker="TEST001",
        iteration_type="daily_update",
        created_at=datetime.now(),
        confidence_metrics={
            "processed_results": 1,
            "token_metrics": {"total_tokens": 100}
        }
    )
    db_session.add(checkpoint)
    db_session.commit()
    
    # Verify checkpoint
    saved_checkpoint = db_session.query(ResearchIteration).filter_by(
        company_ticker="TEST001"
    ).first()
    
    assert saved_checkpoint is not None
    assert saved_checkpoint.confidence_metrics["processed_results"] == 1
    assert "token_metrics" in saved_checkpoint.confidence_metrics


def test_analysis_update_with_history(
    db_session: Session,
    processor: DataProcessor,
    sample_analysis_data,
    sample_workflow_data
):
    """Test updating analysis with history preservation."""
    # Process new data
    processed_data = processor.process(sample_workflow_data)
    
    # Convert to database format with existing data
    db_format = workflow_to_database(
        processed_data,
        existing_data=sample_analysis_data.__dict__
    )
    
    # Update existing analysis
    for key, value in db_format.items():
        setattr(sample_analysis_data, key, value)
    db_session.commit()
    
    # Verify update and history
    updated_analysis = db_session.query(ResearchResults).filter_by(
        company_ticker="TEST001"
    ).first()
    
    assert updated_analysis is not None
    assert "history" in updated_analysis.structured_data
    assert len(updated_analysis.structured_data["history"]) == 1


def test_concurrent_analysis_updates(
    db_session: Session,
    processor: DataProcessor,
    sample_analysis_data
):
    """Test handling concurrent analysis updates."""
    from concurrent.futures import ThreadPoolExecutor
    import threading
    
    def update_analysis(workflow_data):
        with db_session.begin_nested():
            processed_data = processor.process(workflow_data)
            db_format = workflow_to_database(
                processed_data,
                existing_data=sample_analysis_data.__dict__
            )
            for key, value in db_format.items():
                setattr(sample_analysis_data, key, value)
    
    # Create multiple workflow data updates
    updates = [
        {**sample_workflow_data, "tags": {"concern_level": i}}
        for i in range(3)
    ]
    
    # Run concurrent updates
    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(update_analysis, updates)
    
    # Verify final state
    final_analysis = db_session.query(ResearchResults).filter_by(
        company_ticker="TEST001"
    ).first()
    
    assert final_analysis is not None
    assert "history" in final_analysis.structured_data
    assert len(final_analysis.structured_data["history"]) > 0 