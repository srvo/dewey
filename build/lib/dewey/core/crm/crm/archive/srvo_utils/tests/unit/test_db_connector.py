from django.test import TestCase
from django.db import connection


class TestDatabaseConnector(TestCase):
    def test_database_connection(self):
        """Test that we can connect to the database."""
        self.assertTrue(connection.is_usable())

    def test_session_creation(self):
        """Test that we can create a database session."""
        with connection.cursor() as cursor:
            self.assertIsNotNone(cursor)
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
