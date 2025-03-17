from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    BigInteger,
    Boolean,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Research(Base):
    __tablename__ = "research"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False)
    status = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    retries = Column(Integer, default=0)
    data = Column(Text)
    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
    )
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class TestTable(Base):
    __tablename__ = "test_table"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)


class CompanyContext(Base):
    __tablename__ = "company_context"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, unique=True)
    context = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class Universe(Base):
    __tablename__ = "universe"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=False, unique=True)
    isin = Column(String)  # International Securities Identification Number
    security_type = Column(
        String
    )  # e.g., 'common_stock', 'preferred_stock', 'bond', 'fund'
    market_cap = Column(Float)
    sector = Column(String)
    industry = Column(String)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class ResearchResults(Base):
    __tablename__ = "research_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_ticker = Column(String, nullable=False)

    # Current analysis state
    summary = Column(Text)
    risk_score = Column(Integer)
    confidence_score = Column(Integer)
    recommendation = Column(String)

    # Structured data
    structured_data = Column(JSON)  # Current analysis in structured form
    raw_results = Column(JSON)  # Raw LLM outputs
    search_queries = Column(JSON)  # Queries used to gather data

    # Source tracking
    source_date_range = Column(String)  # e.g., "2024-01-01 to 2024-03-31"
    total_sources = Column(Integer)
    source_categories = Column(JSON)  # Types of sources used

    # Temporal tracking
    last_iteration_id = Column(Integer, ForeignKey("research_iterations.id"))
    first_analyzed_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    last_updated_at = Column(TIMESTAMP, onupdate=func.current_timestamp())

    # Additional tracking info
    meta_info = Column(JSON)  # Additional tracking info (renamed from metadata)

    __table_args__ = (
        UniqueConstraint("company_ticker", name="_company_current_research_uc"),
    )


class ResearchSources(Base):
    __tablename__ = "research_sources"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String)
    snippet = Column(Text)
    source_type = Column(String, nullable=False)
    category = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    __table_args__ = (UniqueConstraint("ticker", "url", name="_ticker_url_uc"),)


class Portfolio(Base):
    __tablename__ = "portfolio"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    sector = Column(String)
    weight = Column(Float)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class Exclusion(Base):
    """Companies excluded from analysis for various reasons.
    Each record represents a specific exclusion reason for a company,
    allowing multiple reasons per company with different sources and timestamps."""
    
    __tablename__ = "exclusions"
    id = Column(BigInteger, primary_key=True)
    company = Column(String)
    ticker = Column(String, nullable=False)  # Remove unique constraint
    isin = Column(String)
    category = Column(String, nullable=False)  # Product-based or Conduct-based
    criteria = Column(String, nullable=False)  # Specific exclusion criteria
    concerned_groups = Column(String)  # Source of the exclusion decision
    decision = Column(String)
    excluded_date = Column(String)  # Original decision date if known
    notes = Column(Text)
    is_historical = Column(Boolean, default=False)  # Flag for backfilled/historical decisions
    excluded_at = Column(TIMESTAMP, server_default=func.current_timestamp())  # When we recorded this
    
    __table_args__ = (
        # Index to optimize queries by ticker
        Index('idx_exclusions_ticker', 'ticker'),
    )


class ResearchIteration(Base):
    __tablename__ = "research_iterations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_ticker = Column(String, nullable=False)
    iteration_type = Column(
        String, nullable=False
    )  # e.g., 'initial', 'daily_update', 'quarterly_deep_dive'

    # Input data used for this iteration
    source_count = Column(Integer)  # number of sources considered
    date_range = Column(String)  # e.g., "2024-01-01 to 2024-03-31"
    previous_iteration_id = Column(
        Integer, ForeignKey("research_iterations.id")
    )  # link to previous analysis

    # Analysis outputs
    summary = Column(Text)  # high-level summary
    key_changes = Column(JSON)  # what's different from last iteration
    risk_factors = Column(JSON)  # structured risk assessment
    opportunities = Column(JSON)  # structured opportunities assessment
    confidence_metrics = Column(JSON)  # confidence in different aspects

    # Validation and workflow
    status = Column(String)  # 'pending_review', 'validated', 'needs_correction'
    reviewer_notes = Column(Text)
    reviewed_by = Column(String)
    reviewed_at = Column(TIMESTAMP)

    # Metadata
    prompt_template = Column(String)  # which prompt version was used
    model_version = Column(String)  # which LLM version
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    __table_args__ = (
        UniqueConstraint(
            "company_ticker",
            "iteration_type",
            "created_at",
            name="_iteration_timestamp_uc",
        ),
    )


class ResearchReview(Base):
    __tablename__ = "research_reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # What's being reviewed
    research_result_id = Column(
        Integer, ForeignKey("research_results.id"), nullable=False
    )
    iteration_id = Column(Integer, ForeignKey("research_iterations.id"))
    company_ticker = Column(String, nullable=False)

    # Review details
    review_status = Column(
        String, nullable=False
    )  # 'pending', 'reviewed', 'needs_revision'
    accuracy_rating = Column(Integer)  # 1-5 scale
    completeness_rating = Column(Integer)  # 1-5 scale

    # Specific feedback
    factual_errors = Column(JSON)  # List of specific errors found
    missing_aspects = Column(JSON)  # Important points that were missed
    incorrect_emphasis = Column(JSON)  # Things over/under emphasized

    # Action items
    follow_up_tasks = Column(JSON)  # Additional research needed
    priority_level = Column(String)  # 'high', 'medium', 'low'

    # Review metadata
    reviewer_notes = Column(Text)  # Free-form notes
    reviewed_by = Column(String, nullable=False)
    reviewed_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # Learning feedback
    prompt_improvement = Column(Text)  # Suggestions for better prompts
    source_quality = Column(JSON)  # Feedback on source reliability

    __table_args__ = (
        UniqueConstraint("research_result_id", name="_one_review_per_result_uc"),
    )


class TickHistory(Base):
    """Track historical tick changes for securities."""

    __tablename__ = "tick_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, ForeignKey("universe.ticker"), nullable=False)
    date = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    old_tick = Column(Integer)
    new_tick = Column(Integer, nullable=False)
    note = Column(Text)
    updated_by = Column(String)

    # Validation constraints
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="_ticker_date_uc"),
        CheckConstraint(
            "new_tick >= -100 AND new_tick <= 100", name="tick_range_check"
        ),
    )
