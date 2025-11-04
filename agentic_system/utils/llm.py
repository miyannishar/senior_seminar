"""
LLM initialization utilities using Google ADK with LiteLLM.
Supports OpenAI models through LiteLLM integration.
"""

import os
from typing import Optional
from dotenv import load_dotenv

try:
    from google.adk.models.lite_llm import LiteLlm
except ImportError:
    raise ImportError(
        "Google ADK not installed. Install with: pip install google-adk"
    )

from utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

# OpenAI Models via LiteLLM
OPENAI_GPT_4O = "openai/gpt-4o"
OPENAI_GPT_4O_MINI = "openai/gpt-4o-mini"
OPENAI_GPT_4_TURBO = "openai/gpt-4-turbo"
OPENAI_GPT_35_TURBO = "openai/gpt-3.5-turbo"


def create_llm(
    api_key: Optional[str] = None,
    model: str = OPENAI_GPT_4O_MINI,
    temperature: float = 0.7
) -> LiteLlm:
    """
    Create a LiteLLM instance with OpenAI model for Google ADK.
    
    Args:
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY from environment
        model: OpenAI model name (default: gpt-4o-mini for cost efficiency)
        temperature: Model temperature (0.0-1.0)
    
    Returns:
        LiteLlm: Configured LiteLLM instance for ADK agents
    
    Raises:
        ValueError: If API key not found
    """
    logger.info(f"Creating LiteLLM instance with model: {model}")
    
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment")
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Set it in your .env file or export it."
            )
    
    try:
        llm = LiteLlm(
            model=model,
            api_key=api_key,
            temperature=temperature
        )
        logger.info(f"✅ LLM created successfully: {model}")
        return llm
    except Exception as e:
        logger.error(f"❌ Error creating LLM: {e}")
        raise


def get_fast_llm(api_key: Optional[str] = None) -> LiteLlm:
    """Get a fast, cost-effective model for quick operations."""
    return create_llm(api_key=api_key, model=OPENAI_GPT_4O_MINI, temperature=0.3)


def get_standard_llm(api_key: Optional[str] = None) -> LiteLlm:
    """Get standard model for regular operations."""
    return create_llm(api_key=api_key, model=OPENAI_GPT_4O_MINI, temperature=0.7)


def get_powerful_llm(api_key: Optional[str] = None) -> LiteLlm:
    """Get powerful model for complex reasoning."""
    return create_llm(api_key=api_key, model=OPENAI_GPT_4O, temperature=0.7)

