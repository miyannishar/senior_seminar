"""
Retrieval Agent for finding relevant documents.
Uses Google ADK with retrieval tools.
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from typing import Optional
from google.adk.agents import LlmAgent

from agentic_system.retrieval.prompt import RETRIEVAL_AGENT_FULL
from agentic_system.retrieval.tools import create_retrieval_tools
from agentic_system.utils.llm import get_standard_llm
from retriever import HybridRetriever
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_retrieval_agent(
    retriever: HybridRetriever,
    api_key: Optional[str] = None
) -> LlmAgent:
    """
    Create the retrieval agent for document search.
    
    Args:
        retriever: HybridRetriever instance with documents loaded
        api_key: OpenAI API key (optional, uses env variable if not provided)
    
    Returns:
        LlmAgent configured for document retrieval
    """
    logger.info("🔨 Creating retrieval agent...")
    
    # Create LLM
    llm = get_standard_llm(api_key=api_key)
    
    # Create tool functions bound to retriever
    retrieve_documents, retrieve_by_domain, get_retriever_stats = create_retrieval_tools(retriever)
    
    # Create agent - ADK will auto-convert functions to tools
    agent = LlmAgent(
        name="retrieval_agent",
        model=llm,
        description="Finds relevant documents using hybrid search (Pinecone + TF-IDF)",
        instruction=RETRIEVAL_AGENT_FULL,
        tools=[retrieve_documents, retrieve_by_domain, get_retriever_stats]
    )
    
    logger.info("✅ Retrieval agent created")
    return agent
