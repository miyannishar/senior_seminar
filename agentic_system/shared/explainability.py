"""
Simple explainability tools for access decisions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from typing import Dict, Any, List
from constants.security import ROLE_ACCESS
from utils.logger import setup_logger

logger = setup_logger(__name__)


def explain_access_decision(user_role: str, document_domain: str, decision: str) -> str:
    """Explain why access was granted or denied."""
    allowed_domains = ROLE_ACCESS.get(user_role, [])
    
    if decision == "denied":
        alternative_roles = [role for role, domains in ROLE_ACCESS.items() if document_domain in domains]
        return (
            f"Access DENIED: Role '{user_role}' cannot access '{document_domain}' domain. "
            f"Your role allows: {', '.join(allowed_domains)}. "
            f"To access this domain, you need one of: {', '.join(alternative_roles)}"
        )
    else:
        return f"Access GRANTED: Role '{user_role}' has access to '{document_domain}' domain."


def create_explainability_tools(domain: str):
    """Create simple explainability tools for a domain."""
    
    def explain_why_denied(query: str, user_role: str) -> str:
        """Explain why access was denied."""
        allowed = ROLE_ACCESS.get(user_role, [])
        alternative_roles = [role for role, domains in ROLE_ACCESS.items() if domain in domains]
        
        return (
            f"Access DENIED for query: '{query}'\n"
            f"Your role '{user_role}' can only access: {', '.join(allowed)}\n"
            f"To access {domain} domain, you need: {', '.join(alternative_roles)}"
        )
    
    def explain_retrieval(query: str, docs_found: int, docs_shown: int) -> str:
        """Explain retrieval process."""
        denied = docs_found - docs_shown
        return (
            f"Query: '{query}'\n"
            f"Found {docs_found} documents, validated {docs_shown}, denied {denied} "
            f"based on your role permissions."
        )
    
    return explain_why_denied, explain_retrieval
