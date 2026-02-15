"""Memory module - Typed memory system for ACMS.

Phase 1 Implementation: Clean memory types and service.

Components:
- models.py: MemoryType, MemoryTier, PrivacyLevel, MemoryItem, CandidateMemory
- memory_service.py: MemoryService (centralized CRUD)
- quality_gate.py: Quality validation before storage

Usage:
    from src.memory import MemoryService, MemoryItem, MemoryType, MemoryQualityGate

    # Create memory with quality validation
    gate = MemoryQualityGate()
    service = MemoryService()

    candidate = CandidateMemory(text="...", memory_type=MemoryType.SEMANTIC, source="user")
    decision = gate.evaluate(candidate)

    if decision.should_store:
        memory = await service.create_memory(candidate.to_memory_item(user_id))
"""

from src.memory.models import (
    MemoryType,
    MemoryTier,
    PrivacyLevel,
    MemoryItem,
    CandidateMemory
)
from src.memory.memory_service import MemoryService
from src.memory.quality_gate import MemoryQualityGate, QualityDecision

__all__ = [
    # Models
    "MemoryType",
    "MemoryTier",
    "PrivacyLevel",
    "MemoryItem",
    "CandidateMemory",
    # Service
    "MemoryService",
    # Quality Gate
    "MemoryQualityGate",
    "QualityDecision"
]
