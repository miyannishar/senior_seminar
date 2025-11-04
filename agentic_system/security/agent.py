"""
Security Agent for validation, RBAC, and PII protection.
Uses Google ADK with security tools.
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from typing import Optional
from google.adk.agents import LlmAgent

from agentic_system.security.prompt import SECURITY_AGENT_FULL
from agentic_system.security.tools import create_security_tools
from agentic_system.utils.llm import get_fast_llm
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_security_agent(
    api_key: Optional[str] = None
) -> LlmAgent:
    """
    Create the security agent for validation and access control.
    
    Args:
        api_key: OpenAI API key (optional)
    
    Returns:
        LlmAgent configured for security operations
    """
    logger.info("🔨 Creating security agent...")
    
    # Use fast model for validation (deterministic task)
    llm = get_fast_llm(api_key=api_key)
    
    # Create tool functions
    validate_document, batch_validate_documents, check_permissions, _ = create_security_tools()
    
    # Create agent - ADK will auto-convert functions to tools
    agent = LlmAgent(
        name="security_agent",
        model=llm,
        description="Validates documents, applies RBAC, and masks PII",
        instruction=SECURITY_AGENT_FULL,
        tools=[validate_document, batch_validate_documents, check_permissions]
    )
    
    logger.info("✅ Security agent created")
    return agent
