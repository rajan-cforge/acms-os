#!/usr/bin/env python3
"""
Import Claude conversations from official Claude.ai export

Usage:
    python3 scripts/import_claude_export.py <export_file_path>
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / ".env")

from src.importers.claude_importer import ClaudeImporter


async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/import_claude_export.py <export_file_path>")
        print("Example: python3 scripts/import_claude_export.py ~/Downloads/data-2025-10-22-20-59-23-batch-0000/conversations.json")
        sys.exit(1)

    file_path = sys.argv[1]

    print(f"🚀 Starting Claude conversation import from: {file_path}")
    print("=" * 80)

    # Initialize importer
    importer = ClaudeImporter()
    await importer.initialize()

    # Run import
    result = await importer.import_conversations(file_path)

    # Print results
    print("\n" + "=" * 80)
    print("✅ Import Complete!")
    print("=" * 80)
    print(f"📊 Statistics:")
    print(f"  - Conversations imported: {result['conversations_imported']}")
    print(f"  - Turns created: {result['turns_created']}")
    print(f"  - Errors: {result['errors']}")
    print(f"  - Duration: {result.get('duration_seconds', 0):.2f}s")

    if result['errors'] > 0:
        print(f"\n⚠️  {result['errors']} errors encountered during import")

    print("\n🎯 Next Steps:")
    print("  1. Test search: Ask ACMS about your Claude conversations")
    print("  2. Verify data: Check conversation_threads and conversation_turns tables")
    print("  3. Test UniversalSearchEngine with Claude data")


if __name__ == "__main__":
    asyncio.run(main())
