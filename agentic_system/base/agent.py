"""
Root/Base Agent - Trustworthy RAG Orchestrator using Google ADK.
Coordinates retrieval, security, compliance, and response agents.
"""

import sys
import os
import json
from typing import Optional
from dotenv import load_dotenv

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from agentic_system.base.prompt import ROOT_AGENT_FULL
from agentic_system.utils.llm import get_powerful_llm
from agentic_system.retrieval.agent import create_retrieval_agent
from agentic_system.security.agent import create_security_agent
from agentic_system.compliance.agent import create_compliance_agent
from agentic_system.response.agent import create_response_agent
from retriever import HybridRetriever
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)


def create_trustworthy_rag_agent(api_key: Optional[str] = None) -> LlmAgent:
    """
    Create the Trustworthy RAG orchestrator agent using Google ADK.
    
    This agent coordinates:
    - Retrieval agent (finds documents)
    - Security agent (validates and masks)
    - Compliance agent (checks regulatory compliance)
    - Response agent (generates answers)
    
    Args:
        api_key: OpenAI API key (optional, uses env variable if not provided)
    
    Returns:
        LlmAgent: Configured root orchestrator agent
    """
    logger.info("=" * 60)
    logger.info("🚀 Creating Trustworthy RAG Agentic System with Google ADK")
    logger.info("=" * 60)
    
    # Load documents
    data_path = os.path.join(
        os.path.dirname(__file__),
        "../../data/expanded_docs.json"
    )
    
    logger.info(f"📚 Loading documents from: {data_path}")
    
    try:
        with open(data_path, 'r') as f:
            documents = json.load(f)
        logger.info(f"✅ Loaded {len(documents)} documents")
    except FileNotFoundError:
        logger.error(f"❌ Document file not found: {data_path}")
        raise
    
    # Initialize retriever (Pinecone/FAISS + TF-IDF)
    logger.info("🔧 Initializing hybrid retriever...")
    retriever = HybridRetriever(
        documents=documents,
        use_pinecone=True,
        pinecone_index_name="seniorseminar",
        pinecone_namespace="default"
    )
    
    # Create specialized agents
    logger.info("🤖 Creating specialized sub-agents...")
    
    retrieval_agent = create_retrieval_agent(retriever, api_key=api_key)
    logger.info("  ✅ Retrieval agent ready")
    
    security_agent = create_security_agent(api_key=api_key)
    logger.info("  ✅ Security agent ready")
    
    compliance_agent = create_compliance_agent(api_key=api_key)
    logger.info("  ✅ Compliance agent ready")
    
    response_agent = create_response_agent(api_key=api_key)
    logger.info("  ✅ Response agent ready")
    
    # Create root orchestrator
    logger.info("🎭 Creating root orchestrator agent...")
    
    root_model = get_powerful_llm(api_key=api_key)
    
    # Wrap sub-agents with AgentTool for proper ADK integration
    retrieval_agent_tool = AgentTool(agent=retrieval_agent)
    security_agent_tool = AgentTool(agent=security_agent)
    compliance_agent_tool = AgentTool(agent=compliance_agent)
    response_agent_tool = AgentTool(agent=response_agent)
    
    root_agent = LlmAgent(
        name="trustworthy_rag_agent",
        model=root_model,
        description=(
            "Enterprise Trustworthy RAG orchestrator with privacy, "
            "security, and compliance built-in"
        ),
        instruction=ROOT_AGENT_FULL,
        tools=[
            retrieval_agent_tool,
            security_agent_tool,
            compliance_agent_tool,
            response_agent_tool
        ]
    )
    
    logger.info("=" * 60)
    logger.info("✅ Trustworthy RAG Agent System Ready!")
    logger.info("=" * 60)
    logger.info("Capabilities:")
    logger.info("  🔍 Hybrid retrieval (Pinecone + TF-IDF)")
    logger.info("  🔒 RBAC & PII masking")
    logger.info("  ⚖️  Compliance validation (HIPAA, GDPR, SOX)")
    logger.info("  📝 High-quality response generation")
    logger.info("  🤖 Multi-agent orchestration")
    logger.info("=" * 60)
    
    return root_agent


# Lazy initialization - don't create at import time
# Google ADK will initialize when needed
trustworthy_rag_agent = None

def get_trustworthy_rag_agent(api_key: Optional[str] = None) -> LlmAgent:
    """
    Get or create the trustworthy RAG agent.
    Lazy initialization for Google ADK web UI.
    
    Args:
        api_key: OpenAI API key (optional)
    
    Returns:
        LlmAgent: The root orchestrator agent
    """
    global trustworthy_rag_agent
    if trustworthy_rag_agent is None:
        trustworthy_rag_agent = create_trustworthy_rag_agent(api_key=api_key)
    return trustworthy_rag_agent

