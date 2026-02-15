"""Authentication and authorization module for ACMS.

This module provides:
- Password hashing and verification (using argon2)
- JWT token generation and validation
- Role-based access control (RBAC)
- Authentication middleware for FastAPI

Part of Sprint 1 Security Foundation (Days 4-5).
"""

from src.auth.simple_auth import SimpleAuth, get_auth_service
from src.auth.middleware import get_current_user, require_role, AuthError

__all__ = [
    "SimpleAuth",
    "get_auth_service",
    "get_current_user",
    "require_role",
    "AuthError",
]
