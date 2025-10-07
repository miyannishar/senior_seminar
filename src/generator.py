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


# Logging storage (in production, use proper database or logging service)
INTERACTION_LOGS = []


def log_interaction(func):
    """
    Decorator to log all interactions with the RAG system.
    Captures query, response, sources, timing, and metadata.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = kwargs.get("user", {})
        query = kwargs.get("query", "")
        
        start_time = datetime.datetime.now()
        
        try:
            response, sources, metadata = func(*args, **kwargs)
            status = "success"
            error = None
        except Exception as e:
            response = f"Error: {str(e)}"
            sources = []
            metadata = {}
            status = "error"
            error = str(e)
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
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
        
        # Print formatted log
        print("\n" + "="*80)
        print(f"📝 INTERACTION LOG")
        print(f"   User: {log_entry['user']} (Role: {log_entry['user_role']})")
        print(f"   Query: {query}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Sources: {len(sources)} documents")
        print(f"   Status: {status.upper()}")
        if error:
            print(f"   Error: {error}")
        print("="*80 + "\n")
        
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
            print("⚠️  Warning: OPENAI_API_KEY not set. Generation will fail.")
            print("   Set it with: export OPENAI_API_KEY='your-key-here'")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model_name=model_name,
                temperature=temperature
            )
        
        print(f"✅ SecureRAGGenerator initialized with model: {model_name}")
    
    @log_interaction
    def generate_secure_response(
        self, 
        query: str, 
        user: Dict[str, str],
        k: int = 5
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Generate a secure response using RAG with validation.
        
        Args:
            query: User query
            user: User dictionary with 'username' and 'role'
            k: Number of documents to retrieve
        
        Returns:
            Tuple of (response, sources, metadata)
        """
        # Step 1: Retrieve relevant documents
        retrieved_docs = self.retriever.retrieve(query, k=k)
        
        # Step 2: Validate and filter documents based on user role
        user_role = user.get("role", "guest")
        validated_docs = batch_validate(retrieved_docs, user_role, mask_pii=True)
        
        if not validated_docs:
            return (
                "I couldn't find any information I'm authorized to share with you based on your access level.",
                [],
                {"documents_retrieved": len(retrieved_docs), "documents_after_validation": 0}
            )
        
        # Step 3: Prepare context from validated documents
        context_parts = []
        for i, doc in enumerate(validated_docs, 1):
            context_parts.append(f"[Document {i}: {doc.get('title', 'Untitled')}]\n{doc['content']}\n")
        
        context = "\n".join(context_parts)
        
        # Step 4: Generate response using LLM
        if self.llm is None:
            response = f"[Mock Response - API Key not set]\nBased on {len(validated_docs)} validated documents, I would answer your query: '{query}'"
        else:
            system_prompt = """You are a secure AI assistant with access to verified, filtered enterprise documents.
Your responses must:
1. Only use information from the provided context
2. Never fabricate or guess information
3. Cite which documents you used
4. Respect data sensitivity (some information may be masked)
5. Be clear, concise, and professional"""
            
            user_prompt = f"""Using ONLY the verified context below, answer the question.

Context:
{context}

Question: {query}

Provide a clear answer based solely on the context. If the context doesn't contain enough information, say so."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            try:
                response = self.llm.invoke(messages).content
            except Exception as e:
                response = f"Error generating response: {str(e)}"
        
        # Step 5: Extract sources
        sources = [
            {
                "title": doc.get("title", "Untitled"),
                "id": doc["id"],
                "domain": doc.get("domain", "unknown")
            }
            for doc in validated_docs
        ]
        
        # Step 6: Metadata for observability
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
        """
        Generate response with specific compliance framework validation.
        
        Args:
            query: User query
            user: User dictionary
            compliance_framework: Framework to apply ('hipaa', 'gdpr', 'sox', 'general')
            k: Number of documents to retrieve
        
        Returns:
            Tuple of (response, sources, metadata)
        """
        from validator import ComplianceValidator
        
        # Retrieve documents
        retrieved_docs = self.retriever.retrieve(query, k=k)
        
        # Apply compliance-specific validation
        validator = ComplianceValidator(framework=compliance_framework)
        validated_docs = []
        
        for doc in retrieved_docs:
            validated = validator.validate(doc, user.get("role", "guest"))
            if validated:
                validated_docs.append(validated)
        
        print(f"✅ Compliance validation ({compliance_framework}): {len(validated_docs)}/{len(retrieved_docs)} documents approved")
        
        if not validated_docs:
            return (
                f"No documents available that comply with {compliance_framework.upper()} requirements for your access level.",
                [],
                {
                    "compliance_framework": compliance_framework,
                    "documents_retrieved": len(retrieved_docs),
                    "documents_compliant": 0
                }
            )
        
        # Generate response (reuse logic)
        # [Similar to generate_secure_response, abbreviated for brevity]
        context = "\n".join([f"{doc.get('title', 'Doc')}: {doc['content']}" for doc in validated_docs])
        
        if self.llm:
            prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer based only on context:"
            response = self.llm.invoke([HumanMessage(content=prompt)]).content
        else:
            response = f"[Compliance-aware response using {len(validated_docs)} {compliance_framework}-compliant documents]"
        
        sources = [{"title": doc.get("title"), "id": doc["id"]} for doc in validated_docs]
        metadata = {
            "compliance_framework": compliance_framework,
            "documents_retrieved": len(retrieved_docs),
            "documents_compliant": len(validated_docs)
        }
        
        return response, sources, metadata





