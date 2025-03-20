"""Tests for database utilities."""
import pytest
from unittest.mock import Mock, patch
import uuid
from datetime import datetime, timezone
from typing import List, Tuple

from dewey.core.db.utils import (
    generate_id,
    execute_batch,
    DatabaseConnectionError
)

class TestDatabaseUtils:
    """Test suite for database utilities."""

    def test_generate_id(self):
        """Test ID generation."""
        # Test without prefix
        id1 = generate_id()
        assert isinstance(id1, str)
        assert len(id1) == 32  # UUID hex length
        
        # Test with prefix
        prefix = "test_"
        id2 = generate_id(prefix)
        assert id2.startswith(prefix)
        assert len(id2) == len(prefix) + 32
        
        # Test uniqueness
        ids = [generate_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All IDs should be unique

    def test_execute_batch(self, mock_db_manager, sample_batch_queries):
        """Test batch query execution."""
        # Test successful batch execution
        execute_batch(sample_batch_queries)
        
        # Verify transaction management
        calls = mock_db_manager.execute_query.call_args_list
        assert calls[0][0][0] == "BEGIN TRANSACTION"
        assert calls[-1][0][0] == "COMMIT"
        
        # Verify all queries were executed
        for i, (query, params) in enumerate(sample_batch_queries, start=1):
            assert calls[i][0][0] == query
            assert calls[i][0][1] == params

    def test_execute_batch_rollback(self, mock_db_manager):
        """Test batch execution rollback on error."""
        # Create a failing query
        failing_queries = [
            ("INSERT INTO test VALUES (?)", [1]),
            ("INVALID SQL", []),  # This will fail
            ("INSERT INTO test VALUES (?)", [2])
        ]
        
        # Test that rollback occurs on error
        with pytest.raises(DatabaseConnectionError):
            execute_batch(failing_queries)
        
        # Verify transaction was rolled back
        calls = mock_db_manager.execute_query.call_args_list
        assert calls[0][0][0] == "BEGIN TRANSACTION"
        assert calls[-1][0][0] == "ROLLBACK"

    def test_execute_batch_empty(self, mock_db_manager):
        """Test batch execution with empty query list."""
        execute_batch([])
        mock_db_manager.execute_query.assert_not_called()

    def test_execute_batch_local_only(self, mock_db_manager):
        """Test batch execution in local-only mode."""
        execute_batch(sample_batch_queries, local_only=True)
        
        # Verify local_only flag was passed
        for call in mock_db_manager.execute_query.call_args_list:
            assert call[1].get('local_only') is True

@pytest.mark.integration
class TestDatabaseUtilsIntegration:
    """Integration tests for database utilities."""

    def test_batch_operations(self, test_db):
        """Test batch operations with real database."""
        # Create test table
        test_db.execute("""
            CREATE TABLE batch_test (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Prepare batch queries
        queries = [
            ("INSERT INTO batch_test VALUES (?, ?)", [1, "test1"]),
            ("INSERT INTO batch_test VALUES (?, ?)", [2, "test2"]),
            ("UPDATE batch_test SET value = ? WHERE id = ?", ["updated", 1])
        ]
        
        # Execute batch
        execute_batch(queries)
        
        # Verify results
        result = test_db.execute("""
            SELECT * FROM batch_test ORDER BY id
        """).fetchall()
        
        assert len(result) == 2
        assert result[0] == (1, "updated")
        assert result[1] == (2, "test2")

    def test_batch_rollback(self, test_db):
        """Test batch rollback with real database."""
        # Create test table
        test_db.execute("""
            CREATE TABLE rollback_test (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Prepare queries with an error
        queries = [
            ("INSERT INTO rollback_test VALUES (?, ?)", [1, "test1"]),
            ("INVALID SQL", []),  # This will fail
            ("INSERT INTO rollback_test VALUES (?, ?)", [2, "test2"])
        ]
        
        # Execute batch (should fail)
        with pytest.raises(DatabaseConnectionError):
            execute_batch(queries)
        
        # Verify no data was committed
        result = test_db.execute("""
            SELECT COUNT(*) FROM rollback_test
        """).fetchone()
        
        assert result[0] == 0  # Table should be empty due to rollback 