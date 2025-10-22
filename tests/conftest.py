"""
Pytest Configuration and Fixtures
"""

import pytest
import os
import sys
from typing import List, Dict, Any

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))


@pytest.fixture
def sample_documents() -> List[Dict[str, Any]]:
    """Sample documents for testing."""
    return [
        {
            "id": "test_001",
            "title": "Test Finance Document",
            "content": "This document contains financial information about Q1 revenue of $1.5M.",
            "domain": "finance",
            "classification": "confidential"
        },
        {
            "id": "test_002",
            "title": "Test HR Document",
            "content": "Employee benefits include health insurance and 401k matching.",
            "domain": "hr",
            "classification": "internal"
        },
        {
            "id": "test_003",
            "title": "Test Public Document",
            "content": "Our company values transparency and innovation in all we do.",
            "domain": "public",
            "classification": "public"
        },
        {
            "id": "test_004",
            "title": "Test Health Document",
            "content": "Patient confidentiality is maintained according to HIPAA standards.",
            "domain": "health",
            "classification": "confidential"
        }
    ]


@pytest.fixture
def test_users() -> Dict[str, Dict[str, str]]:
    """Sample users for testing."""
    return {
        "admin": {"username": "admin_user", "role": "admin"},
        "analyst": {"username": "analyst_user", "role": "analyst"},
        "manager": {"username": "manager_user", "role": "manager"},
        "employee": {"username": "employee_user", "role": "employee"},
        "guest": {"username": "guest_user", "role": "guest"}
    }


@pytest.fixture(autouse=True)
def mock_openai_key(monkeypatch):
    """Mock OpenAI API key for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

