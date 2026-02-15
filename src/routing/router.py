"""
Confidence-Based Routing Engine

Intelligent routing based on confidence scores.

Modes:
- LOCAL_ONLY: confidence ≥90% → Serve from cache ($0)
- PASSTHROUGH: confidence <90% → Route to LLM

(ENRICHED mode deferred to Week 7 after validation)

Implementation Status: PLACEHOLDER
Week 5 Day 6: Task 1 (6 hours)
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Router:
    """
    Confidence-based routing engine.

    To be implemented in Week 5 Day 6.
    """

    async def route(self, query: str, user_id: str) -> Dict[str, Any]:
        """
        Route query based on confidence.

        To be implemented in Week 5 Day 6.
        """
        pass
