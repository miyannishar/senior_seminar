"""
Response Agent for generating final answers from validated documents.
Uses Google ADK to create high-quality, well-cited responses.
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from typing import Optional
from google.adk.agents import LlmAgent

from agentic_system.response.prompt import RESPONSE_AGENT_FULL
from agentic_system.response.tools import create_response_tools
from agentic_system.utils.llm import get_powerful_llm
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_response_agent(
    api_key: Optional[str] = None
) -> LlmAgent:
    """
    Create the response agent for generating final answers.
    
    Args:
        api_key: OpenAI API key (optional)
    
    Returns:
        LlmAgent configured for response generation
    """
    logger.info("🔨 Creating response agent...")
    
    # Use powerful model for high-quality responses
    llm = get_powerful_llm(api_key=api_key)
    
    # Create tool functions
    generate_response, extract_sources = create_response_tools()
    
    # Create agent - ADK will auto-convert functions to tools
    agent = LlmAgent(
        name="response_agent",
        model=llm,
        description="Generates high-quality responses from validated documents",
        instruction=RESPONSE_AGENT_FULL,
        tools=[generate_response, extract_sources]
    )
    
    logger.info("✅ Response agent created")
    return agent
