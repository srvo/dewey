
# Refactored from: test_schema
# Date: 2025-03-16T16:19:11.275608
# Refactor Version: 1.0
import sys
import unittest
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from models.schema_verify import verify_schema
from models.tick_history import Base, get_engine


class TestSchema(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test database."""
        self.engine = get_engine(use_sqlite=True)
        Base.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        """Clean up test database."""
        Base.metadata.drop_all(self.engine)

    def test_schema_verification(self) -> None:
        """Test that schema verification passes with correct schema."""
        success, differences = verify_schema()
        assert success, f"Schema verification failed with differences: {differences}"

    def test_schema_differences(self) -> None:
        """Test that schema verification detects differences."""
        # Drop a column to create a schema mismatch
        with self.engine.connect() as conn:
            conn.execute("ALTER TABLE tick_history DROP COLUMN monthyear")

        success, differences = verify_schema()
        assert not success, "Schema verification should fail with missing column"
        assert any(
            "monthyear" in diff for diff in differences
        ), "Schema differences should mention missing monthyear column"


if __name__ == "__main__":
    unittest.main()
