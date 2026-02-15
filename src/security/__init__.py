"""Security module for ACMS.

RBAC and privacy filtering is handled by:
- src/privacy/policy.py - AccessFilter, get_access_filter(), build_weaviate_filter()

This module contains additional security utilities.
"""

# Note: The canonical RBAC implementation is in src/privacy/policy.py
# Use: from src.privacy.policy import get_access_filter, AccessFilter
