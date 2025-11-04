"""
Compliance Agent for regulatory frameworks (HIPAA, GDPR, SOX).
Uses Google ADK with compliance validation tools.
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from typing import Optional
from google.adk.agents import LlmAgent

from agentic_system.compliance.prompt import COMPLIANCE_AGENT_FULL
from agentic_system.security.tools import create_security_tools
from agentic_system.utils.llm import get_fast_llm
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_compliance_agent(
    api_key: Optional[str] = None
) -> LlmAgent:
    """
    Create the compliance agent for regulatory validation.
    
    Args:
        api_key: OpenAI API key (optional)
    
    Returns:
        LlmAgent configured for compliance validation
    """
    logger.info("🔨 Creating compliance agent...")
    
    # Use fast model for compliance checks (rule-based)
    llm = get_fast_llm(api_key=api_key)
    
    # Create tool function - reuse security tools for compliance validation
    _, _, _, validate_compliance = create_security_tools()
    
    # Create agent - ADK will auto-convert function to tool
    agent = LlmAgent(
        name="compliance_agent",
        model=llm,
        description="Validates documents against regulatory compliance frameworks",
        instruction=COMPLIANCE_AGENT_FULL,
        tools=[validate_compliance]
    )
    
    logger.info("✅ Compliance agent created")
    return agent
