"""
Law Agent for legal queries.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from typing import Optional
from google.adk.agents import LlmAgent
from agentic_system.law.prompt import LAW_AGENT_FULL
from agentic_system.shared.tools import create_rag_tools
from agentic_system.shared.before_agent_callback import create_before_agent_callback
from agentic_system.utils.llm import get_standard_llm
from retriever import HybridRetriever
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_law_agent(retriever: HybridRetriever, api_key: Optional[str] = None) -> LlmAgent:
    """Create law agent."""
    logger.info("🔨 Creating law agent...")
    
    llm = get_standard_llm(api_key=api_key)
    tools = create_rag_tools(retriever, domain="legal")
    before_agent_callback = create_before_agent_callback(domain="legal", default_role="employee")
    
    agent = LlmAgent(
        name="law_agent",
        model=llm,
        description="Handles legal queries with role-based access control",
        instruction=LAW_AGENT_FULL,
        tools=list(tools),
        before_agent_callback=before_agent_callback
    )
    
    logger.info("✅ Law agent created")
    return agent
