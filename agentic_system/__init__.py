"""
Trustworthy RAG Agentic System using Google ADK
Enterprise-grade multi-agent system with privacy, security, and compliance.
"""

from agentic_system.base.agent import get_trustworthy_rag_agent, create_trustworthy_rag_agent

__all__ = ["get_trustworthy_rag_agent", "create_trustworthy_rag_agent"]

# For Google ADK web UI - export the agent getter
def get_agent():
    """
    Get the root agent for Google ADK web UI.
    
    This function is called by Google ADK to get the agent.
    """
    return get_trustworthy_rag_agent()

# Also export root_agent for direct access (ADK looks for this)
# Import from agent.py which has the lazy-loaded root_agent
try:
    from agentic_system.agent import root_agent
    __all__.append("root_agent")
except ImportError:
    # Fallback if agent.py not available
    root_agent = get_trustworthy_rag_agent()
    __all__.append("root_agent")
