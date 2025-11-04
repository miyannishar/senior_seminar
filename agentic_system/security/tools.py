"""
Security tools for validation, RBAC, and PII masking.
Standalone functions for security operations.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from typing import Dict, Any, List, Optional

from validator import (
    validation_filter,
    batch_validate,
    check_access_permission,
    ComplianceValidator
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_security_tools():
    """
    Create security tool functions.
    
    Returns:
        Tuple of tool functions: (validate_document, batch_validate_documents, check_permissions)
    """
    logger.info("✅ Security tools initialized")
    
    def validate_document(
        document: Dict[str, Any] = None,
        user_role: str = None,
        mask_pii: bool = True,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a single document against user permissions.
        
        Args:
            document: Document to validate (required)
            user_role: User's role (admin, analyst, manager, employee, guest) (required)
            mask_pii: Whether to mask PII
        
        Returns:
            Validated document or None if access denied
        """
        # Handle ADK function calling format
        if document is None and 'document' in kwargs:
            document = kwargs['document']
        if user_role is None and 'user_role' in kwargs:
            user_role = kwargs['user_role']
        if document is None or user_role is None:
            raise ValueError("document and user_role parameters are required")
            
        logger.info(f"🔒 Validating document {document.get('id')} for role: {user_role}")
        
        try:
            validated = validation_filter(
                doc=document,
                user_role=user_role,
                mask_pii=mask_pii,
                log_violations=True
            )
            
            if validated:
                logger.info(f"✅ Document {document.get('id')} validated")
            else:
                logger.warning(f"🚫 Access denied to {document.get('id')}")
            
            return validated
            
        except Exception as e:
            logger.error(f"❌ Validation error: {e}")
            return None
    
    def batch_validate_documents(
        documents: List[Dict[str, Any]] = None,
        user_role: str = None,
        mask_pii: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple documents efficiently.
        
        Args:
            documents: List of documents to validate (required)
            user_role: User's role (required)
            mask_pii: Whether to mask PII
        
        Returns:
            List of validated documents (denied ones filtered out)
        """
        # Handle ADK function calling format
        if documents is None and 'documents' in kwargs:
            documents = kwargs['documents']
        if user_role is None and 'user_role' in kwargs:
            user_role = kwargs['user_role']
        if documents is None or user_role is None:
            raise ValueError("documents and user_role parameters are required")
            
        logger.info(f"🔒 Batch validating {len(documents)} documents for {user_role}")
        
        try:
            validated = batch_validate(
                documents=documents,
                user_role=user_role,
                mask_pii=mask_pii
            )
            
            denied = len(documents) - len(validated)
            logger.info(f"✅ Validated: {len(validated)}, Denied: {denied}")
            
            return validated
            
        except Exception as e:
            logger.error(f"❌ Batch validation error: {e}")
            return []
    
    def check_permissions(
        user_role: str = None,
        domain: str = None,
        **kwargs
    ) -> bool:
        """
        Check if user role has access to domain.
        
        Args:
            user_role: User's role (required)
            domain: Document domain (required)
        
        Returns:
            True if access allowed, False otherwise
        """
        # Handle ADK function calling format
        if user_role is None and 'user_role' in kwargs:
            user_role = kwargs['user_role']
        if domain is None and 'domain' in kwargs:
            domain = kwargs['domain']
        if user_role is None or domain is None:
            raise ValueError("user_role and domain parameters are required")
            
        try:
            allowed = check_access_permission(user_role, domain)
            logger.info(f"🔑 Permission check: {user_role} -> {domain}: {allowed}")
            return allowed
        except Exception as e:
            logger.error(f"❌ Permission check error: {e}")
            return False
    
    def validate_compliance(
        document: Dict[str, Any] = None,
        user_role: str = None,
        framework: str = "general",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Validate document against compliance framework.
        
        Args:
            document: Document to validate (required)
            user_role: User's role (required)
            framework: Compliance framework (hipaa, gdpr, sox, general)
        
        Returns:
            Validated document or None if non-compliant
        """
        # Handle ADK function calling format
        if document is None and 'document' in kwargs:
            document = kwargs['document']
        if user_role is None and 'user_role' in kwargs:
            user_role = kwargs['user_role']
        if framework == "general" and 'framework' in kwargs:
            framework = kwargs['framework']
        if document is None or user_role is None:
            raise ValueError("document and user_role parameters are required")
            
        logger.info(f"⚖️  Validating against {framework.upper()} for {user_role}")
        
        try:
            validator = ComplianceValidator(framework=framework)
            validated = validator.validate(document, user_role)
            
            if validated:
                logger.info(f"✅ Document complies with {framework.upper()}")
            else:
                logger.warning(f"🚫 Document violates {framework.upper()}")
            
            return validated
            
        except Exception as e:
            logger.error(f"❌ Compliance validation error: {e}")
            return None
    
    return validate_document, batch_validate_documents, check_permissions, validate_compliance
