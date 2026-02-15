#!/usr/bin/env python3
"""
Test ACMS Self-Awareness - Interactive Examples

Run these commands to test ACMS's knowledge of its own build history.
"""

import asyncio
from src.storage.memory_crud import MemoryCRUD
from src.mcp.config import MCPConfig


async def store_memory_example():
    """Example: Store a new memory in ACMS"""
    print("=" * 70)
    print("EXAMPLE 1: Storing a Memory")
    print("=" * 70)

    crud = MemoryCRUD()

    memory_id = await crud.create_memory(
        user_id=MCPConfig.DEFAULT_USER_ID,
        content="User learned how to query ACMS for build history using semantic search",
        tags=["user_learning", "acms_usage", "phase-2.5"],
        tier="SHORT"
    )

    print(f"✅ Stored memory with ID: {memory_id}")
    print()


async def search_build_history():
    """Example: Search ACMS's build history"""
    print("=" * 70)
    print("EXAMPLE 2: Searching Build History")
    print("=" * 70)

    crud = MemoryCRUD()

    queries = [
        "What is ACMS and how was it built?",
        "What technologies does ACMS use?",
        "How does encryption work in ACMS?",
        "What were the Phase 1 infrastructure problems?",
        "What MCP tools were implemented in Phase 2B?",
    ]

    for query in queries:
        print(f"\n🔍 Query: {query}")
        print("-" * 70)

        results = await crud.search_memories(
            query=query,
            user_id=MCPConfig.DEFAULT_USER_ID,
            limit=2
        )

        if results:
            for i, memory in enumerate(results, 1):
                print(f"\n{i}. [{memory['tier']}] {memory['content'][:150]}...")
                print(f"   Tags: {', '.join(memory['tags'][:5])}")
        else:
            print("   No results found")

        print()


async def list_by_phase():
    """Example: List memories by phase"""
    print("=" * 70)
    print("EXAMPLE 3: List Memories by Phase")
    print("=" * 70)

    crud = MemoryCRUD()

    phases = {
        "phase-0": "Bootstrap (ACMS-Lite implementation)",
        "phase-1": "Infrastructure (Docker, databases)",
        "phase-2a": "Storage Layer (PostgreSQL, Weaviate, encryption)",
        "phase-2b": "MCP Server (FastMCP, Claude Desktop integration)"
    }

    for phase_tag, description in phases.items():
        results = await crud.list_memories(
            user_id=MCPConfig.DEFAULT_USER_ID,
            tag=phase_tag,
            limit=3
        )

        print(f"\n📦 {phase_tag.upper()}: {description}")
        print(f"   Found {len(results)} memories")

        if results:
            print(f"   Sample: {results[0]['content'][:100]}...")
        print()


async def list_milestones():
    """Example: List major milestones"""
    print("=" * 70)
    print("EXAMPLE 4: List Major Milestones")
    print("=" * 70)

    crud = MemoryCRUD()

    results = await crud.list_memories(
        user_id=MCPConfig.DEFAULT_USER_ID,
        tag="milestone",
        limit=10
    )

    print(f"\n🎯 Found {len(results)} major milestones:\n")

    for i, memory in enumerate(results, 1):
        print(f"{i}. {memory['content'][:100]}...")
        print(f"   Phase: {memory['phase']} | Created: {memory['created_at']}")
        print()


async def get_specific_memory():
    """Example: Get a specific memory by ID"""
    print("=" * 70)
    print("EXAMPLE 5: Get Specific Memory by ID")
    print("=" * 70)

    crud = MemoryCRUD()

    # First, search for a milestone
    results = await crud.search_memories(
        query="Phase 2B MCP Server integration complete",
        user_id=MCPConfig.DEFAULT_USER_ID,
        limit=1
    )

    if results:
        memory_id = results[0]['memory_id']
        print(f"\n📋 Found memory: {memory_id}")

        # Now get the full memory
        memory = await crud.get_memory(memory_id, decrypt=True)

        print(f"\nFull Memory Details:")
        print(f"  Content: {memory['content'][:200]}...")
        print(f"  Tags: {memory['tags']}")
        print(f"  Tier: {memory['tier']}")
        print(f"  Phase: {memory['phase']}")
        print(f"  Access Count: {memory['access_count']}")
        print(f"  Created: {memory['created_at']}")
    else:
        print("   No memory found")

    print()


async def main():
    """Run all examples"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "ACMS SELF-AWARENESS TEST SUITE" + " " * 23 + "║")
    print("║" + " " * 15 + "Interactive Examples for Users" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    # Run all examples
    await store_memory_example()
    await search_build_history()
    await list_by_phase()
    await list_milestones()
    await get_specific_memory()

    print("=" * 70)
    print("✅ ALL EXAMPLES COMPLETE")
    print("=" * 70)
    print()
    print("You can now:")
    print("1. Modify these examples for your own queries")
    print("2. Use Claude Desktop to query ACMS naturally")
    print("3. Build your own scripts using MemoryCRUD API")
    print()


if __name__ == "__main__":
    asyncio.run(main())
