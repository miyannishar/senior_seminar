"""
Configuration Management
Centralized configuration for the Trustworthy RAG system.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """LLM model configuration."""
    name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None
    
    def __post_init__(self):
        """Load API key from environment if not provided."""
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class RetrievalConfig:
    """Retrieval system configuration."""
    top_k: int = 5
    semantic_weight: float = 0.7
    keyword_max_features: int = 1000
    use_bigrams: bool = True


@dataclass
class SecurityConfig:
    """Security and validation configuration."""
    enable_pii_masking: bool = True
    enable_rbac: bool = True
    log_access_violations: bool = True
    mask_ssn: bool = True
    mask_credit_cards: bool = True
    mask_emails: bool = True


@dataclass
class SystemConfig:
    """Main system configuration."""
    model: ModelConfig = None
    retrieval: RetrievalConfig = None
    security: SecurityConfig = None
    log_level: str = "INFO"
    data_path: str = "../data/sample_docs.json"
    
    def __post_init__(self):
        """Initialize sub-configs if not provided."""
        if self.model is None:
            self.model = ModelConfig()
        if self.retrieval is None:
            self.retrieval = RetrievalConfig()
        if self.security is None:
            self.security = SecurityConfig()


def get_config() -> SystemConfig:
    """
    Get system configuration from environment or defaults.
    
    Returns:
        SystemConfig instance
    """
    return SystemConfig(
        model=ModelConfig(
            name=os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
            temperature=float(os.getenv("MODEL_TEMPERATURE", "0.7"))
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )

