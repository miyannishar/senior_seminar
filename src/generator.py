"""
Secure Generation Layer
Integrates retrieval and validation into a secure LLM-based generation pipeline
with comprehensive logging and traceability.
"""

import datetime
import json
from typing import Dict, Any, List, Tuple, Optional
from functools import wraps
import os

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from retriever import HybridRetriever
from validator import batch_validate
from utils.logger import setup_logger, log_query
from utils.config import get_config
from utils.exceptions import GenerationException
from constants import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = setup_logger(__name__)


# Logging storage (in production, use proper database or logging service)
INTERACTION_LOGS = []


def _print_interaction_summary(log_entry: Dict[str, Any]):
    """Print formatted interaction summary to console."""
    print("\n" + "="*80)
    print(f"📝 INTERACTION LOG")
    print(f"   User: {log_entry['user']} (Role: {log_entry['user_role']})")
    print(f"   Query: {log_entry['query']}")
    print(f"   Duration: {log_entry['duration_seconds']:.2f}s")
    print(f"   Sources: {len(log_entry['sources'])} documents")
    print(f"   Status: {log_entry['status'].upper()}")
    if log_entry.get('error'):
        print(f"   Error: {log_entry['error']}")
    print("="*80 + "\n")


def log_interaction(func):
    """Decorator to log all RAG system interactions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = kwargs.get("user", {})
        query = kwargs.get("query", "")
        start_time = datetime.datetime.now()
        
        try:
            response, sources, metadata = func(*args, **kwargs)
            status, error = "success", None
        except Exception as e:
            response, sources, metadata = f"Error: {str(e)}", [], {}
            status, error = "error", str(e)
        
        duration = (datetime.datetime.now() - start_time).total_seconds()
        
        log_entry = {
            "user": user.get("username", "anonymous"),
            "user_role": user.get("role", "guest"),
            "query": query,
            "timestamp": start_time.isoformat(),
            "response_preview": response[:200] + "..." if len(response) > 200 else response,
            "sources": sources,
            "metadata": metadata,
            "duration_seconds": duration,
            "status": status,
            "error": error
        }
        
        INTERACTION_LOGS.append(log_entry)
        _print_interaction_summary(log_entry)
        
        return response, sources, metadata
    
    return wrapper


def export_logs(filename: str = "interaction_logs.json"):
    """
    Export interaction logs to a JSON file.
    
    Args:
        filename: Output filename for logs
    """
    with open(filename, 'w') as f:
        json.dump(INTERACTION_LOGS, f, indent=2)
    print(f"📊 Exported {len(INTERACTION_LOGS)} logs to {filename}")


class SecureRAGGenerator:
    """
    Secure RAG generation system with validation and logging.
    """
    
    def __init__(
        self, 
        documents: List[Dict[str, Any]],
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7
    ):
        """
        Initialize the secure RAG generator.
        
        Args:
            documents: List of source documents
            model_name: OpenAI model to use
            temperature: LLM temperature (0-1)
        """
        self.retriever = HybridRetriever(documents)
        self.model_name = model_name
        self.temperature = temperature
        
        # Check API key
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("⚠️  OPENAI_API_KEY not set. Generation will fail.")
            logger.warning("   Set it with: export OPENAI_API_KEY='your-key-here'")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model_name=model_name,
                temperature=temperature
            )
        
        logger.info(f"✅ SecureRAGGenerator initialized with model: {model_name}")
    
    def _build_context(self, validated_docs: List[Dict[str, Any]]) -> str:
        """Build context string from validated documents."""
        context_parts = [
            f"[Document {i}: {doc.get('title', 'Untitled')}]\n{doc['content']}\n"
            for i, doc in enumerate(validated_docs, 1)
        ]
        return "\n".join(context_parts)
    
    def _extract_sources(self, validated_docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract source metadata from validated documents."""
        return [
            {
                "title": doc.get("title", "Untitled"),
                "id": doc["id"],
                "domain": doc.get("domain", "unknown")
            }
            for doc in validated_docs
        ]
    
    def _generate_llm_response(self, context: str, query: str) -> str:
        """Generate response using LLM."""
        if self.llm is None:
            return f"[Mock Response - API Key not set]\nContext available for query: '{query}'"
        
        user_prompt = USER_PROMPT_TEMPLATE.format(context=context, query=query)
        
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]
            return self.llm.invoke(messages).content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Error generating response: {str(e)}"
    
    @log_interaction
    def generate_secure_response(
        self, 
        query: str, 
        user: Dict[str, str],
        k: int = 5
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """Generate a secure response using RAG with validation."""
        # Retrieve and validate documents
        retrieved_docs = self.retriever.retrieve(query, k=k)
        user_role = user.get("role", "guest")
        validated_docs = batch_validate(retrieved_docs, user_role, mask_pii=True)
        
        if not validated_docs:
            return (
                "I couldn't find any information I'm authorized to share with you based on your access level.",
                [],
                {"documents_retrieved": len(retrieved_docs), "documents_after_validation": 0}
            )
        
        # Generate response
        context = self._build_context(validated_docs)
        response = self._generate_llm_response(context, query)
        sources = self._extract_sources(validated_docs)
        
        metadata = {
            "documents_retrieved": len(retrieved_docs),
            "documents_after_validation": len(validated_docs),
            "documents_denied": len(retrieved_docs) - len(validated_docs),
            "user_role": user_role,
            "model": self.model_name,
        }
        
        return response, sources, metadata
    
    def generate_with_compliance(
        self,
        query: str,
        user: Dict[str, str],
        compliance_framework: str = "general",
        k: int = 5
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """Generate response with specific compliance framework validation."""
        from validator import ComplianceValidator
        
        # Retrieve and validate with compliance framework
        retrieved_docs = self.retriever.retrieve(query, k=k)
        validator = ComplianceValidator(framework=compliance_framework)
        
        validated_docs = [
            validated for doc in retrieved_docs
            if (validated := validator.validate(doc, user.get("role", "guest")))
        ]
        
        logger.info(
            f"✅ Compliance validation ({compliance_framework}): "
            f"{len(validated_docs)}/{len(retrieved_docs)} documents approved"
        )
        
        if not validated_docs:
            return (
                f"No documents available that comply with {compliance_framework.upper()} "
                f"requirements for your access level.",
                [],
                {
                    "compliance_framework": compliance_framework,
                    "documents_retrieved": len(retrieved_docs),
                    "documents_compliant": 0
                }
            )
        
        # Generate response using helper methods
        context = self._build_context(validated_docs)
        response = self._generate_llm_response(context, query)
        sources = self._extract_sources(validated_docs)
        
        metadata = {
            "compliance_framework": compliance_framework,
            "documents_retrieved": len(retrieved_docs),
            "documents_compliant": len(validated_docs)
        }
        
        return response, sources, metadata





