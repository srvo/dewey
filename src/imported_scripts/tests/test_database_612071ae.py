from django.db import connection
from django.test import TestCase


class TestDatabaseConnector(TestCase):
    def test_database_connection(self) -> None:
        """Test that we can connect to the database."""
        assert connection.is_usable()

    def test_session_creation(self) -> None:
        """Test that we can create a database session."""
        with connection.cursor() as cursor:
            assert cursor is not None
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
