"""
Logging Configuration
Professional logging setup with proper formatting and levels.
"""

import logging
import sys
from pathlib import Path


def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Set up a logger with console and file handlers.
    
    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler with color-friendly format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    
    # File handler with detailed format
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "trustworthy_rag.log")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# Module-level logger for audit trail
audit_logger = setup_logger("trustworthy_rag.audit")


def log_access_attempt(user: str, role: str, domain: str, granted: bool):
    """Log access control decisions for audit trail."""
    status = "GRANTED" if granted else "DENIED"
    audit_logger.info(f"ACCESS {status} | User: {user} | Role: {role} | Domain: {domain}")


def log_pii_detection(document_id: str, pii_types: list):
    """Log PII detection for compliance tracking."""
    audit_logger.info(f"PII DETECTED | Doc: {document_id} | Types: {', '.join(pii_types)}")


def log_query(user: str, query: str, doc_count: int, duration: float):
    """Log query execution for performance monitoring."""
    audit_logger.info(
        f"QUERY | User: {user} | Query: {query[:50]}... | Docs: {doc_count} | Duration: {duration:.2f}s"
    )

