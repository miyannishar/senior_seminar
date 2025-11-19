"""
Health Agent for healthcare queries.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from typing import Optional
from google.adk.agents import LlmAgent
from agentic_system.health.prompt import HEALTH_AGENT_FULL
from agentic_system.shared.tools import create_rag_tools
from agentic_system.shared.before_agent_callback import create_before_agent_callback
from agentic_system.utils.llm import get_standard_llm
from retriever import HybridRetriever
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_health_agent(retriever: HybridRetriever, api_key: Optional[str] = None) -> LlmAgent:
    """Create health agent."""
    logger.info("🔨 Creating health agent...")
    
    llm = get_standard_llm(api_key=api_key)
    tools = create_rag_tools(retriever, domain="health")
    before_agent_callback = create_before_agent_callback(domain="health", default_role="employee")
    
    agent = LlmAgent(
        name="health_agent",
        model=llm,
        description="Handles healthcare queries with role-based access control",
        instruction=HEALTH_AGENT_FULL,
        tools=list(tools),
        before_agent_callback=before_agent_callback
    )
    
    logger.info("✅ Health agent created")
    return agent
