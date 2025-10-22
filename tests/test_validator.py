"""
Tests for Validation Module
"""

import pytest
from validator import (
    mask_sensitive_data,
    detect_sensitive_terms,
    check_access_permission,
    validation_filter,
    batch_validate,
    ComplianceValidator
)


class TestPIIMasking:
    """Tests for PII masking functionality."""
    
    def test_ssn_masking(self):
        """Test SSN masking."""
        text = "My SSN is 123-45-6789 and another 987654321"
        masked = mask_sensitive_data(text, aggressive=True)
        assert "123-45-6789" not in masked
        assert "[MASKED-SSN]" in masked
    
    def test_credit_card_masking(self):
        """Test credit card masking."""
        text = "Card: 4532-1234-5678-9010"
        masked = mask_sensitive_data(text, aggressive=True)
        assert "4532-1234-5678-9010" not in masked
        assert "[MASKED-CC]" in masked
    
    def test_email_masking(self):
        """Test email masking."""
        text = "Contact: user@example.com"
        masked = mask_sensitive_data(text, aggressive=True)
        assert "user@example.com" not in masked
        assert "[MASKED-EMAIL]" in masked
    
    def test_phone_masking(self):
        """Test phone number masking."""
        text = "Call: 555-123-4567"
        masked = mask_sensitive_data(text, aggressive=True)
        assert "555-123-4567" not in masked
        assert "[MASKED-PHONE]" in masked


class TestSensitiveTermDetection:
    """Tests for sensitive term detection."""
    
    def test_detect_ssn_term(self):
        """Test detection of SSN term."""
        text = "This document contains SSN information"
        detected = detect_sensitive_terms(text)
        assert "SSN" in detected
    
    def test_detect_salary_term(self):
        """Test detection of salary term."""
        text = "Employee Salary details are confidential"
        detected = detect_sensitive_terms(text)
        assert "Salary" in detected or "Confidential" in detected
    
    def test_no_sensitive_terms(self):
        """Test document without sensitive terms."""
        text = "This is a public announcement"
        detected = detect_sensitive_terms(text)
        assert len(detected) == 0


class TestRBAC:
    """Tests for Role-Based Access Control."""
    
    def test_admin_access(self):
        """Test admin can access all domains."""
        assert check_access_permission("admin", "finance")
        assert check_access_permission("admin", "hr")
        assert check_access_permission("admin", "health")
        assert check_access_permission("admin", "public")
    
    def test_analyst_access(self):
        """Test analyst access."""
        assert check_access_permission("analyst", "finance")
        assert check_access_permission("analyst", "hr")
        assert check_access_permission("analyst", "public")
        assert not check_access_permission("analyst", "health")
    
    def test_employee_access(self):
        """Test employee limited access."""
        assert check_access_permission("employee", "public")
        assert not check_access_permission("employee", "finance")
        assert not check_access_permission("employee", "hr")
    
    def test_guest_access(self):
        """Test guest very limited access."""
        assert check_access_permission("guest", "public")
        assert not check_access_permission("guest", "finance")


class TestValidationFilter:
    """Tests for document validation."""
    
    def test_allowed_access(self, sample_documents):
        """Test validation allows appropriate access."""
        doc = sample_documents[0]  # Finance document
        validated = validation_filter(doc, "analyst", mask_pii=False)
        assert validated is not None
        assert validated['id'] == doc['id']
    
    def test_denied_access(self, sample_documents):
        """Test validation denies inappropriate access."""
        doc = sample_documents[0]  # Finance document
        validated = validation_filter(doc, "guest", mask_pii=False)
        assert validated is None
    
    def test_pii_masking_applied(self, sample_documents):
        """Test PII masking is applied."""
        doc = {
            "id": "test_pii",
            "content": "SSN: 123-45-6789",
            "domain": "public"
        }
        validated = validation_filter(doc, "guest", mask_pii=True)
        assert validated is not None
        assert "123-45-6789" not in validated['content']


class TestBatchValidation:
    """Tests for batch validation."""
    
    def test_batch_validate_admin(self, sample_documents):
        """Test batch validation for admin."""
        validated = batch_validate(sample_documents, "admin")
        assert len(validated) == len(sample_documents)
    
    def test_batch_validate_employee(self, sample_documents):
        """Test batch validation for employee."""
        validated = batch_validate(sample_documents, "employee")
        # Should only get public documents
        assert all(doc['domain'] == 'public' for doc in validated)
    
    def test_batch_validate_counts(self, sample_documents):
        """Test validation counts are correct."""
        validated = batch_validate(sample_documents, "analyst")
        # Analyst should get finance, hr, and public (not health)
        assert len(validated) == 3


class TestComplianceValidator:
    """Tests for compliance framework validation."""
    
    def test_hipaa_validation(self, sample_documents):
        """Test HIPAA compliance."""
        validator = ComplianceValidator(framework="hipaa")
        
        # Health document should pass for admin
        health_doc = sample_documents[3]
        validated = validator.validate(health_doc, "admin")
        assert validated is not None
        
        # Finance document should fail
        finance_doc = sample_documents[0]
        validated = validator.validate(finance_doc, "admin")
        assert validated is None
    
    def test_gdpr_validation(self, sample_documents):
        """Test GDPR compliance."""
        validator = ComplianceValidator(framework="gdpr")
        
        # Only public should pass
        public_doc = sample_documents[2]
        validated = validator.validate(public_doc, "employee")
        assert validated is not None
    
    def test_sox_validation(self, sample_documents):
        """Test SOX compliance."""
        validator = ComplianceValidator(framework="sox")
        
        # Finance should pass
        finance_doc = sample_documents[0]
        validated = validator.validate(finance_doc, "analyst")
        assert validated is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

