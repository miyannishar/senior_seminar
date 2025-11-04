"""
Response generation tools for the Response Agent.
Standalone functions for response generation.
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from typing import Dict, Any, List
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_response_tools():
    """
    Create response generation tool functions.
    
    Returns:
        Tuple of tool functions: (generate_response, extract_sources)
    """
    logger.info("✅ Response tools initialized")
    
    def generate_response(
        query: str = None,
        validated_documents: List[Dict[str, Any]] = None,
        user_role: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from validated documents.
        
        Args:
            query: User's query (required)
            validated_documents: List of validated documents (required)
            user_role: User's role (required)
        
        Returns:
            Dict with response, sources, and metadata
        """
        # Handle ADK function calling format
        if query is None and 'query' in kwargs:
            query = kwargs['query']
        if validated_documents is None and 'validated_documents' in kwargs:
            validated_documents = kwargs['validated_documents']
        if user_role is None and 'user_role' in kwargs:
            user_role = kwargs['user_role']
        if query is None or validated_documents is None or user_role is None:
            raise ValueError("query, validated_documents, and user_role parameters are required")
            
        logger.info(f"📝 Generating response for query: '{query[:50]}...'")
        
        if not validated_documents:
            return {
                "response": (
                    "I couldn't find any information I'm authorized to share "
                    "with you based on your access level."
                ),
                "sources": [],
                "metadata": {
                    "documents_available": 0,
                    "user_role": user_role
                }
            }
        
        # Build context from validated documents
        context_parts = []
        for i, doc in enumerate(validated_documents, 1):
            context_parts.append(
                f"[Document {i}: {doc.get('title', 'Untitled')} (ID: {doc['id']})]\n"
                f"{doc['content']}\n"
            )
        
        context = "\n".join(context_parts)
        
        # Extract sources
        sources = [
            {
                "title": doc.get("title", "Untitled"),
                "id": doc["id"],
                "domain": doc.get("domain", "unknown")
            }
            for doc in validated_documents
        ]
        
        return {
            "response": f"Context available with {len(validated_documents)} documents",
            "sources": sources,
            "context": context,
            "metadata": {
                "documents_available": len(validated_documents),
                "user_role": user_role
            }
        }
    
    def extract_sources(
        documents: List[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, str]]:
        """
        Extract source metadata from documents.
        
        Args:
            documents: List of documents (required)
        
        Returns:
            List of source metadata
        """
        # Handle ADK function calling format
        if documents is None and 'documents' in kwargs:
            documents = kwargs['documents']
        if documents is None:
            raise ValueError("documents parameter is required")
            
        return [
            {
                "title": doc.get("title", "Untitled"),
                "id": doc["id"],
                "domain": doc.get("domain", "unknown")
            }
            for doc in documents
        ]
    
    return generate_response, extract_sources
