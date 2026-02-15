"""
Privacy Level Definitions

Four-tier privacy system for enterprise data protection.
"""

from enum import Enum


class PrivacyLevel(Enum):
    """
    Privacy levels for memory/knowledge storage

    Levels (from least to most restrictive):
    - PUBLIC: Company-wide knowledge (docs, processes, tutorials)
    - INTERNAL: Team-level information (project docs, meeting notes)
    - CONFIDENTIAL: Sensitive business data (client budgets, financials, PII)
    - LOCAL_ONLY: Personal notes, private conversations (owner-only access)
    """

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    LOCAL_ONLY = "LOCAL_ONLY"

    def __str__(self):
        return self.value
