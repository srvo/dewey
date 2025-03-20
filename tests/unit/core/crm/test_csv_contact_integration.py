"""Tests for CSV contact integration."""
import pytest
from pathlib import Path
import json
from datetime import datetime
from dewey.core.crm.csv_contact_integration import (
    process_client_contact_master,
    process_blog_signup_form,
    process_onboarding_form,
    update_unified_contacts
)

class TestCSVContactIntegration:
    """Test suite for CSV contact integration."""

    def test_process_client_contact_master(self, sample_csv_data):
        """Test processing client contact master CSV."""
        contacts = process_client_contact_master(sample_csv_data["client_master"])
        assert len(contacts) == 1
        
        contact = contacts[0]
        assert contact["email"] == "john@example.com"
        assert contact["first_name"] == "John"
        assert contact["last_name"] == "Doe"
        assert contact["country"] == "US"
        assert contact["source"] == "client_contact_master"
        
        # Verify metadata
        metadata = json.loads(contact["metadata"])
        assert metadata["sent"] == "10"
        assert metadata["opens"] == "5"
        assert metadata["clicks"] == "2"

    def test_process_blog_signup_form(self, sample_csv_data):
        """Test processing blog signup form CSV."""
        contacts = process_blog_signup_form(sample_csv_data["blog_signup"])
        assert len(contacts) == 1
        
        contact = contacts[0]
        assert contact["email"] == "jane@example.com"
        assert contact["full_name"] == "Jane Smith"
        assert contact["company"] == "Tech Corp"
        assert contact["phone"] == "123456789"
        assert contact["source"] == "blog_signup_form"
        assert contact["tags"] == "blog_signup"

    def test_process_onboarding_form(self, sample_csv_data):
        """Test processing onboarding form CSV."""
        contacts = process_onboarding_form(sample_csv_data["onboarding"])
        assert len(contacts) == 1
        
        contact = contacts[0]
        assert contact["email"] == "bob@example.com"
        assert contact["full_name"] == "Bob Wilson"
        assert contact["company"] == "Dev Inc"
        assert contact["phone"] == "987654321"
        assert contact["source"] == "onboarding_form"
        assert contact["tags"] == "onboarding,client"

    def test_update_unified_contacts(self, test_db):
        """Test updating unified contacts table."""
        contacts = {
            "john@example.com": {
                "email": "john@example.com",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
                "company": "Example Corp",
                "job_title": "Engineer",
                "phone": "123456789",
                "country": "US",
                "source": "test",
                "domain": "example.com",
                "last_interaction_date": datetime.now().isoformat(),
                "first_seen_date": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "tags": "test",
                "notes": "Test note",
                "metadata": json.dumps({"key": "value"})
            }
        }
        
        update_unified_contacts(test_db, contacts)
        
        # Verify contact was updated
        result = test_db.execute("""
            SELECT email, full_name, company, job_title 
            FROM crm_contacts 
            WHERE email = 'john@example.com'
        """).fetchone()
        
        assert result is not None
        assert result[0] == "john@example.com"
        assert result[1] == "John Doe"
        assert result[2] == "Example Corp"
        assert result[3] == "Engineer"

    def test_error_handling(self, tmp_path):
        """Test error handling for invalid files."""
        # Test with non-existent file
        assert process_client_contact_master("nonexistent.csv") == []
        
        # Test with invalid CSV format
        invalid_file = tmp_path / "invalid.csv"
        invalid_file.write_text("invalid,csv,format")
        assert process_blog_signup_form(str(invalid_file)) == []
        
        # Test with empty file
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")
        assert process_onboarding_form(str(empty_file)) == []

    def test_data_validation(self, sample_csv_data):
        """Test data validation in processing."""
        # Test client contact master with missing email
        contacts = process_client_contact_master(sample_csv_data["client_master"])
        assert all(c["email"] for c in contacts)
        
        # Test blog signup with missing required fields
        contacts = process_blog_signup_form(sample_csv_data["blog_signup"])
        assert all(c["email"] and c["full_name"] for c in contacts)
        
        # Test onboarding form with missing fields
        contacts = process_onboarding_form(sample_csv_data["onboarding"])
        assert all(c["email"] and c["full_name"] for c in contacts)

    @pytest.mark.integration
    def test_full_integration_workflow(self, sample_csv_data, test_db):
        """Integration test for full CSV integration workflow."""
        # Process all CSV files
        client_contacts = process_client_contact_master(
            sample_csv_data["client_master"]
        )
        blog_contacts = process_blog_signup_form(
            sample_csv_data["blog_signup"]
        )
        onboarding_contacts = process_onboarding_form(
            sample_csv_data["onboarding"]
        )
        
        # Combine all contacts
        all_contacts = {}
        for contacts in [client_contacts, blog_contacts, onboarding_contacts]:
            for contact in contacts:
                all_contacts[contact["email"]] = contact
        
        # Update unified contacts
        update_unified_contacts(test_db, all_contacts)
        
        # Verify all contacts were stored
        result = test_db.execute("""
            SELECT COUNT(*) FROM crm_contacts
        """).fetchone()
        
        assert result[0] == len(all_contacts)
        
        # Verify specific contact details
        for email in ["john@example.com", "jane@example.com", "bob@example.com"]:
            result = test_db.execute("""
                SELECT email, source FROM crm_contacts WHERE email = ?
            """, [email]).fetchone()
            assert result is not None
            assert result[0] == email 