"""Gateway Coordinators - Modular orchestration components.

The orchestrator is split into 5 coordinators for testability:
1. PreflightCoordinator - Security checks (uses PreflightGate)
2. QueryPlanner - Intent detection + query augmentation + web search decision
3. RetrievalCoordinator - Dual memory search + ranking + context building
4. LLMCoordinator - Agent selection + prompt building + streaming
5. PersistenceCoordinator - Metrics + memory writing + caching

Each coordinator:
- Has a single responsibility
- Can be tested in isolation with mocks
- Uses dependency injection for external services
- Emits events for UI progress tracking

Part of Sprint 2 Architecture & Resilience (Days 6-7).
"""

from src.gateway.coordinators.query_planner import QueryPlanner, QueryPlan
from src.gateway.coordinators.retrieval import RetrievalCoordinator, RetrievalResult
from src.gateway.coordinators.llm import LLMCoordinator, StreamEvent
from src.gateway.coordinators.persistence import PersistenceCoordinator

__all__ = [
    "QueryPlanner",
    "QueryPlan",
    "RetrievalCoordinator",
    "RetrievalResult",
    "LLMCoordinator",
    "StreamEvent",
    "PersistenceCoordinator",
]
