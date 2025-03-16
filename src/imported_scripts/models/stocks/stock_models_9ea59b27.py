def model(dbt, session):
    dbt.config(
        materialized="table",
        packages=["sqlalchemy"],
    )

    from sqlalchemy import (
        Boolean,
        Column,
        DateTime,
        Float,
        ForeignKey,
        Integer,
        String,
        Text,
    )
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import relationship

    Base = declarative_base()

    class TrackedStock(Base):
        __tablename__ = "tracked_stocks"

        id = Column(Integer, primary_key=True)
        symbol = Column(String(10), unique=True, index=True)  # Stock symbol like 'AAPL'
        isin = Column(String(12), unique=True, nullable=True)  # ISIN number
        name = Column(String(100))  # Company name
        is_active = Column(Boolean, default=True)  # To temporarily disable tracking
        notes = Column(Text, nullable=True)  # Any notes about why we're tracking this
        added_date = Column(DateTime)  # When we started tracking

        # Relationship to analyses
        analyses = relationship("StockAnalysis", back_populates="stock")

    class StockAnalysis(Base):
        __tablename__ = "stock_analysis"

        id = Column(Integer, primary_key=True)
        stock_id = Column(Integer, ForeignKey("tracked_stocks.id"))
        timestamp = Column(DateTime, index=True)  # When analysis was run
        price = Column(Float)  # Current price
        industry = Column(String(100))  # Industry classification

        # Analysis results
        fundamental_changes = Column(Text)  # What fundamental things changed
        psychological_changes = Column(Text)  # Market sentiment changes
        industry_comparison = Column(Text)  # How it compares to industry
        market_comparison = Column(Text)  # How it compares to broader market
        market_insights = Column(
            Text,
            nullable=True,
        )  # Recent market insights from Farfalle search

        # Additional metrics we might want
        volume = Column(Float)
        market_cap = Column(Float)
        pe_ratio = Column(Float)

        # Relationship back to the tracked stock
        stock = relationship("TrackedStock", back_populates="analyses")

    # Query your source data
    stocks_df = dbt.ref("stg_universe")  # Use staging model
    dbt.ref("stg_exclusions")  # Use staging model

    # For now, just return stocks data
    return stocks_df
