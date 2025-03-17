"""Test data store functionality."""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ethifinx.db.data_store import DataStore
from ethifinx.db.exceptions import DatabaseSaveError
from ethifinx.db.models import Base, TestTable

Base = declarative_base()


class TestModel(Base):
    """Test model for database operations."""

    __tablename__ = "test_table"

    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)

    def __init__(self, key: str, value: str):
        """Initialize test model."""
        self.key = key
        self.value = value


@pytest.fixture(scope="session")
def test_engine():
    """Create test engine."""
    engine = create_engine("sqlite:///:memory:")
    return engine


@pytest.fixture(scope="session")
def setup_test_database(test_engine):
    """Set up test database."""
    Base.metadata.create_all(test_engine)
    return test_engine


@pytest.fixture(scope="session")
def test_session(test_engine):
    """Create test session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def data_store(test_session):
    """Create DataStore instance."""
    return DataStore(session=test_session)


def test_save_to_db_success(data_store):
    """Test successful database save."""
    test_data = TestTable(key="test", value="value")
    data_store.save_to_db(test_data)
    saved_data = data_store.session.query(TestTable).first()
    assert saved_data.key == "test"
    assert saved_data.value == "value"


def test_save_to_db_failure(data_store):
    """Test database save failure."""
    with pytest.raises(DatabaseSaveError):
        test_data = TestTable(
            key=None, value=None
        )  # This should fail due to nullable=False
        data_store.save_to_db(test_data)
