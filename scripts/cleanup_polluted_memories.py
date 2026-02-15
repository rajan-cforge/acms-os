"""
ACMS Intelligent Memory Pollution Cleanup Script

Identifies and removes polluted memories using AI-powered detection.
Pollution includes: generic responses, incorrect information, low-quality content.

Usage:
    python scripts/cleanup_polluted_memories.py --auto-detect
    python scripts/cleanup_polluted_memories.py --keyword "association for computing machinery"
    python scripts/cleanup_polluted_memories.py --dry-run
    python scripts/cleanup_polluted_memories.py --before-date "2025-10-20"
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime
from typing import List, Dict, Tuple
import logging

# Add project root to path
sys.path.append('/path/to/acms')

from sqlalchemy import create_engine, text
from src.storage.weaviate_client import WeaviateClient
from src.embeddings.openai_embeddings import OpenAIEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PollutionDetector:
    """AI-powered memory pollution detector"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.pollution_patterns = [
            # Generic/Placeholder responses
            "I don't have specific information",
            "I don't have access to",
            "I cannot determine",
            "association for computing machinery",
            "applied and computational mathematics",
            "academic computing and media services",
            "automated configuration management system",

            # Uncertain language (high occurrence = pollution)
            "might be", "could be", "possibly", "perhaps",
            "I'm not sure", "I don't know",

            # Generic filler
            "various possibilities", "multiple meanings",
            "several options", "different interpretations"
        ]

    async def detect_polluted_memory(self, memory: Dict) -> Tuple[bool, float, List[str]]:
        """
        Detect if a memory is polluted.

        Returns:
            (is_polluted, confidence_score, reasons)
        """
        content = memory['content'].lower()
        reasons = []
        pollution_score = 0.0

        # Pattern matching
        for pattern in self.pollution_patterns:
            if pattern.lower() in content:
                pollution_score += 0.3
                reasons.append(f"Contains generic pattern: '{pattern}'")

        # Length check - very short responses are often low quality
        if len(content) < 100:
            pollution_score += 0.2
            reasons.append(f"Very short response ({len(content)} chars)")

        # Check if memory is a question without answer
        if '?' in content and len(content.split('?')[1].strip()) < 50:
            pollution_score += 0.4
            reasons.append("Appears to be question without substantial answer")

        # Check for contradictions or uncertainty
        uncertainty_words = ['might', 'could', 'possibly', 'perhaps', 'maybe']
        uncertainty_count = sum(1 for word in uncertainty_words if word in content)
        if uncertainty_count >= 3:
            pollution_score += 0.3
            reasons.append(f"High uncertainty ({uncertainty_count} uncertain words)")

        # Normalize score
        pollution_score = min(pollution_score, 1.0)

        is_polluted = pollution_score >= 0.5

        return is_polluted, pollution_score, reasons


