"""
Shared RAG tools for all domain agents.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from typing import Dict, Any, List
from retriever import HybridRetriever
from validator import check_access_permission, validation_filter, mask_sensitive_data
from agentic_system.shared.role_mapping import get_role_for_access
from agentic_system.shared.explainability import create_explainability_tools
from agentic_system.shared.audit import get_audit_logger
from agentic_system.shared.security_monitor import get_security_monitor
from agentic_system.shared.guardrails import get_guardrails
from utils.logger import setup_logger

logger = setup_logger(__name__)

audit_logger = get_audit_logger()
security_monitor = get_security_monitor()
guardrails = get_guardrails()


def create_rag_tools(retriever: HybridRetriever, domain: str):
    """Create RAG tools for a domain."""
    logger.info(f"✅ RAG tools initialized for domain: {domain}")
    
    explain_why_denied, explain_retrieval = create_explainability_tools(domain)
    
    def check_access(department_role: str, **kwargs) -> bool:
        """Check if user has access to domain."""
        document_domain = kwargs.get('document_domain', domain)
        
        general_role = get_role_for_access(domain, department_role)
        allowed = check_access_permission(general_role, document_domain)
        
        audit_logger.log_access_attempt(
            user="current_user",
            user_role=general_role,
            domain=document_domain,
            decision="granted" if allowed else "denied"
        )
        
        # Create security alert if access denied
        if not allowed:
            reason = f"Role '{general_role}' (from department role '{department_role}') does not have access to '{document_domain}' domain"
            security_monitor.record_access_denial(
                user="current_user",
                session_id=kwargs.get('session_id', 'unknown'),
                domain=document_domain,
                role=general_role,
                query=kwargs.get('query', ''),
                reason=reason
            )
        
        return allowed
    
    def retrieve_and_validate(query: str, department_role: str, k: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Retrieve and validate documents."""
        logger.info("=" * 60)
        logger.info(f"🔍 TOOL CALLED: retrieve_and_validate")
        logger.info(f"   Domain: {domain}")
        logger.info(f"   Query: {query[:200]}...")
        logger.info(f"   Department Role: {department_role}")
        logger.info("=" * 60)
        
        if not query or not department_role:
            raise ValueError("query and department_role required")
        
        general_role = get_role_for_access(domain, department_role)
        
        # Check domain access first - create alert if denied
        if not check_access_permission(general_role, domain):
            reason = f"Role '{general_role}' (from department role '{department_role}') does not have access to '{domain}' domain"
            security_monitor.record_access_denial(
                user="current_user",
                session_id=kwargs.get('session_id', 'unknown'),
                domain=domain,
                role=general_role,
                query=query,
                reason=reason
            )
            audit_logger.log_access_attempt("current_user", general_role, domain, "denied")
            return []  # Return empty - access denied
        
        # Guardrail check - THIS IS WHERE VALIDATION HAPPENS
        logger.info(f"🛡️  Running guardrail validation for domain '{domain}'...")
        is_safe, violation = guardrails.validate_input(query, "current_user", general_role, domain)
        if not is_safe:
            logger.critical("=" * 60)
            logger.critical("🚨 INPUT BLOCKED BY GUARDRAILS IN TOOL")
            logger.critical(f"   Violation: {violation.get('description', 'Unknown')}")
            logger.critical(f"   Type: {violation.get('violation_type', 'UNKNOWN')}")
            logger.critical(f"   Severity: {violation.get('severity', 'UNKNOWN')}")
            logger.critical("=" * 60)
            return []
        
        # Retrieve documents
        try:
            all_results = retriever.retrieve(query=query, k=k * 2)
        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            return []
        
        # Filter by domain
        domain_results = [doc for doc in all_results if doc.get('domain') == domain]
        if not domain_results:
            domain_results = [doc for doc in all_results if doc.get('domain') == 'public']
        
        # Validate access
        validated_docs = []
        for doc in domain_results:
            doc_domain = doc.get('domain', 'public')
            if not check_access_permission(general_role, doc_domain):
                audit_logger.log_access_attempt("current_user", general_role, doc_domain, "denied")
                reason = f"Role '{general_role}' (from department role '{department_role}') attempted to access document in '{doc_domain}' domain"
                security_monitor.record_access_denial(
                    user="current_user",
                    session_id=kwargs.get('session_id', 'unknown'),
                    domain=doc_domain,
                    role=general_role,
                    query=query,
                    reason=reason
                )
                continue
            
            validated = validation_filter(doc, user_role=general_role, mask_pii=True, log_violations=True)
            if validated:
                validated_docs.append(validated)
        
        audit_logger.log_query("current_user", general_role, query, domain, len(all_results), len(validated_docs))
        
        return validated_docs[:k]
    
    def extract_info(**kwargs) -> Dict[str, Any]:
        """Extract info from validated documents."""
        validated_documents = kwargs.get('validated_documents') or kwargs.get('documents') or []
        
        if not validated_documents:
            return {"context": "", "sources": [], "document_count": 0, "domain": domain}
        
        context_parts = []
        sources = []
        for doc in validated_documents:
            if isinstance(doc, dict):
                context_parts.append(f"[{doc.get('title', 'Untitled')}]\n{doc.get('content', '')}\n")
                sources.append({"title": doc.get("title", "Untitled"), "id": doc.get("id", "unknown")})
        
        return {
            "context": "\n".join(context_parts),
            "sources": sources,
            "document_count": len(validated_documents),
            "domain": domain
        }
    
    def mask_pii_for_role(text: str, department_role: str = "employee", **kwargs) -> str:
        """Mask PII in text."""
        
        general_role = get_role_for_access(domain, department_role)
        aggressive = general_role not in ['admin', 'analyst']
        return mask_sensitive_data(text, aggressive=aggressive)
        
    def explain_decision(query: str, user_role: str = "employee", decision_type: str = "access", **kwargs) -> str:
        """Explain a decision."""
        
        if decision_type == "access":
            return explain_why_denied(query, user_role)
        elif decision_type == "retrieval":
            return explain_retrieval(query, kwargs.get('documents_found', 0), kwargs.get('documents_shown', 0))
        return f"Decision explanation for {decision_type}"
    
    def get_compliance_report(framework: str = "general", **kwargs) -> Dict[str, Any]:
        """Get compliance report."""
        return audit_logger.get_compliance_report(framework=framework)
    
    def get_security_alerts(**kwargs) -> List[Dict[str, Any]]:
        """Get security alerts."""
        severity = kwargs.get('severity')
        return security_monitor.get_alerts(severity=severity)
    
    return (
        check_access,
        retrieve_and_validate,
        extract_info,
        mask_pii_for_role,
        explain_decision,
        get_compliance_report,
        get_security_alerts
    )
