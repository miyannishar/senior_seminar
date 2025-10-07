"""
Validation and Privacy Filtering Module
Implements multi-step validation including:
- Sensitive term detection
- PII masking
- Role-based access control (RBAC)
- Regulatory compliance filtering
"""

import re
from typing import Dict, Any, Optional, List

from utils.logger import setup_logger, log_access_attempt, log_pii_detection
from utils.exceptions import AccessDeniedException
from constants import SENSITIVE_TERMS, PII_PATTERNS, ROLE_ACCESS

logger = setup_logger(__name__)


def mask_sensitive_data(text: str, aggressive: bool = False) -> str:
    """
    Mask sensitive information in text using regex patterns.
    
    Args:
        text: Text to be masked
        aggressive: If True, applies all PII patterns. If False, only common ones.
    
    Returns:
        Text with sensitive data masked
    """
    masked_text = text
    patterns_to_apply = PII_PATTERNS if aggressive else {
        k: v for k, v in PII_PATTERNS.items() 
        if k in ['ssn', 'ssn_no_dash', 'credit_card', 'account_id']
    }
    
    for pattern_name, (pattern, replacement) in patterns_to_apply.items():
        masked_text = re.sub(pattern, replacement, masked_text)
    
    return masked_text


def detect_sensitive_terms(text: str) -> List[str]:
    """
    Detect sensitive terms in the text.
    
    Args:
        text: Text to scan
    
    Returns:
        List of detected sensitive terms
    """
    detected = []
    text_lower = text.lower()
    
    for term in SENSITIVE_TERMS:
        if term.lower() in text_lower:
            detected.append(term)
    
    return detected


def check_access_permission(user_role: str, document_domain: str) -> bool:
    """Check if a user role has access to a document domain."""
    allowed_domains = ROLE_ACCESS.get(user_role, [])
    return document_domain in allowed_domains


def _get_masking_patterns_for_role(user_role: str, domain: str) -> List[str]:
    """
    Determine which PII patterns to apply based on role and domain.
    
    Returns:
        List of pattern names to mask
    """
    # Admin: minimal masking
    if user_role == 'admin':
        return ['ssn', 'ssn_no_dash', 'credit_card', 'account_id']
    
    # Analyst in finance/HR: mask only critical PII
    if user_role == 'analyst' and domain in ['finance', 'hr']:
        return ['ssn', 'ssn_no_dash', 'credit_card']
    
    # Manager in HR: mask sensitive financial data too
    if user_role == 'manager' and domain == 'hr':
        return ['ssn', 'ssn_no_dash', 'credit_card', 'salary']
    
    # Default: aggressive masking for all others
    return list(PII_PATTERNS.keys())


def _apply_role_based_masking(doc: Dict[str, Any], user_role: str, domain: str) -> Dict[str, Any]:
    """Apply PII masking based on user role and document domain."""
    original_content = doc['content']
    patterns_to_mask = _get_masking_patterns_for_role(user_role, domain)
    
    masked_content = original_content
    for pattern_name in patterns_to_mask:
        if pattern_name in PII_PATTERNS:
            pattern, replacement = PII_PATTERNS[pattern_name]
            masked_content = re.sub(pattern, replacement, masked_content)
    
    if original_content != masked_content:
        doc['content'] = masked_content
        doc['pii_masked'] = True
        logger.info(f"🔒 PII masked in document: {doc.get('title', doc['id'])}")
    
    return doc


def validation_filter(
    doc: Dict[str, Any], 
    user_role: str,
    mask_pii: bool = True,
    log_violations: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Apply comprehensive validation and filtering to a document.
    
    This is the main validation function that:
    1. Checks role-based access control
    2. Detects sensitive terms
    3. Masks PII based on role and domain
    4. Returns validated document or None if access denied
    
    Args:
        doc: Document dictionary with 'content', 'domain', etc.
        user_role: Role of the requesting user
        mask_pii: Whether to mask PII in the content
        log_violations: Whether to log access violations
    
    Returns:
        Validated document dictionary or None if access denied
    """
    # Create a copy to avoid modifying original
    validated_doc = doc.copy()
    
    # Step 1: Role-based access control
    document_domain = doc.get('domain', 'public')
    if not check_access_permission(user_role, document_domain):
        log_access_attempt("user", user_role, document_domain, granted=False)
        if log_violations:
            logger.warning(f"🚫 Access denied: Role '{user_role}' cannot access '{document_domain}' domain")
        return None
    
    log_access_attempt("user", user_role, document_domain, granted=True)
    
    # Step 2: Detect sensitive terms
    sensitive_terms_found = detect_sensitive_terms(doc['content'])
    if sensitive_terms_found:
        validated_doc['sensitive_terms_detected'] = sensitive_terms_found
        logger.warning(f"⚠️  Sensitive terms detected: {', '.join(sensitive_terms_found)}")
        log_pii_detection(doc.get('id', 'unknown'), sensitive_terms_found)
    
    # Step 3: Role-aware PII Masking
    if mask_pii:
        validated_doc = _apply_role_based_masking(validated_doc, user_role, document_domain)
    
    # Step 4: Add validation metadata
    validated_doc['validated'] = True
    validated_doc['validator_version'] = '1.0'
    
    return validated_doc


def batch_validate(
    documents: List[Dict[str, Any]], 
    user_role: str,
    mask_pii: bool = True
) -> List[Dict[str, Any]]:
    """
    Validate a batch of documents.
    
    Args:
        documents: List of document dictionaries
        user_role: Role of the requesting user
        mask_pii: Whether to mask PII
    
    Returns:
        List of validated documents (excluding those denied access)
    """
    validated_docs = []
    denied_count = 0
    
    for doc in documents:
        validated = validation_filter(doc, user_role, mask_pii=mask_pii, log_violations=False)
        if validated:
            validated_docs.append(validated)
        else:
            denied_count += 1
    
    if denied_count > 0:
        logger.info(f"🚫 {denied_count} document(s) denied due to access restrictions")
    
    logger.info(f"✅ {len(validated_docs)} document(s) passed validation")
    
    return validated_docs


class ComplianceValidator:
    """
    Advanced compliance validator for specific regulatory frameworks.
    """
    
    def __init__(self, framework: str = "general"):
        """
        Initialize compliance validator.
        
        Args:
            framework: Compliance framework ('hipaa', 'gdpr', 'sox', 'general')
        """
        self.framework = framework
        self.rules = self._load_framework_rules()
    
    def _load_framework_rules(self) -> Dict[str, Any]:
        """Load compliance rules based on framework."""
        rules = {
            "hipaa": {
                "allowed_domains": ["health", "public"],
                "require_encryption": True,
                "mask_phi": True,
            },
            "gdpr": {
                "allowed_domains": ["public"],
                "require_consent": True,
                "data_minimization": True,
            },
            "sox": {
                "allowed_domains": ["finance", "public"],
                "audit_trail": True,
                "separation_of_duties": True,
            },
            "general": {
                "allowed_domains": ["public"],
                "basic_masking": True,
            }
        }
        return rules.get(self.framework, rules["general"])
    
    def validate(self, doc: Dict[str, Any], user_role: str) -> Optional[Dict[str, Any]]:
        """
        Validate document against compliance framework.
        
        Args:
            doc: Document to validate
            user_role: User role
        
        Returns:
            Validated document or None
        """
        # Apply framework-specific validation
        if doc.get('domain') not in self.rules.get('allowed_domains', []):
            logger.warning(f"🚫 Compliance violation: {self.framework} does not allow '{doc.get('domain')}' domain")
            return None
        
        # Apply standard validation
        return validation_filter(doc, user_role, mask_pii=True)

