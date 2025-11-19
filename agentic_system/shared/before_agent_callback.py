"""
Before Agent Callback for Guardrail Validation.

This callback runs BEFORE the agent processes a request, allowing us to
validate input and block unsafe requests before they reach the agent.
"""

import sys
import os
from typing import Optional

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai.types import Content, Part
from agentic_system.shared.guardrails import get_guardrails
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_before_agent_callback(domain: str = "unknown", default_role: str = "employee"):
    """
    Create a before_agent_callback function for ADK agents.
    
    Args:
        domain: Domain name for the agent (e.g., "finance", "hr")
        default_role: Default user role if not specified
    
    Returns:
        Callback function for before_agent_callback
    """
    guardrails = get_guardrails()
    
    def before_agent_callback(
        callback_context: CallbackContext,
        **kwargs
    ) -> Optional[LlmResponse]:
        """Before agent callback that validates input with guardrails."""
        try:
            # Extract user message from user_content
            user_message = None
            user_id = "unknown"
            session_id = None
            
            # Get session info
            if hasattr(callback_context, 'session'):
                session = callback_context.session
                if hasattr(session, 'id'):
                    session_id = session.id
                if hasattr(session, 'user_id'):
                    user_id = session.user_id
            
            # Extract message from user_content
            if hasattr(callback_context, 'user_content') and callback_context.user_content:
                user_content = callback_context.user_content
                if hasattr(user_content, 'parts') and user_content.parts:
                    text_parts = [part.text for part in user_content.parts if hasattr(part, 'text') and part.text]
                    if text_parts:
                        user_message = ' '.join(text_parts)
            
            if not user_message:
                return None  # Allow to proceed if we can't extract message
            
            # Validate input with guardrails
            is_safe, violation = guardrails.validate_input(
                query=user_message,
                user=user_id,
                role=default_role,
                domain=domain,
                session_id=session_id,
                store_query=True
            )
            
            if not is_safe:
                logger.critical(f"🚨 Guardrail violation blocked: {violation.get('violation_type')} - {violation.get('description')}")
                
                # Create user-friendly blocked message
                violation_type = violation.get('violation_type', 'POLICY_VIOLATION')
                description = violation.get('description', 'This message violates our security policy')
                
                # Map violation types to user-friendly messages
                violation_messages = {
                    'TOXIC_CONTENT': 'This message contains inappropriate content that violates our policy',
                    'PII_DETECTED': 'This message contains sensitive personal information that violates our policy',
                    'RATE_LIMIT_EXCEEDED': 'Too many requests detected. Please wait before trying again',
                    'POLICY_VIOLATION': 'This message violates our security policy'
                }
                
                user_message = violation_messages.get(violation_type, description)
                blocked_message = f"🚨 This message violates our policy and has been blocked.\n\nReason: {user_message}\n\nI cannot assist with this request."
                
                return LlmResponse(
                    content=Content(
                        role="model",
                        parts=[Part(text=blocked_message)]
                    )
                )
            
            return None  # Allow the agent to proceed
            
        except Exception as e:
            logger.error(f"Error in before_agent_callback: {e}", exc_info=True)
            return None  # On error, allow to proceed
    
    return before_agent_callback
