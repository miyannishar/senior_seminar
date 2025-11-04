"""
Retrieval tools for the Trustworthy RAG agentic system.
Standalone functions for document retrieval.
"""

import sys
import os

# Add src to path to import existing modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from typing import Dict, Any, List

from retriever import HybridRetriever
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_retrieval_tools(retriever: HybridRetriever):
    """
    Create retrieval tool functions bound to a retriever instance.
    
    Args:
        retriever: HybridRetriever instance with documents loaded
    
    Returns:
        Tuple of tool functions: (retrieve_documents, retrieve_by_domain, get_retriever_stats)
    """
    logger.info("✅ Retrieval tools initialized")
    
    def retrieve_documents(
        query: str = None,
        k: int = 5,
        semantic_weight: float = 0.7,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents using hybrid search.
        
        Args:
            query: Search query (required)
            k: Number of documents to retrieve
            semantic_weight: Weight for semantic search (0-1)
        
        Returns:
            List of retrieved documents with relevance scores
        """
        # Handle ADK function calling format
        if query is None and 'query' in kwargs:
            query = kwargs['query']
        if query is None:
            raise ValueError("query parameter is required")
            
        logger.info(f"🔍 Retrieving documents for query: '{query[:50]}...'")
        
        try:
            results = retriever.retrieve(
                query=query,
                k=k,
                semantic_weight=semantic_weight
            )
            
            logger.info(f"✅ Retrieved {len(results)} documents")
            return results
            
        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            return []
    
    def retrieve_by_domain(
        query: str = None,
        domain: str = None,
        k: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents filtered by domain.
        
        Args:
            query: Search query (required)
            domain: Domain to filter by (finance, hr, health, legal, public) (required)
            k: Number of documents to retrieve
        
        Returns:
            List of retrieved documents from specified domain
        """
        # Handle ADK function calling format
        if query is None and 'query' in kwargs:
            query = kwargs['query']
        if domain is None and 'domain' in kwargs:
            domain = kwargs['domain']
        if query is None or domain is None:
            raise ValueError("query and domain parameters are required")
            
        logger.info(f"🔍 Retrieving {domain} documents for: '{query[:50]}...'")
        
        try:
            results = retriever.retrieve_by_domain(
                query=query,
                domain=domain,
                k=k
            )
            
            logger.info(f"✅ Retrieved {len(results)} documents from {domain}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Domain retrieval failed: {e}")
            return []
    
    def get_retriever_stats(**kwargs) -> Dict[str, Any]:
        """
        Get retriever statistics and health information.
        
        Returns:
            Dictionary with retriever stats
        """
        try:
            stats = retriever.get_stats()
            logger.info("📊 Retrieved system stats")
            return stats
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {"error": str(e)}
    
    return retrieve_documents, retrieve_by_domain, get_retriever_stats
