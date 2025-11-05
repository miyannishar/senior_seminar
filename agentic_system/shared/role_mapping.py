"""
Role mapping for department-specific roles to general access control roles.
"""

from typing import Dict, List, Optional

# Map department-specific roles to general access control roles
# Format: {department_role: general_role}
DEPARTMENT_ROLE_MAPPING: Dict[str, Dict[str, str]] = {
    "accounting": {
        "manager": "analyst",  # Accounting manager has analyst-level access
        "senior_accountant": "analyst",
        "accountant": "manager",
        "employee": "employee",
        "general": "guest"
    },
    "finance": {
        "manager": "analyst",
        "analyst": "analyst",
        "employee": "employee",
        "general": "guest"
    },
    "hr": {
        "manager": "manager",
        "hr_specialist": "analyst",
        "employee": "employee",
        "general": "guest"
    },
    "legal": {
        "manager": "admin",  # Legal managers have admin access
        "legal_counsel": "analyst",
        "paralegal": "manager",
        "employee": "employee",
        "general": "guest"
    },
    "health": {
        "manager": "admin",  # Health managers have admin access (HIPAA compliance)
        "doctor": "analyst",  # Doctors have analyst access
        "nurse": "manager",
        "employee": "employee",
        "general": "guest"
    }
}


def get_available_roles(department: str) -> List[str]:
    """
    Get list of available roles for a department.
    
    Args:
        department: Department name (accounting, finance, hr, legal)
    
    Returns:
        List of available role names
    """
    mapping = DEPARTMENT_ROLE_MAPPING.get(department, {})
    return list(mapping.keys())


def get_role_description(department: str, role: str) -> str:
    """
    Get description of what access level a role has.
    
    Args:
        department: Department name
        role: Role within that department
    
    Returns:
        Description string
    """
    general_role = map_department_role_to_general_role(department, role)
    
    descriptions = {
        "admin": "full access to all domains",
        "analyst": "access to finance, hr, and public domains",
        "manager": "access to hr and public domains",
        "employee": "access to public domain only",
        "guest": "access to public domain only"
    }
    
    return descriptions.get(general_role, "limited access")


def map_department_role_to_general_role(department: str, department_role: str) -> str:
    """
    Map a department-specific role to a general access control role.
    
    Args:
        department: Department name (accounting, finance, hr, legal)
        department_role: Role within that department
    
    Returns:
        General role for access control (admin, analyst, manager, employee, guest)
    """
    mapping = DEPARTMENT_ROLE_MAPPING.get(department, {})
    general_role = mapping.get(department_role.lower(), "guest")
    
    return general_role


def get_role_for_access(department: str, department_role: str) -> str:
    """
    Get the access control role for a department-specific role.
    
    This is used to check permissions against the ROLE_ACCESS mapping.
    
    Args:
        department: Department name
        department_role: Role within that department
    
    Returns:
        General role for access control
    """
    return map_department_role_to_general_role(department, department_role)


def format_role_options_for_prompt(department: str) -> str:
    """
    Format available roles for inclusion in prompts.
    
    Args:
        department: Department name
    
    Returns:
        Formatted string with role options and descriptions
    """
    roles = get_available_roles(department)
    mapping = DEPARTMENT_ROLE_MAPPING.get(department, {})
    
    lines = []
    for role in roles:
        general_role = mapping.get(role, "guest")
        desc = get_role_description(department, role)
        lines.append(f"     - `{role}` - Maps to {general_role} role ({desc})")
    
    return "\n".join(lines)
