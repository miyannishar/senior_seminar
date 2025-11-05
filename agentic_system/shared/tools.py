"""
Shared RAG tools for all domain agents.
These tools validate access DETERMINISTICALLY before allowing any data to reach the LLM.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from typing import Dict, Any, List, Optional

from retriever import HybridRetriever
from validator import (
    check_access_permission,
    validation_filter,
    batch_validate,
    mask_sensitive_data,
    detect_sensitive_terms
)
from agentic_system.shared.role_mapping import get_role_for_access
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_rag_tools(retriever: HybridRetriever, domain: str):
    """
    Create RAG tools bound to a retriever and domain.
    These tools validate access deterministically before extraction.
    
    Args:
        retriever: HybridRetriever instance
        domain: Document domain (finance, hr, health, legal, public)
    
    Returns:
        Tuple of tool functions: (check_access, retrieve_and_validate, extract_info)
    """
    logger.info(f"✅ RAG tools initialized for domain: {domain}")
    
    def check_access(department_role: str, document_domain: Optional[str] = None, **kwargs) -> bool:
        """
        Check if user has access to a domain. DETERMINISTIC - no LLM involved.
        
        Maps department-specific roles (e.g., "manager" in finance) to general roles
        for access control checking.
        
        Args:
            department_role: User's role within the department (e.g., "manager", "employee")
            document_domain: Domain to check (defaults to agent's domain)
        
        Returns:
            True if access allowed, False otherwise
        """
        if document_domain is None and 'document_domain' in kwargs:
            document_domain = kwargs['document_domain']
        if document_domain is None:
            document_domain = domain
        
        # Map department role to general role for access control
        general_role = get_role_for_access(domain, department_role)
        
        allowed = check_access_permission(general_role, document_domain)
        logger.info(f"🔑 Access check: {department_role} ({domain}) -> {general_role} -> {document_domain}: {allowed}")
        return allowed
    
    def retrieve_and_validate(
        query: Optional[str] = None,
        department_role: Optional[str] = None,
        k: int = 5,
        semantic_weight: float = 0.7,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents and validate access DETERMINISTICALLY before returning.
        This ensures unauthorized PII never reaches the LLM.
        
        Steps:
        1. Retrieve documents using hybrid search
        2. Filter by domain
        3. Map department role to general role
        4. Check access permission for each document (deterministic)
        5. Mask PII according to role (deterministic)
        6. Return only validated, masked documents
        
        Args:
            query: Search query (required)
            department_role: User's role within the department (e.g., "manager", "employee") (required)
            k: Number of documents to retrieve
            semantic_weight: Weight for semantic search (0-1)
        
        Returns:
            List of validated, masked documents (unauthorized ones filtered out)
        """
        # Handle ADK function calling format
        if query is None and 'query' in kwargs:
            query = kwargs['query']
        if department_role is None and 'department_role' in kwargs:
            department_role = kwargs['department_role']
        if query is None or department_role is None:
            raise ValueError("query and department_role parameters are required")
        
        # Map department role to general role for access control
        general_role = get_role_for_access(domain, department_role)
        
        logger.info(f"🔍 Retrieving and validating documents for: '{query[:50]}...' (role: {department_role} -> {general_role})")
        
        # Step 1: Retrieve documents using hybrid search
        try:
            all_results = retriever.retrieve(
                query=query,
                k=k * 2,  # Get more to account for filtering
                semantic_weight=semantic_weight
            )
            logger.info(f"📚 Retrieved {len(all_results)} documents")
        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            return []
        
        # Step 2: Filter by domain
        domain_mapping = {
            'financial': 'finance',   # Financial queries use finance domain documents
        }
        search_domain = domain_mapping.get(domain, domain)
        
        domain_results = [doc for doc in all_results if doc.get('domain') == search_domain]
        if not domain_results:
            logger.warning(f"⚠️  No documents found in {search_domain} domain")
            # Fallback to public domain
            domain_results = [doc for doc in all_results if doc.get('domain') == 'public']
        
        # Step 3: Validate access DETERMINISTICALLY (before LLM sees anything)
        validated_docs = []
        denied_count = 0
        
        for doc in domain_results:
            # Check access first (deterministic) - use the actual document domain
            # Use general_role (mapped from department_role) for access control
            doc_domain = doc.get('domain', 'public')
            if not check_access_permission(general_role, doc_domain):
                denied_count += 1
                logger.warning(f"🚫 Access denied: {department_role} ({general_role}) cannot access {doc_domain} document: {doc.get('id')}")
                continue
            
            # Validate and mask PII (deterministic) - this happens BEFORE LLM sees data
            # Use general_role for validation (matches ROLE_ACCESS mapping)
            validated = validation_filter(
                doc=doc,
                user_role=general_role,
                mask_pii=True,
                log_violations=True
            )
            
            if validated:
                validated_docs.append(validated)
            else:
                denied_count += 1
        
        logger.info(f"✅ Validated: {len(validated_docs)}, Denied: {denied_count}")
        
        # Return top k validated documents
        return validated_docs[:k]
    
    def extract_info(
        validated_documents: Optional[List[Dict[str, Any]]] = None,
        query: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract information from validated documents.
        This is called AFTER validation, so all documents are already clean.
        
        Note: You should first call retrieve_and_validate to get validated documents,
        then pass those documents to this function.
        
        Args:
            validated_documents: List of validated, masked documents from retrieve_and_validate (required)
            query: Original query for context
        
        Returns:
            Dict with extracted information, sources, and metadata
        """
        # Handle ADK function calling format - check multiple possible parameter names
        if validated_documents is None:
            validated_documents = kwargs.get('validated_documents') or kwargs.get('documents') or kwargs.get('docs')
        
        if validated_documents is None:
            logger.warning("⚠️  extract_info called without validated_documents. Please call retrieve_and_validate first.")
            return {
                "context": "",
                "sources": [],
                "document_count": 0,
                "domain": domain,
                "error": "No validated documents provided. Please call retrieve_and_validate first to get documents."
            }
        
        # Ensure it's a list
        if not isinstance(validated_documents, list):
            logger.warning(f"⚠️  validated_documents is not a list: {type(validated_documents)}")
            return {
                "context": "",
                "sources": [],
                "document_count": 0,
                "domain": domain,
                "error": "validated_documents must be a list"
            }
        
        logger.info(f"📝 Extracting info from {len(validated_documents)} validated documents")
        
        # Build context from validated documents
        context_parts = []
        sources = []
        
        for doc in validated_documents:
            if not isinstance(doc, dict):
                continue
            context_parts.append(
                f"[Document: {doc.get('title', 'Untitled')} (ID: {doc.get('id', 'unknown')})]\n"
                f"{doc.get('content', '')}\n"
            )
            sources.append({
                "title": doc.get("title", "Untitled"),
                "id": doc.get("id", "unknown"),
                "domain": doc.get("domain", "unknown")
            })
        
        context = "\n".join(context_parts)
        
        return {
            "context": context,
            "sources": sources,
            "document_count": len(validated_documents),
            "domain": domain
        }
    
    def mask_pii_for_role(
        text: Optional[str] = None,
        department_role: Optional[str] = None,
        document_domain: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Mask PII in text according to role and domain.
        DETERMINISTIC - no LLM involved.
        
        Args:
            text: Text to mask (required)
            department_role: User's role within the department (required)
            document_domain: Document domain (defaults to agent's domain)
        
        Returns:
            Text with PII masked according to role
        """
        if text is None and 'text' in kwargs:
            text = kwargs['text']
        if department_role is None and 'department_role' in kwargs:
            department_role = kwargs['department_role']
        if text is None or department_role is None:
            raise ValueError("text and department_role parameters are required")
        
        if document_domain is None:
            document_domain = domain
        
        # Map department role to general role
        general_role = get_role_for_access(domain, department_role)
        
        # Determine masking aggressiveness based on role
        aggressive = general_role not in ['admin', 'analyst']
        
        masked = mask_sensitive_data(text, aggressive=aggressive)
        
        if masked != text:
            logger.info(f"🔒 PII masked for role: {department_role} ({general_role})")
        
        return masked
    
    return check_access, retrieve_and_validate, extract_info, mask_pii_for_role

