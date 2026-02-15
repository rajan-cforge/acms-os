#!/usr/bin/env python3
"""
ACMS CLI - Command-line interface for ACMS operations

Provides easy command-line access to ACMS functionality:
- Search memories semantically
- Store new memories
- List memories with filters
- Get specific memories
- View statistics

Usage:
    python3 -m src.scripts.acms_cli search "query text" [--limit 10] [--tags tag1,tag2]
    python3 -m src.scripts.acms_cli store "content" --tags tag1,tag2 [--tier SHORT]
    python3 -m src.scripts.acms_cli list [--tag phase-0] [--tier LONG] [--limit 20]
    python3 -m src.scripts.acms_cli get <memory_id>
    python3 -m src.scripts.acms_cli stats
"""

import sys
import asyncio
import argparse
from typing import Optional, List
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.storage.memory_crud import MemoryCRUD
from src.mcp.config import MCPConfig


class ACMSCLI:
    """Command-line interface for ACMS."""

    def __init__(self):
        self.crud = MemoryCRUD()
        self.user_id = MCPConfig.DEFAULT_USER_ID

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self.crud, 'weaviate'):
            try:
                self.crud.weaviate.close()
            except:
                pass

    async def search(self, query: str, limit: int = 10, tags: Optional[List[str]] = None):
        """Search memories semantically.

        Args:
            query: Search query
            limit: Max results
            tags: Optional tag filters
        """
        print(f"\n🔍 Searching for: '{query}'")
        print("=" * 80)

        results = await self.crud.search_memories(
            query=query,
            user_id=self.user_id,
            limit=limit
        )

        # Filter by tags if specified
        if tags:
            results = [r for r in results if any(tag in r.get('tags', []) for tag in tags)]

        if not results:
            print("❌ No results found")
            return

        print(f"✅ Found {len(results)} results:\n")

        for i, memory in enumerate(results, 1):
            print(f"{i}. [{memory['tier']}] {memory['content'][:200]}...")
            print(f"   Tags: {', '.join(memory['tags'][:8])}")
            print(f"   Phase: {memory.get('phase', 'N/A')}")
            print(f"   Distance: {memory.get('semantic_distance', 'N/A'):.4f}")
            print(f"   ID: {memory['memory_id']}")
            print()

    async def store(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        tier: str = "SHORT",
        phase: Optional[str] = None
    ):
        """Store a new memory.

        Args:
            content: Memory content
            tags: Optional tags
            tier: Memory tier (SHORT/MID/LONG)
            phase: Optional phase
        """
        print(f"\n💾 Storing new memory...")
        print("=" * 80)

        memory_id = await self.crud.create_memory(
            user_id=self.user_id,
            content=content,
            tags=tags or [],
            tier=tier,
            phase=phase
        )

        if memory_id:
            print(f"✅ Stored memory: {memory_id}")
            print(f"   Content: {content[:100]}...")
            print(f"   Tags: {tags}")
            print(f"   Tier: {tier}")
            print(f"   Phase: {phase or 'N/A'}")
        else:
            print(f"⚠️  Duplicate detected - memory not stored")

    async def list_memories(
        self,
        tag: Optional[str] = None,
        phase: Optional[str] = None,
        tier: Optional[str] = None,
        limit: int = 20
    ):
        """List memories with filters.

        Args:
            tag: Optional tag filter
            phase: Optional phase filter
            tier: Optional tier filter
            limit: Max results
        """
        print(f"\n📋 Listing memories...")
        print("=" * 80)

        results = await self.crud.list_memories(
            user_id=self.user_id,
            tag=tag,
            phase=phase,
            tier=tier,
            limit=limit
        )

        if not results:
            print("❌ No results found")
            return

        print(f"✅ Found {len(results)} memories:\n")

        for i, memory in enumerate(results, 1):
            print(f"{i}. [{memory['tier']}] {memory['content'][:150]}...")
            print(f"   Tags: {', '.join(memory['tags'][:8])}")
            print(f"   Phase: {memory.get('phase', 'N/A')} | Created: {memory['created_at']}")
            print(f"   ID: {memory['memory_id']}")
            print()

    async def get_memory(self, memory_id: str, decrypt: bool = True):
        """Get a specific memory by ID.

        Args:
            memory_id: Memory UUID
            decrypt: Whether to decrypt content
        """
        print(f"\n📄 Retrieving memory: {memory_id}")
        print("=" * 80)

        memory = await self.crud.get_memory(memory_id, decrypt=decrypt)

        if not memory:
            print(f"❌ Memory not found: {memory_id}")
            return

        print(f"✅ Memory found:\n")
        print(f"Content:\n{memory['content']}\n")
        print(f"Details:")
        print(f"  Memory ID: {memory['memory_id']}")
        print(f"  User ID: {memory['user_id']}")
        print(f"  Tier: {memory['tier']}")
        print(f"  Phase: {memory.get('phase', 'N/A')}")
        print(f"  Tags: {', '.join(memory['tags'])}")
        print(f"  CRS Score: {memory['crs_score']}")
        print(f"  Access Count: {memory['access_count']}")
        print(f"  Created: {memory['created_at']}")
        print(f"  Updated: {memory['updated_at']}")
        print(f"  Last Accessed: {memory['last_accessed']}")

        if memory.get('decrypted_content'):
            print(f"\n  Decrypted Content:\n  {memory['decrypted_content'][:200]}...")

    async def stats(self):
        """Show ACMS statistics."""
        print(f"\n📊 ACMS Statistics")
        print("=" * 80)

        # Count by phase
        print("\n📦 Phase Distribution:")
        for phase_tag in ['phase-0', 'phase-1', 'phase-2a', 'phase-2b', 'phase-2.5']:
            results = await self.crud.list_memories(
                user_id=self.user_id,
                tag=phase_tag,
                limit=500
            )
            phase_name = {
                'phase-0': 'Phase 0 (Bootstrap)',
                'phase-1': 'Phase 1 (Infrastructure)',
                'phase-2a': 'Phase 2A (Storage Layer)',
                'phase-2b': 'Phase 2B (MCP Server)',
                'phase-2.5': 'Phase 2.5 (Self-Aware ACMS)'
            }.get(phase_tag, phase_tag)
            print(f"  {phase_name}: {len(results)} memories")

        # Count by tier
        print("\n🎯 Tier Distribution:")
        for tier in ['SHORT', 'MID', 'LONG']:
            results = await self.crud.list_memories(
                user_id=self.user_id,
                tier=tier,
                limit=500
            )
            print(f"  {tier}: {len(results)} memories")

        # Count by tag type
        print("\n🏷️  Common Tags:")
        tag_counts = {}
        all_memories = await self.crud.list_memories(
            user_id=self.user_id,
            limit=500
        )
        for memory in all_memories:
            for tag in memory['tags']:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Top 10 tags
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for tag, count in top_tags:
            print(f"  {tag}: {count}")

        # Total count
        total = len(all_memories)
        print(f"\n📈 Total Memories: {total}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ACMS CLI - Command-line interface for ACMS operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for memories
  python3 -m src.scripts.acms_cli search "Phase 2 storage implementation"
  python3 -m src.scripts.acms_cli search "encryption" --tags phase-2a --limit 5

  # Store a new memory
  python3 -m src.scripts.acms_cli store "Learned about Docker networking" --tags docker,learning --tier SHORT

  # List memories
  python3 -m src.scripts.acms_cli list --tag milestone
  python3 -m src.scripts.acms_cli list --phase phase-1 --limit 10

  # Get specific memory
  python3 -m src.scripts.acms_cli get <memory-uuid>

  # View statistics
  python3 -m src.scripts.acms_cli stats
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search memories semantically')
    search_parser.add_argument('query', type=str, help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Max results (default: 10)')
    search_parser.add_argument('--tags', type=str, help='Comma-separated tag filters')

    # Store command
    store_parser = subparsers.add_parser('store', help='Store a new memory')
    store_parser.add_argument('content', type=str, help='Memory content')
    store_parser.add_argument('--tags', type=str, help='Comma-separated tags')
    store_parser.add_argument('--tier', type=str, default='SHORT', choices=['SHORT', 'MID', 'LONG'],
                             help='Memory tier (default: SHORT)')
    store_parser.add_argument('--phase', type=str, help='Phase identifier')

    # List command
    list_parser = subparsers.add_parser('list', help='List memories with filters')
    list_parser.add_argument('--tag', type=str, help='Tag filter')
    list_parser.add_argument('--phase', type=str, help='Phase filter')
    list_parser.add_argument('--tier', type=str, choices=['SHORT', 'MID', 'LONG'], help='Tier filter')
    list_parser.add_argument('--limit', type=int, default=20, help='Max results (default: 20)')

    # Get command
    get_parser = subparsers.add_parser('get', help='Get a specific memory by ID')
    get_parser.add_argument('memory_id', type=str, help='Memory UUID')
    get_parser.add_argument('--no-decrypt', action='store_true', help='Skip decryption')

    # Stats command
    subparsers.add_parser('stats', help='Show ACMS statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = ACMSCLI()

    try:
        if args.command == 'search':
            tags = args.tags.split(',') if args.tags else None
            await cli.search(args.query, args.limit, tags)

        elif args.command == 'store':
            tags = args.tags.split(',') if args.tags else None
            await cli.store(args.content, tags, args.tier, args.phase)

        elif args.command == 'list':
            await cli.list_memories(args.tag, args.phase, args.tier, args.limit)

        elif args.command == 'get':
            await cli.get_memory(args.memory_id, decrypt=not args.no_decrypt)

        elif args.command == 'stats':
            await cli.stats()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up resources
        cli.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
