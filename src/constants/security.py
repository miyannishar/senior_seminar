"""
Security Constants
PII patterns, sensitive terms, and role-based access control mappings.
"""

from typing import Dict, List, Tuple

# Sensitive terms that trigger security alerts
SENSITIVE_TERMS: List[str] = [
    "SSN",
    "AccountNumber",
    "Salary",
    "PatientName",
    "Confidential",
    "Password",
    "CreditCard",
    "BankAccount"
]

# PII regex patterns for masking
# Format: {pattern_name: (regex_pattern, replacement_text)}
PII_PATTERNS: Dict[str, Tuple[str, str]] = {
    'ssn': (r'\b\d{3}-\d{2}-\d{4}\b', '[MASKED-SSN]'),
    'ssn_no_dash': (r'\b\d{9}\b', '[MASKED-SSN]'),
    'credit_card': (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[MASKED-CC]'),
    'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[MASKED-EMAIL]'),
    'phone': (r'\b\d{3}-\d{3}-\d{4}\b', '[MASKED-PHONE]'),
    'account_id': (r'\b[A-Z]{2}\d{6}\b', '[MASKED-ID]'),
    'salary': (r'\$\d{1,3}(,\d{3})*(\.\d{2})?', '[MASKED-AMOUNT]'),
}

# Role-based access control mapping
# Format: {role: [allowed_domains]}
ROLE_ACCESS: Dict[str, List[str]] = {
    "admin": ["finance", "hr", "health", "public", "legal"],
    "analyst": ["finance", "hr", "public"],
    "manager": ["hr", "public"],
    "employee": ["public"],
    "guest": ["public"]
}

# Role-specific PII masking rules
# Format: {role: {domain: [patterns_to_mask]}}
ROLE_MASKING_RULES: Dict[str, Dict[str, List[str]]] = {
    "admin": {
        "default": ['ssn', 'ssn_no_dash', 'credit_card', 'account_id']
    },
    "analyst": {
        "finance": ['ssn', 'ssn_no_dash', 'credit_card'],
        "hr": ['ssn', 'ssn_no_dash', 'credit_card'],
        "default": list(PII_PATTERNS.keys())
    },
    "manager": {
        "hr": ['ssn', 'ssn_no_dash', 'credit_card', 'salary'],
        "default": list(PII_PATTERNS.keys())
    },
    "default": {
        "default": list(PII_PATTERNS.keys())
    }
}

