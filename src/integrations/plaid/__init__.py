# src/integrations/plaid/__init__.py
"""
Plaid Integration for ACMS Financial Constitution

Phase 2A: Financial data ingestion from Plaid API
- Investment holdings and transactions
- Securities master data
- Account balances

Privacy: All dollar amounts encrypted at rest.
LLM Boundary: Financial data NEVER sent to external LLMs.
"""

from .client import PlaidClient
from .oauth import PlaidOAuth
from .sync_service import PlaidSyncService

__all__ = ["PlaidClient", "PlaidOAuth", "PlaidSyncService"]
