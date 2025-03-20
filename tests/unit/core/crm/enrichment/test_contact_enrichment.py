"""Tests for contact enrichment service."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json
from dewey.core.crm.enrichment.contact_enrichment import ContactEnrichmentService

class TestContactEnrichmentService:
    """Test suite for contact enrichment service."""

    @pytest.fixture
    def service(self, mock_db_connection):
        """Create a ContactEnrichmentService instance."""
        return ContactEnrichmentService()

    def test_initialization(self, service):
        """Test service initialization."""
        assert service.engine is not None
        # Verify tables were created
        service.engine.execute.assert_any_call("""
            CREATE TABLE IF NOT EXISTS crm_contacts (
                id VARCHAR PRIMARY KEY,
                email VARCHAR UNIQUE,
                name VARCHAR,
                company VARCHAR,
                title VARCHAR,
                first_seen_date TIMESTAMP,
                last_seen_date TIMESTAMP,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def test_enrich_contact(self, service, sample_contact_data):
        """Test contact enrichment."""
        result = service.enrich_contact(sample_contact_data)
        assert result is not None
        assert "enriched" in result
        assert "data" in result
        assert result["data"]["company"] == "Example Corp"

    def test_store_enrichment(self, service, sample_contact_data, test_db):
        """Test storing enrichment data."""
        enrichment_data = {
            "enriched": True,
            "data": {
                "company": "Updated Corp",
                "title": "Senior Engineer",
                "linkedin_url": "https://linkedin.com/in/johndoe"
            }
        }
        
        service.store_enrichment(
            contact_id="contact123",
            email="john@example.com",
            enrichment_data=enrichment_data,
            conn=test_db
        )
        
        # Verify data was stored
        result = test_db.execute("""
            SELECT company, title 
            FROM crm_contacts 
            WHERE email = 'john@example.com'
        """).fetchone()
        
        assert result is not None
        assert result[0] == "Updated Corp"
        assert result[1] == "Senior Engineer"

    def test_process_contact_batch(self, service, test_db):
        """Test batch contact processing."""
        contacts = [
            {"email": "john@example.com", "name": "John Doe"},
            {"email": "jane@example.com", "name": "Jane Smith"}
        ]
        
        results = service.process_contact_batch(contacts)
        assert len(results) == 2
        assert all(r["enriched"] for r in results)
        assert all("data" in r for r in results)

    def test_validate_enrichment_data(self, service):
        """Test enrichment data validation."""
        valid_data = {
            "enriched": True,
            "data": {
                "company": "Test Corp",
                "title": "Engineer"
            }
        }
        assert service.validate_enrichment_data(valid_data) is True
        
        invalid_data = [
            {"enriched": True},  # Missing data
            {"data": {}},  # Missing enriched flag
            None,  # None
            {"enriched": True, "data": None}  # Invalid data
        ]
        for data in invalid_data:
            assert service.validate_enrichment_data(data) is False

    def test_update_contact_metadata(self, service, test_db):
        """Test updating contact metadata."""
        metadata = {
            "last_enrichment": datetime.now().isoformat(),
            "source": "test",
            "confidence": 0.95
        }
        
        service.update_contact_metadata(
            email="test@example.com",
            metadata=metadata,
            conn=test_db
        )
        
        # Verify metadata was updated
        result = test_db.execute("""
            SELECT metadata 
            FROM crm_contacts 
            WHERE email = 'test@example.com'
        """).fetchone()
        
        assert result is not None
        stored_metadata = json.loads(result[0])
        assert stored_metadata["source"] == "test"
        assert stored_metadata["confidence"] == 0.95

    def test_error_handling(self, service):
        """Test error handling."""
        # Test with invalid contact data
        with pytest.raises(ValueError):
            service.enrich_contact(None)
        
        # Test with invalid enrichment data
        with pytest.raises(ValueError):
            service.store_enrichment(
                contact_id="123",
                email="test@example.com",
                enrichment_data=None
            )

    @pytest.mark.integration
    def test_full_enrichment_workflow(self, service, test_db, sample_contact_data):
        """Integration test for full enrichment workflow."""
        # Process contact
        result = service.enrich_contact(sample_contact_data)
        assert result["enriched"] is True
        
        # Store enrichment
        service.store_enrichment(
            contact_id="contact123",
            email=sample_contact_data["email"],
            enrichment_data=result,
            conn=test_db
        )
        
        # Verify contact was updated
        stored_contact = test_db.execute("""
            SELECT email, company, title, metadata 
            FROM crm_contacts 
            WHERE email = ?
        """, [sample_contact_data["email"]]).fetchone()
        
        assert stored_contact is not None
        assert stored_contact[1] == result["data"]["company"]
        assert stored_contact[2] == result["data"]["title"]
        
        # Verify metadata
        metadata = json.loads(stored_contact[3])
        assert "last_enrichment" in metadata
        assert metadata["enriched"] is True 