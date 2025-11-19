"""
Base/Orchestrator Agent - Routes queries to domain-specific agents.
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

from agentic_system.base.prompt import BASE_AGENT_FULL
from agentic_system.utils.llm import get_powerful_llm
from agentic_system.shared.before_agent_callback import create_before_agent_callback
from agentic_system.financial.agent import create_financial_agent
from agentic_system.hr.agent import create_hr_agent
from agentic_system.health.agent import create_health_agent
from agentic_system.law.agent import create_law_agent
from retriever import HybridRetriever
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)


def create_trustworthy_rag_agent(api_key: Optional[str] = None) -> LlmAgent:
    """
    Create the Trustworthy RAG orchestrator agent using Google ADK.
    
    This agent routes queries to domain-specific agents:
    - Financial agent (financial performance queries)
    - HR agent (HR and benefits queries)
    - Health agent (healthcare and HIPAA compliance queries)
    - Law agent (legal and compliance queries)
    
    Args:
        api_key: OpenAI API key (optional, uses env variable if not provided)
    
    Returns:
        LlmAgent: Configured root orchestrator agent
    """
    logger.info("=" * 60)
    logger.info("🚀 Creating Trustworthy RAG Agentic System with Domain Agents")
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
    
    # Create domain agents
    logger.info("🤖 Creating domain-specific agents...")
    
    financial_agent = create_financial_agent(retriever, api_key=api_key)
    logger.info("  ✅ Financial agent ready (with guardrails)")
    
    hr_agent = create_hr_agent(retriever, api_key=api_key)
    logger.info("  ✅ HR agent ready (with guardrails)")
    
    health_agent = create_health_agent(retriever, api_key=api_key)
    logger.info("  ✅ Health agent ready (with guardrails)")
    
    law_agent = create_law_agent(retriever, api_key=api_key)
    logger.info("  ✅ Law agent ready (with guardrails)")
    
    # Create root orchestrator with sub-agents
    logger.info("🎭 Creating base orchestrator agent with sub-agents...")
    
    root_model = get_powerful_llm(api_key=api_key)
    before_agent_callback = create_before_agent_callback(domain="base", default_role="employee")
    
    # Create root orchestrator with before_agent_callback
    root_agent = LlmAgent(
        name="trustworthy_rag_agent",
        model=root_model,
        description=(
            "Enterprise Trustworthy RAG orchestrator with domain-specific sub-agents "
            "and role-based access control"
        ),
        instruction=BASE_AGENT_FULL,
        sub_agents=[
            financial_agent,
            hr_agent,
            health_agent,
            law_agent
        ],
        before_agent_callback=before_agent_callback
    )
    
    logger.info("=" * 60)
    logger.info("✅ Trustworthy RAG Agent System Ready!")
    logger.info("=" * 60)
    logger.info("Domain Agents:")
    logger.info("  💰 Financial Agent")
    logger.info("  👥 HR Agent")
    logger.info("  🏥 Health Agent")
    logger.info("  ⚖️  Law Agent")
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
