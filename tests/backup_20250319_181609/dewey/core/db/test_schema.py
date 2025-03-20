"""Tests for database schema management."""
import pytest
from unittest.mock import Mock, patch
import duckdb
from datetime import datetime

from dewey.core.db.schema import (
    create_tables,
    validate_schema,
    migrate_schema,
    TABLE_SCHEMAS,
    TABLE_INDEXES
)

class TestDatabaseSchema:
    """Test suite for database schema management."""

    def test_table_schemas_validity(self):
        """Test validity of table schema definitions."""
        for table_name, schema in TABLE_SCHEMAS.items():
            # Verify schema is a valid CREATE TABLE statement
            assert schema.strip().upper().startswith("CREATE TABLE")
            assert table_name in schema
            
            # Verify schema can be executed
            with duckdb.connect(':memory:') as conn:
                conn.execute(schema)
                # Verify table was created
                result = conn.execute(f"SELECT * FROM {table_name} LIMIT 0").fetchall()
                assert isinstance(result, list)

    def test_table_indexes_validity(self):
        """Test validity of table index definitions."""
        for table_name, indexes in TABLE_INDEXES.items():
            # Create table first
            with duckdb.connect(':memory:') as conn:
                conn.execute(TABLE_SCHEMAS[table_name])
                
                # Verify each index can be created
                for index_sql in indexes:
                    assert index_sql.strip().upper().startswith("CREATE INDEX")
                    conn.execute(index_sql)

    def test_create_tables(self, test_db):
        """Test table creation."""
        # Drop any existing tables
        for table_name in TABLE_SCHEMAS.keys():
            test_db.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create tables
        create_tables(test_db)
        
        # Verify tables were created
        for table_name in TABLE_SCHEMAS.keys():
            result = test_db.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table_name}'
            """).fetchone()
            assert result is not None
            assert result[0] == table_name

    def test_validate_schema(self, test_db):
        """Test schema validation."""
        # Create tables
        create_tables(test_db)
        
        # Validate schema
        assert validate_schema(test_db) is True
        
        # Drop a table and verify validation fails
        test_db.execute("DROP TABLE users")
        assert validate_schema(test_db) is False

    def test_migrate_schema(self, test_db):
        """Test schema migration."""
        # Create old version of schema
        test_db.execute("""
            CREATE TABLE users (
                id VARCHAR PRIMARY KEY,
                name VARCHAR
            )
        """)
        
        # Insert test data
        test_db.execute("""
            INSERT INTO users (id, name) VALUES ('1', 'test')
        """)
        
        # Migrate schema
        migrate_schema(test_db)
        
        # Verify new columns were added and data preserved
        result = test_db.execute("""
            SELECT id, name, email, created_at 
            FROM users WHERE id = '1'
        """).fetchone()
        
        assert result is not None
        assert result[0] == '1'
        assert result[1] == 'test'
        assert result[2] is None  # New email column should be NULL
        assert result[3] is not None  # created_at should have default value

    def test_schema_constraints(self, test_db):
        """Test schema constraints."""
        create_tables(test_db)
        
        # Test primary key constraint
        with pytest.raises(duckdb.ConstraintException):
            test_db.execute("""
                INSERT INTO users (id, name) VALUES 
                ('1', 'test1'),
                ('1', 'test2')  -- Duplicate primary key
            """)
        
        # Test foreign key constraint
        with pytest.raises(duckdb.ConstraintException):
            test_db.execute("""
                INSERT INTO transactions (id, user_id, amount)
                VALUES ('1', 'nonexistent', 100)
            """)

    def test_schema_defaults(self, test_db):
        """Test schema default values."""
        create_tables(test_db)
        
        # Insert row with minimal values
        test_db.execute("""
            INSERT INTO users (id, name) VALUES ('1', 'test')
        """)
        
        # Verify default values
        result = test_db.execute("""
            SELECT created_at, updated_at, is_active
            FROM users WHERE id = '1'
        """).fetchone()
        
        assert result is not None
        assert result[0] is not None  # created_at should have default
        assert result[1] is not None  # updated_at should have default
        assert result[2] is True  # is_active should default to true

@pytest.mark.integration
class TestDatabaseSchemaIntegration:
    """Integration tests for database schema management."""

    def test_full_schema_workflow(self, test_db):
        """Test complete schema management workflow."""
        # Start with empty database
        for table_name in TABLE_SCHEMAS.keys():
            test_db.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create schema
        create_tables(test_db)
        
        # Verify schema
        assert validate_schema(test_db) is True
        
        # Insert test data
        test_db.execute("""
            INSERT INTO users (id, name, email) VALUES 
            ('1', 'test1', 'test1@example.com'),
            ('2', 'test2', 'test2@example.com')
        """)
        
        test_db.execute("""
            INSERT INTO transactions (id, user_id, amount) VALUES
            ('t1', '1', 100),
            ('t2', '1', 200),
            ('t3', '2', 300)
        """)
        
        # Verify data
        users = test_db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        transactions = test_db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        
        assert users == 2
        assert transactions == 3
        
        # Test schema migration
        migrate_schema(test_db)
        
        # Verify data was preserved
        assert test_db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
        assert test_db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 3 