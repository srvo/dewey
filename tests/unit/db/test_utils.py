"""
Tests for database utility functions.

This module tests the database utility functions.
"""

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from src.dewey.core.db.utils import (
    build_delete_query,
    build_insert_query,
    build_limit_clause,
    build_order_clause,
    build_select_query,
    build_update_query,
    build_where_clause,
    format_bool,
    format_json,
    format_list,
    format_timestamp,
    generate_id,
    parse_bool,
    parse_json,
    parse_list,
    parse_timestamp,
    sanitize_string,
)


class TestDatabaseUtils(unittest.TestCase):
    """Test database utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock database manager if needed
        self.db_manager_patcher = patch("src.dewey.core.db.utils.db_manager")
        self.mock_db_manager = self.db_manager_patcher.start()

    def tearDown(self):
        """Tear down test fixtures."""
        self.db_manager_patcher.stop()

    def test_generate_id(self):
        """Test generating unique IDs."""
        # Generate an ID
        id1 = generate_id()

        # Check that it's a string
        self.assertIsInstance(id1, str)

        # Generate another ID
        id2 = generate_id()

        # Check that they are different
        self.assertNotEqual(id1, id2)

        # Test with a prefix
        id3 = generate_id("test_")

        # Check that it has the prefix
        self.assertTrue(id3.startswith("test_"))

    def test_format_timestamp(self):
        """Test formatting timestamps."""
        # Create a timestamp
        dt = datetime(2023, 1, 15, 12, 30, 45, tzinfo=UTC)

        # Format it
        formatted = format_timestamp(dt)

        # Check format
        self.assertEqual(formatted, "2023-01-15T12:30:45+00:00")

        # Test with no timestamp (should use current time)
        formatted = format_timestamp()

        # Check that it's a string in ISO format
        self.assertIsInstance(formatted, str)
        self.assertIn("T", formatted)  # ISO format has a T between date and time

    def test_parse_timestamp(self):
        """Test parsing timestamps."""
        # Parse an ISO timestamp
        dt = parse_timestamp("2023-01-15T12:30:45+00:00")

        # Check result
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.hour, 12)
        self.assertEqual(dt.minute, 30)
        self.assertEqual(dt.second, 45)

        # Test with a different format
        dt = parse_timestamp("2023-01-15 12:30:45")

        # Check result
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.hour, 12)
        self.assertEqual(dt.minute, 30)
        self.assertEqual(dt.second, 45)

    def test_sanitize_string(self):
        """Test sanitizing strings."""
        # Sanitize a string with potentially dangerous SQL characters
        sanitized = sanitize_string("DROP TABLE; --comment")

        # Check that it's been sanitized
        self.assertNotIn(";", sanitized)
        self.assertNotIn("--", sanitized)

    def test_format_json(self):
        """Test formatting JSON."""
        # Create a Python object
        data = {"name": "Test", "value": 42}

        # Format as JSON
        formatted = format_json(data)

        # Check result
        self.assertIsInstance(formatted, str)

        # Parse back to ensure it's valid JSON
        parsed = json.loads(formatted)
        self.assertEqual(parsed["name"], "Test")
        self.assertEqual(parsed["value"], 42)

    def test_parse_json(self):
        """Test parsing JSON."""
        # Create a JSON string
        json_str = '{"name":"Test","value":42}'

        # Parse JSON
        parsed = parse_json(json_str)

        # Check result
        self.assertEqual(parsed["name"], "Test")
        self.assertEqual(parsed["value"], 42)

        # Test with invalid JSON
        with self.assertRaises(Exception):
            parse_json("Not valid JSON")

    def test_format_list(self):
        """Test formatting lists."""
        # Format a list
        formatted = format_list(["a", "b", "c"])

        # Check result
        self.assertEqual(formatted, "a,b,c")

        # Test with a different separator
        formatted = format_list(["a", "b", "c"], separator="|")
        self.assertEqual(formatted, "a|b|c")

    def test_parse_list(self):
        """Test parsing lists."""
        # Parse a comma-separated string
        parsed = parse_list("a,b,c")

        # Check result
        self.assertEqual(parsed, ["a", "b", "c"])

        # Test with a different separator
        parsed = parse_list("a|b|c", separator="|")
        self.assertEqual(parsed, ["a", "b", "c"])

    def test_format_bool(self):
        """Test formatting booleans."""
        # Format a boolean
        self.assertEqual(format_bool(True), 1)
        self.assertEqual(format_bool(False), 0)

    def test_parse_bool(self):
        """Test parsing booleans."""
        # Parse various boolean representations
        self.assertTrue(parse_bool(1))
        self.assertTrue(parse_bool("1"))
        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("TRUE"))
        self.assertTrue(parse_bool("yes"))

        self.assertFalse(parse_bool(0))
        self.assertFalse(parse_bool("0"))
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("FALSE"))
        self.assertFalse(parse_bool("no"))

    def test_build_where_clause(self):
        """Test building WHERE clauses."""
        # Build a simple WHERE clause
        where, params = build_where_clause({"id": 1, "name": "Test"})

        # Check result
        self.assertIn("WHERE", where)
        self.assertIn("id = ?", where)
        self.assertIn("name = ?", where)
        self.assertIn("AND", where)
        self.assertEqual(params, [1, "Test"])

        # Test with a NULL condition
        where, params = build_where_clause({"id": 1, "name": None})
        self.assertIn("name IS NULL", where)

        # Test with an IN condition
        where, params = build_where_clause({"id": [1, 2, 3]})
        self.assertIn("id IN (?, ?, ?)", where)
        self.assertEqual(params, [1, 2, 3])

    def test_build_order_clause(self):
        """Test building ORDER BY clauses."""
        # Build an ORDER BY clause
        order = build_order_clause("name")

        # Check result
        self.assertEqual(order, "ORDER BY name ASC")

        # Test with descending order
        order = build_order_clause("name DESC")
        self.assertEqual(order, "ORDER BY name DESC")

        # Test with multiple columns
        order = build_order_clause(["name ASC", "id DESC"])
        self.assertEqual(order, "ORDER BY name ASC, id DESC")

    def test_build_limit_clause(self):
        """Test building LIMIT clauses."""
        # Build a LIMIT clause
        limit = build_limit_clause(10)

        # Check result
        self.assertEqual(limit, "LIMIT 10")

        # Test with offset
        limit = build_limit_clause(10, 5)
        self.assertEqual(limit, "LIMIT 10 OFFSET 5")

    def test_build_select_query(self):
        """Test building SELECT queries."""
        # Build a simple SELECT query
        query, params = build_select_query("users")

        # Check result
        self.assertIn("SELECT * FROM users", query)

        # Test with columns
        query, params = build_select_query("users", columns=["id", "name"])
        self.assertIn("SELECT id, name FROM users", query)

        # Test with conditions
        query, params = build_select_query("users", conditions={"id": 1})
        self.assertIn("SELECT * FROM users WHERE id = ?", query)
        self.assertEqual(params, [1])

        # Test with order
        query, params = build_select_query("users", order_by="name")
        self.assertIn("SELECT * FROM users ORDER BY name ASC", query)

        # Test with limit
        query, params = build_select_query("users", limit=10)
        self.assertIn("SELECT * FROM users LIMIT 10", query)

        # Test with everything
        query, params = build_select_query(
            "users",
            columns=["id", "name"],
            conditions={"active": True},
            order_by="name",
            limit=10,
            offset=5,
        )
        self.assertIn(
            "SELECT id, name FROM users WHERE active = ? ORDER BY name ASC LIMIT 10 OFFSET 5",
            query,
        )
        self.assertEqual(params, [1])  # True is formatted as 1

    def test_build_insert_query(self):
        """Test building INSERT queries."""
        # Build an INSERT query
        query, params = build_insert_query("users", {"name": "Test", "age": 42})

        # Check result
        self.assertIn("INSERT INTO users", query)
        self.assertIn("name", query)
        self.assertIn("age", query)
        self.assertIn("VALUES (?, ?)", query)
        self.assertEqual(params, ["Test", 42])

    def test_build_update_query(self):
        """Test building UPDATE queries."""
        # Build an UPDATE query
        query, params = build_update_query(
            "users", {"name": "Updated", "age": 43}, {"id": 1},
        )

        # Check result
        self.assertIn("UPDATE users SET", query)
        self.assertIn("name = ?", query)
        self.assertIn("age = ?", query)
        self.assertIn("WHERE id = ?", query)
        self.assertEqual(params, ["Updated", 43, 1])

    def test_build_delete_query(self):
        """Test building DELETE queries."""
        # Build a DELETE query
        query, params = build_delete_query("users", {"id": 1})

        # Check result
        self.assertIn("DELETE FROM users WHERE id = ?", query)
        self.assertEqual(params, [1])


if __name__ == "__main__":
    unittest.main()
