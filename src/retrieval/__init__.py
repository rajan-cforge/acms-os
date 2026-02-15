"""Retrieval module - 3-stage retrieval pipeline.

Phase 2 Implementation: Clean separation of retrieval stages.

Stages:
1. Retriever - Raw fetch from vector DB + text search
2. Ranker - CRS scoring and re-ranking
3. ContextBuilder - Token-budgeted context assembly

Usage:
    from src.retrieval import Retriever, Ranker, ContextBuilder

    # Stage 1: Retrieve
    raw_results = await retriever.retrieve(query_embedding, filters)

    # Stage 2: Rank
    scored_results = ranker.score(raw_results, query_embedding)

    # Stage 3: Build context
    context = context_builder.build(scored_results)
"""

from src.retrieval.retriever import Retriever, RawResult
from src.retrieval.ranker import Ranker, ScoredResult
from src.retrieval.context_builder import ContextBuilder

__all__ = [
    "Retriever",
    "RawResult",
    "Ranker",
    "ScoredResult",
    "ContextBuilder"
]
