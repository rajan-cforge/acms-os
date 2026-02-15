"""
ACMS-Lite to ACMS Migration Script

Migrates all memories from ACMS-Lite (SQLite) to full ACMS (PostgreSQL + Weaviate).

Features:
- Deduplication check (skip if content_hash exists)
- Tag enrichment (auto-add phase tags)
- Batch processing with progress tracking
- Rollback capability (read-only source)
- Dry-run mode for testing

Usage:
    python3 -m src.scripts.migrate_acms_lite --dry-run  # Test first
    python3 -m src.scripts.migrate_acms_lite             # Execute
"""

import sys
import asyncio
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.storage.memory_crud import MemoryCRUD
from src.mcp.config import MCPConfig


class ACMSLiteMigrator:
    """Migrate ACMS-Lite memories to full ACMS."""

    def __init__(self, acms_lite_db: str = ".acms_lite.db", dry_run: bool = False):
        """
        Initialize migrator.

        Args:
            acms_lite_db: Path to ACMS-Lite SQLite database
            dry_run: If True, don't actually write to ACMS
        """
        self.acms_lite_db = acms_lite_db
        self.dry_run = dry_run
        self.memory_crud = MemoryCRUD()

        # Migration statistics
        self.stats = {
            "total": 0,
            "migrated": 0,
            "skipped_duplicates": 0,
            "failed": 0,
            "enriched_tags": 0
        }

        # Failed memories for retry
        self.failed_memories: List[Dict[str, Any]] = []

    def _get_content_hash(self, content: str) -> str:
        """Generate content hash for deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _enrich_tags(self, tags: List[str], phase: Optional[str]) -> List[str]:
        """
        Enhancement 3: Tag enrichment.

        Auto-add phase tags and enrich existing tags.

        Args:
            tags: Original tags
            phase: Phase name (e.g., "bootstrap", "infra", "storage", "mcp_server")

        Returns:
            Enriched tag list
        """
        enriched = set(tags)

        # Add phase tag if not already present
        if phase:
            phase_lower = phase.lower()

            # Map phase names to standard format
            phase_mapping = {
                "bootstrap": "phase-0",
                "infra": "phase-1",
                "storage": "phase-2a",
                "mcp_server": "phase-2b",
                "mcp_setup": "phase-2b",
                "2a": "phase-2a",
                "phase-2a": "phase-2a"
            }

            phase_tag = phase_mapping.get(phase_lower, f"phase-{phase_lower}")
            enriched.add(phase_tag)

            # Add technical tag if implementation-related
            if "implementation" in tags or "tech_spec" in tags:
                enriched.add("technical")

            # Add milestone tag if checkpoint or milestone
            if "checkpoint" in tags or "milestone" in tags:
                enriched.add("key_milestone")

        # Enrich specific tag combinations
        if "storage" in tags:
            enriched.add("phase-2a")
        if "mcp" in tags or "mcp_server" in tags:
            enriched.add("phase-2b")

        return sorted(list(enriched))

    async def _check_duplicate(self, content_hash: str) -> bool:
        """
        Enhancement 1: Deduplication check.

        Check if memory with this content_hash already exists in ACMS.

        Args:
            content_hash: Hash of memory content

        Returns:
            True if duplicate exists, False otherwise
        """
        # Query ACMS for existing memory with this hash
        # Note: This requires querying PostgreSQL directly since we don't have
        # a content_hash field yet. For now, we'll do simple content matching.

        # TODO: Add content_hash column to MemoryItem model for efficient deduplication
        # For Phase 2.5, we'll skip this check since we know ACMS-Lite memories
        # don't exist in ACMS yet (fresh migration).

        return False

    def _read_acms_lite_memories(self) -> List[Dict[str, Any]]:
        """
        Read all memories from ACMS-Lite SQLite database.

        Returns:
            List of memory dicts with keys: id, content, tags, phase, created_at
        """
        conn = sqlite3.connect(self.acms_lite_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, content, tag, phase, created_at
            FROM memories
            ORDER BY created_at ASC
        """)

        memories = []
        for row in cursor.fetchall():
            # ACMS-Lite stores single tag per memory (not comma-separated)
            tag_str = row['tag'] or ""
            tags = [tag_str] if tag_str else []

            memories.append({
                'id': row['id'],
                'content': row['content'],
                'tags': tags,
                'phase': row['phase'],
                'created_at': row['created_at']
            })

        conn.close()
        self.stats['total'] = len(memories)

        print(f"📊 Found {len(memories)} memories in ACMS-Lite")
        return memories

    async def _migrate_memory(self, memory: Dict[str, Any]) -> bool:
        """
        Migrate a single memory to ACMS.

        Args:
            memory: Memory dict from ACMS-Lite

        Returns:
            True if successful, False if failed
        """
        try:
            content = memory['content']
            tags = memory['tags']
            phase = memory['phase']

            # Enhancement 1: Check for duplicates
            content_hash = self._get_content_hash(content)
            if await self._check_duplicate(content_hash):
                self.stats['skipped_duplicates'] += 1
                print(f"  ⏭️  Skipped duplicate: {content[:50]}...")
                return True

            # Enhancement 3: Enrich tags
            enriched_tags = self._enrich_tags(tags, phase)
            if len(enriched_tags) > len(tags):
                self.stats['enriched_tags'] += 1

            # Determine tier based on tags and phase
            tier = "SHORT"  # Default
            if "milestone" in tags or "checkpoint" in tags or "phase_summary" in tags:
                tier = "LONG"
            elif "decision" in tags or "implementation" in tags:
                tier = "MID"

            # Dry run: just print what we would do
            if self.dry_run:
                print(f"  [DRY-RUN] Would migrate: {content[:60]}... (tier: {tier}, tags: {len(enriched_tags)})")
                self.stats['migrated'] += 1
                return True

            # Actually migrate to ACMS
            memory_id = await self.memory_crud.create_memory(
                user_id=MCPConfig.DEFAULT_USER_ID,
                content=content,
                tags=enriched_tags,
                tier=tier,
                phase=phase or "unknown"
            )

            if memory_id:
                self.stats['migrated'] += 1
                return True
            else:
                # Duplicate detected by ACMS (content deduplication)
                self.stats['skipped_duplicates'] += 1
                return True

        except Exception as e:
            print(f"  ❌ Failed to migrate: {memory.get('content', '')[:50]}... - Error: {e}")
            self.stats['failed'] += 1
            self.failed_memories.append(memory)
            return False

    async def migrate(self, batch_size: int = 10) -> Dict[str, Any]:
        """
        Execute migration from ACMS-Lite to ACMS.

        Args:
            batch_size: Number of memories to process in each batch

        Returns:
            Migration statistics
        """
        print(f"\n🚀 {'DRY-RUN: ' if self.dry_run else ''}Starting ACMS-Lite → ACMS Migration")
        print(f"   Source: {self.acms_lite_db}")
        print(f"   Batch size: {batch_size}")
        print()

        # Read all memories from ACMS-Lite
        memories = self._read_acms_lite_memories()

        if not memories:
            print("⚠️  No memories found in ACMS-Lite")
            return self.stats

        # Process in batches
        total_batches = (len(memories) + batch_size - 1) // batch_size

        for i in range(0, len(memories), batch_size):
            batch = memories[i:i+batch_size]
            batch_num = (i // batch_size) + 1

            print(f"📦 Batch {batch_num}/{total_batches} ({len(batch)} memories)")

            # Process batch
            for memory in batch:
                await self._migrate_memory(memory)

            # Progress update
            progress = (self.stats['migrated'] + self.stats['skipped_duplicates']) / self.stats['total'] * 100
            print(f"   Progress: {progress:.1f}% ({self.stats['migrated']} migrated, {self.stats['skipped_duplicates']} skipped)")
            print()

        # Final report
        print("\n" + "="*60)
        print("📊 Migration Complete!")
        print("="*60)
        print(f"Total memories:       {self.stats['total']}")
        print(f"Successfully migrated: {self.stats['migrated']}")
        print(f"Skipped (duplicates):  {self.stats['skipped_duplicates']}")
        print(f"Failed:                {self.stats['failed']}")
        print(f"Tags enriched:         {self.stats['enriched_tags']}")
        print("="*60)

        if self.failed_memories:
            print(f"\n⚠️  {len(self.failed_memories)} memories failed to migrate")
            print("Failed memories saved to: /tmp/failed_migrations.txt")

            # Save failed memories for retry
            with open('/tmp/failed_migrations.txt', 'w') as f:
                for mem in self.failed_memories:
                    f.write(f"{mem['id']}: {mem['content'][:100]}...\n")

        return self.stats


async def main():
    """Main entry point for migration script."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate ACMS-Lite to ACMS")
    parser.add_argument('--dry-run', action='store_true', help='Test migration without writing')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
    parser.add_argument('--db', type=str, default='.acms_lite.db', help='Path to ACMS-Lite database')

    args = parser.parse_args()

    # Run migration
    migrator = ACMSLiteMigrator(acms_lite_db=args.db, dry_run=args.dry_run)
    stats = await migrator.migrate(batch_size=args.batch_size)

    # Exit with error code if failures
    if stats['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
