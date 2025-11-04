"""
Law/Legal Agent for legal and compliance queries.
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from typing import Optional
from google.adk.agents import LlmAgent

from agentic_system.law.prompt import LAW_AGENT_FULL
from agentic_system.shared.tools import create_rag_tools
from agentic_system.utils.llm import get_standard_llm
from retriever import HybridRetriever
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_law_agent(
    retriever: HybridRetriever,
    api_key: Optional[str] = None
) -> LlmAgent:
    """
    Create the law/legal agent.
    
    Args:
        retriever: HybridRetriever instance
        api_key: OpenAI API key (optional)
    
    Returns:
        LlmAgent configured for legal queries
    """
    logger.info("🔨 Creating law agent...")
    
    # Create LLM
    llm = get_standard_llm(api_key=api_key)
    
    # Create RAG tools bound to retriever and legal domain
    check_access, retrieve_and_validate, extract_info, mask_pii_for_role = create_rag_tools(
        retriever=retriever,
        domain="legal"
    )
    
    # Create agent - ADK will auto-convert functions to tools
    agent = LlmAgent(
        name="law_agent",
        model=llm,
        description="Handles legal and compliance queries with role-based access control",
        instruction=LAW_AGENT_FULL,
        tools=[check_access, retrieve_and_validate, extract_info, mask_pii_for_role]
    )
    
    logger.info("✅ Law agent created")
    return agent

