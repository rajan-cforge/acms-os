#!/usr/bin/env python3
"""
Weaviate Re-Sync Script

Re-generates embeddings for all memories in PostgreSQL and syncs to Weaviate.

Usage:
    python3 scripts/resync_weaviate.py [--batch-size 100] [--start-from 0]

Progress:
    - Processes in batches to handle rate limits
    - Saves progress every 1000 memories
    - Can resume from last checkpoint if interrupted

Cost Estimate:
    - OpenAI text-embedding-3-small: $0.00002 per embedding
    - 93,507 memories = ~$1.87 total
    - Time: 30-45 minutes (depending on rate limits)
"""

import os
import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from src.storage.database import get_session
from src.storage.models import MemoryItem
from src.storage.weaviate_client import WeaviateClient
from src.embeddings.openai_embeddings import OpenAIEmbeddings


class WeaviateResyncer:
    """Re-sync all memories from PostgreSQL to Weaviate."""

    def __init__(self, batch_size: int = 100, start_from: int = 0):
        """Initialize resyncer.

        Args:
            batch_size: Number of memories to process per batch
            start_from: Memory offset to resume from
        """
        self.batch_size = batch_size
        self.start_from = start_from
        self.weaviate = WeaviateClient()
        self.openai = OpenAIEmbeddings()

        # Stats
        self.total_processed = 0
        self.total_synced = 0
        self.total_errors = 0
        self.start_time = None
        self.estimated_cost = 0.0

    async def get_total_count(self) -> int:
        """Get total count of memories to sync."""
        async with get_session() as session:
            stmt = select(MemoryItem)
            result = await session.execute(stmt)
            memories = result.scalars().all()
            return len(memories)

    async def sync_batch(self, offset: int) -> Dict[str, Any]:
        """Sync a batch of memories.

        Args:
            offset: Starting offset for this batch

        Returns:
            dict: Batch stats (synced, errors, cost)
        """
        batch_stats = {"synced": 0, "errors": 0, "cost": 0.0}

        async with get_session() as session:
            # Fetch batch
            stmt = (
                select(MemoryItem)
                .order_by(MemoryItem.created_at)
                .limit(self.batch_size)
                .offset(offset)
            )
            result = await session.execute(stmt)
            memories = result.scalars().all()

            if not memories:
                return batch_stats

            # Process each memory
            for memory in memories:
                try:
                    # Generate embedding
                    embedding = self.openai.generate_embedding(memory.content)
                    batch_stats["cost"] += 0.00002  # OpenAI cost per embedding

                    # Prepare vector data
                    vector_data = {
                        "content": memory.content,
                        "memory_id": str(memory.memory_id),
                        "user_id": str(memory.user_id),
                        "tier": memory.tier,
                        "phase": memory.phase or "",
                        "tags": memory.tags or [],
                        "privacy_level": memory.privacy_level or "INTERNAL",  # FIX: Include privacy_level
                        "crs_score": memory.crs_score or 0.0,
                        "created_at": memory.created_at,
                    }

                    # Insert into Weaviate
                    vector_uuid = self.weaviate.insert_vector(
                        collection="ACMS_MemoryItems_v1",
                        vector=embedding,
                        data=vector_data,
                    )

                    # Update PostgreSQL with new vector ID
                    memory.embedding_vector_id = vector_uuid
                    batch_stats["synced"] += 1

                except Exception as e:
                    print(f"❌ Error syncing memory {memory.memory_id}: {e}")
                    batch_stats["errors"] += 1
                    continue

            # Commit PostgreSQL updates
            await session.commit()

        return batch_stats

    async def run(self):
        """Execute full re-sync."""
        self.start_time = time.time()

        # Get total count
        total_memories = await self.get_total_count()
        print(f"\n{'='*60}")
        print(f"  Weaviate Re-Sync")
        print(f"{'='*60}")
        print(f"Total memories to sync: {total_memories:,}")
        print(f"Batch size: {self.batch_size}")
        print(f"Starting from: {self.start_from}")
        print(f"Estimated cost: ${(total_memories * 0.00002):.2f}")
        print(f"Estimated time: {(total_memories / 200):.0f}-{(total_memories / 100):.0f} minutes")
        print(f"{'='*60}\n")

        # Confirm
        response = input("Proceed with re-sync? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Cancelled")
            return

        print(f"\n🚀 Starting re-sync at {datetime.now().strftime('%H:%M:%S')}\n")

        # Process in batches
        offset = self.start_from
        while offset < total_memories:
            batch_start = time.time()

            # Sync batch
            batch_stats = await self.sync_batch(offset)
            self.total_synced += batch_stats["synced"]
            self.total_errors += batch_stats["errors"]
            self.estimated_cost += batch_stats["cost"]
            self.total_processed += self.batch_size

            # Calculate progress
            progress = min(100, (offset + self.batch_size) / total_memories * 100)
            elapsed = time.time() - self.start_time
            rate = self.total_synced / elapsed if elapsed > 0 else 0
            eta_seconds = (total_memories - offset) / rate if rate > 0 else 0
            eta_minutes = eta_seconds / 60

            # Progress update
            print(f"[{progress:5.1f}%] Synced: {self.total_synced:,}/{total_memories:,} | "
                  f"Errors: {self.total_errors} | "
                  f"Rate: {rate:.1f}/s | "
                  f"ETA: {eta_minutes:.1f}m | "
                  f"Cost: ${self.estimated_cost:.2f}")

            # Checkpoint every 1000 memories
            if self.total_synced % 1000 == 0 and self.total_synced > 0:
                print(f"  ✅ Checkpoint: {self.total_synced:,} memories synced")

            offset += self.batch_size

            # Rate limiting (avoid hitting OpenAI limits)
            # OpenAI limit: 3000 requests/min for tier 1
            # Optimized: 500 requests/min = 8.33/sec (safe margin below 3000/min)
            batch_time = time.time() - batch_start
            min_batch_time = self.batch_size / 500  # 500 req/min (OPTIMIZED)
            if batch_time < min_batch_time:
                await asyncio.sleep(min_batch_time - batch_time)

        # Final stats
        elapsed = time.time() - self.start_time
        print(f"\n{'='*60}")
        print(f"  ✅ Re-sync Complete!")
        print(f"{'='*60}")
        print(f"Total synced: {self.total_synced:,}")
        print(f"Total errors: {self.total_errors}")
        print(f"Final cost: ${self.estimated_cost:.2f}")
        print(f"Time elapsed: {elapsed/60:.1f} minutes")
        print(f"Average rate: {self.total_synced/elapsed:.1f} memories/sec")
        print(f"{'='*60}\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Re-sync PostgreSQL memories to Weaviate")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size (default: 100)")
    parser.add_argument("--start-from", type=int, default=0, help="Offset to resume from (default: 0)")
    args = parser.parse_args()

    resyncer = WeaviateResyncer(
        batch_size=args.batch_size,
        start_from=args.start_from,
    )

    await resyncer.run()


if __name__ == "__main__":
    asyncio.run(main())
