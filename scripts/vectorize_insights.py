#!/usr/bin/env python3
"""Vectorize pending insights to ACMS_Insights_v1."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.intelligence.insight_extractor import InsightStorage

async def vectorize():
    storage = InsightStorage()
    # vectorize_pending takes limit only - embeddings are created internally
    vectorized = await storage.vectorize_pending(limit=2500)
    print(f'Vectorized {vectorized} insights to ACMS_Insights_v1')

if __name__ == "__main__":
    asyncio.run(vectorize())
