"""
Custom Exceptions
Define specific exceptions for better error handling.
"""


class TrustworthyRAGException(Exception):
    """Base exception for Trustworthy RAG system."""
    pass


class AccessDeniedException(TrustworthyRAGException):
    """Raised when user doesn't have permission to access a resource."""
    
    def __init__(self, user_role: str, domain: str):
        self.user_role = user_role
        self.domain = domain
        super().__init__(f"Access denied: Role '{user_role}' cannot access domain '{domain}'")


class ValidationException(TrustworthyRAGException):
    """Raised when document validation fails."""
    pass


class RetrievalException(TrustworthyRAGException):
    """Raised when document retrieval fails."""
    pass


class GenerationException(TrustworthyRAGException):
    """Raised when LLM generation fails."""
    pass


class ConfigurationException(TrustworthyRAGException):
    """Raised when configuration is invalid or missing."""
    pass

