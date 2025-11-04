"""
Agent module for Google ADK Web UI

Google ADK looks for 'agentic_system.agent.root_agent' when you run 'adk web'.
This file exposes the root_agent variable that ADK expects.
"""

import sys
import os
from pathlib import Path

# Add paths to ensure imports work
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / ".env"
load_dotenv(env_path)

# Import agent getter
from agentic_system.base.agent import get_trustworthy_rag_agent

# Export root_agent for Google ADK
# ADK expects this variable to be named 'root_agent'
# Lazy loading - agent is created when this module is accessed
def _create_root_agent():
    """Create and return the root agent."""
    return get_trustworthy_rag_agent()

# Create root_agent on module load (ADK will access it)
root_agent = _create_root_agent()

