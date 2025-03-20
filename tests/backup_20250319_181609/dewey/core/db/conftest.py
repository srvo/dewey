"""Common test fixtures for database tests."""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import duckdb
from datetime import datetime
import json
from typing import Dict, Any

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration."""
    return {
        'local_db_path': ':memory:',  # Use in-memory database for tests
        'motherduck_db': 'md:dewey_test',
        'motherduck_token': 'test_token',
        'pool_size': 2,
        'max_retries': 2,
        'retry_delay': 0.1,
        'sync_interval': 60,
        'max_sync_age': 3600,
        'backup_dir': '/tmp/dewey_test_backups',
        'backup_retention_days': 1
    }

@pytest.fixture
def mock_duckdb_connection():
    """Create a mock DuckDB connection."""
    mock = MagicMock()
    mock.execute.return_value.fetchall.return_value = [(1,)]
    return mock

@pytest.fixture
def test_db():
    """Create a test database connection."""
    conn = duckdb.connect(':memory:')
    
    # Create test tables
    conn.execute("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            value DOUBLE,
            created_at TIMESTAMP
        )
    """)
    
    # Insert sample data
    conn.execute("""
        INSERT INTO test_table VALUES 
        (1, 'test1', 1.1, CURRENT_TIMESTAMP),
        (2, 'test2', 2.2, CURRENT_TIMESTAMP)
    """)
    
    yield conn
    conn.close()

@pytest.fixture
def mock_motherduck():
    """Create a mock MotherDuck connection."""
    with patch('duckdb.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [(1,)]
        mock_connect.return_value = mock_conn
        yield mock_conn

@pytest.fixture
def sample_table_schemas():
    """Provide sample table schemas for testing."""
    return {
        'users': """
            CREATE TABLE users (
                id VARCHAR PRIMARY KEY,
                email VARCHAR UNIQUE,
                name VARCHAR,
                created_at TIMESTAMP
            )
        """,
        'transactions': """
            CREATE TABLE transactions (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                amount DECIMAL(18,2),
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
    }

@pytest.fixture
def sample_table_indexes():
    """Provide sample table indexes for testing."""
    return {
        'users': [
            'CREATE INDEX idx_users_email ON users(email)',
            'CREATE INDEX idx_users_created_at ON users(created_at)'
        ],
        'transactions': [
            'CREATE INDEX idx_transactions_user_id ON transactions(user_id)',
            'CREATE INDEX idx_transactions_created_at ON transactions(created_at)'
        ]
    }

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    env_vars = {
        'DEWEY_LOCAL_DB': ':memory:',
        'DEWEY_MOTHERDUCK_DB': 'md:dewey_test',
        'MOTHERDUCK_TOKEN': 'test_token',
        'DEWEY_DB_POOL_SIZE': '2',
        'DEWEY_DB_MAX_RETRIES': '2',
        'DEWEY_DB_RETRY_DELAY': '0.1',
        'DEWEY_SYNC_INTERVAL': '60',
        'DEWEY_MAX_SYNC_AGE': '3600',
        'DEWEY_BACKUP_DIR': '/tmp/dewey_test_backups',
        'DEWEY_BACKUP_RETENTION_DAYS': '1'
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars

@pytest.fixture
def mock_db_manager():
    """Create a mock DatabaseManager."""
    mock = MagicMock()
    mock.execute_query.return_value = [(1,)]
    mock.is_online.return_value = True
    return mock

@pytest.fixture
def sample_batch_queries():
    """Provide sample batch queries for testing."""
    return [
        ("INSERT INTO test_table (id, name) VALUES (?, ?)", [1, "test1"]),
        ("UPDATE test_table SET name = ? WHERE id = ?", ["updated", 1]),
        ("DELETE FROM test_table WHERE id = ?", [1])
    ] 