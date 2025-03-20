from dewey.core.base_script import BaseScript

import json
import unittest

from farfalle.scripts.analyze_entities import CompanyTracker, EntityAnalysis


class TestCompanyTracker(BaseScriptunittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tracker = CompanyTracker(db_path=":memory:")

    async def test_save_and_get_analysis(self) -> None:
        """Test basic save and retrieve functionality."""
        analysis = EntityAnalysis(
            name="Test Company",
            sector="Test Sector",
            has_controversy=True,
            controversy_summary="Test summary",
            confidence_score=0.9,
            sources=["http://example.com"],
        )
        await self.tracker.save_analysis(analysis)
        retrieved = await self.tracker.get_analysis("Test Company")
        assert retrieved is not None
        assert retrieved["has_controversy"] is True
        assert retrieved["controversy_summary"] == "Test summary"
        assert retrieved["confidence_score"] == 0.9
        assert json.loads(retrieved["sources"]) == ["http://example.com"]

    async def test_get_nonexistent_analysis(self) -> None:
        """Test retrieving a non-existent company."""
        result = await self.tracker.get_analysis("Nonexistent Company")
        assert result is None

    async def test_get_all_analyses(self) -> None:
        """Test retrieving all analyses."""
        # Add multiple analyses
        companies = [
            ("Company A", "Sector 1", True),
            ("Company B", "Sector 2", False),
            ("Company C", "Sector 1", True),
        ]

        for name, sector, has_controversy in companies:
            analysis = EntityAnalysis(
                name=name,
                sector=sector,
                has_controversy=has_controversy,
                controversy_summary=f"Summary for {name}",
                confidence_score=0.8,
                sources=[],
            )
            await self.tracker.save_analysis(analysis)

        all_analyses = await self.tracker.get_all_analyses()
        assert len(all_analyses) == 3
        assert sorted([a["company_name"] for a in all_analyses]) == sorted(
            [name for name, _, _ in companies],
        )

    async def test_error_conditions(self) -> None:
        """Test error handling in save and retrieve."""
        # Test invalid company name
        await self.tracker.save_analysis(
            EntityAnalysis(
                name="",
                sector="Test",
                has_controversy=True,
                controversy_summary="Test",
                confidence_score=0.5,
                sources=[],
            ),
        )
        assert await self.tracker.get_analysis("") is None

    async def test_edge_cases(self) -> None:
        """Test edge cases in data handling."""
        # Test very long text
        long_text = "x" * 10000
        analysis = EntityAnalysis(
            name="Long Text Co",
            sector="Test",
            has_controversy=True,
            controversy_summary=long_text,
            confidence_score=1.0,
            sources=[],
        )
        await self.tracker.save_analysis(analysis)
        retrieved = await self.tracker.get_analysis("Long Text Co")
        assert retrieved["controversy_summary"] == long_text


if __name__ == "__main__":
    unittest.main()