class MemoryCleaner:
    """Clean polluted memories from all storage tiers"""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.detector = PollutionDetector()
        self.engine = create_engine(
            'postgresql://acms_user:acms_password@localhost:5432/acms_db'
        )
        self.weaviate = WeaviateClient()

    def find_memories_with_keyword(self, keyword: str) -> List[Dict]:
        """Find memories containing specific keyword"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, content, source, privacy_level, created_at
                    FROM memories
                    WHERE content ILIKE :keyword
                    ORDER BY created_at ASC
                """),
                {"keyword": f"%{keyword}%"}
            )
            return [dict(row._mapping) for row in result]

    def find_memories_before_date(self, date_str: str) -> List[Dict]:
        """Find memories created before specific date"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, content, source, privacy_level, created_at
                    FROM memories
                    WHERE created_at < :date
                    ORDER BY created_at ASC
                """),
                {"date": date_str}
            )
            return [dict(row._mapping) for row in result]

    def find_all_memories(self) -> List[Dict]:
        """Find all memories for auto-detection"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, content, source, privacy_level, created_at
                    FROM memories
                    ORDER BY created_at ASC
                """)
            )
            return [dict(row._mapping) for row in result]

    async def auto_detect_polluted_memories(self) -> List[Dict]:
        """Auto-detect polluted memories using AI"""
        logger.info("🔍 Scanning all memories for pollution...")
        all_memories = self.find_all_memories()
        logger.info(f"Found {len(all_memories)} total memories")

        polluted_memories = []

        for i, memory in enumerate(all_memories):
            if i % 10 == 0:
                logger.info(f"Scanning memory {i+1}/{len(all_memories)}...")

            is_polluted, score, reasons = await self.detector.detect_polluted_memory(memory)

            if is_polluted:
                memory['pollution_score'] = score
                memory['pollution_reasons'] = reasons
                polluted_memories.append(memory)

        logger.info(f"✅ Found {len(polluted_memories)} polluted memories")
        return polluted_memories

    def delete_memory(self, memory_id: str):
        """Delete memory from PostgreSQL and Weaviate"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete memory: {memory_id}")
            return

        # Delete from PostgreSQL
        with self.engine.connect() as conn:
            conn.execute(
                text("DELETE FROM memories WHERE id = :id"),
                {"id": memory_id}
            )
            conn.commit()

        # Delete from Weaviate
        try:
            collection = self.weaviate._client.collections.get("ConversationMemory_v1")
            collection.data.delete_many(
                where={"path": ["memory_id"], "operator": "Equal", "valueText": str(memory_id)}
            )
        except Exception as e:
            logger.warning(f"Could not delete from Weaviate: {e}")

        logger.info(f"✅ Deleted memory: {memory_id}")

    def print_memory_report(self, memories: List[Dict]):
        """Print detailed report of memories to be cleaned"""
        print("\n" + "=" * 80)
        print(f"POLLUTION REPORT: {len(memories)} memories found")
        print("=" * 80)

        for i, memory in enumerate(memories):
            print(f"\n[{i+1}] Memory ID: {memory['id']}")
            print(f"Created: {memory['created_at']}")
            print(f"Source: {memory.get('source', 'N/A')}")

            if 'pollution_score' in memory:
                print(f"Pollution Score: {memory['pollution_score']:.2f}")
                print(f"Reasons:")
                for reason in memory['pollution_reasons']:
                    print(f"  - {reason}")

            # Print first 200 chars of content
            content_preview = memory['content'][:200] + "..." if len(memory['content']) > 200 else memory['content']
            print(f"Content: {content_preview}")
            print("-" * 80)

    async def cleanup(self, args):
        """Main cleanup logic"""
        memories_to_delete = []

        if args.keyword:
            logger.info(f"🔍 Searching for keyword: {args.keyword}")
            memories_to_delete = self.find_memories_with_keyword(args.keyword)

        elif args.before_date:
            logger.info(f"🔍 Finding memories before: {args.before_date}")
            memories_to_delete = self.find_memories_before_date(args.before_date)

        elif args.auto_detect:
            memories_to_delete = await self.auto_detect_polluted_memories()

        else:
            logger.error("❌ Must specify --keyword, --before-date, or --auto-detect")
            return

        if not memories_to_delete:
            logger.info("✅ No polluted memories found!")
            return

        # Print report
        self.print_memory_report(memories_to_delete)

        # Confirm deletion
        if not self.dry_run:
            print(f"\n⚠️  About to delete {len(memories_to_delete)} memories!")
            confirm = input("Type 'DELETE' to confirm: ")

            if confirm != "DELETE":
                logger.info("Cleanup cancelled.")
                return

        # Delete memories
        for memory in memories_to_delete:
            self.delete_memory(memory['id'])

        logger.info(f"\n✅ Cleanup complete! Processed {len(memories_to_delete)} memories")

    def __del__(self):
        """Cleanup connections"""
        try:
            self.weaviate.close()
        except:
            pass


async def main():
    parser = argparse.ArgumentParser(description="ACMS Memory Pollution Cleanup")
    parser.add_argument('--keyword', help="Delete memories containing keyword")
    parser.add_argument('--before-date', help="Delete memories before date (YYYY-MM-DD)")
    parser.add_argument('--auto-detect', action='store_true', help="AI-powered pollution detection")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be deleted without deleting")

    args = parser.parse_args()

    cleaner = MemoryCleaner(dry_run=args.dry_run)
    await cleaner.cleanup(args)


if __name__ == "__main__":
    asyncio.run(main())
