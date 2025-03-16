def model(dbt, session):
    dbt.config(materialized="table", packages=["sqlalchemy"])

    from sqlalchemy import Column, Float, String
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class TickHistory(Base):
        __tablename__ = "tick_history"

        ticker = Column(String, primary_key=True)
        old_tick = Column(String)
        new_tick = Column(String)
        date = Column(String, primary_key=True)
        isin = Column(String)
        month = Column(Float)
        year = Column(Float)
        monthyear = Column(Float)

    # Query your source data
    return dbt.ref("stg_tick_history")  # Use staging model instead of source
