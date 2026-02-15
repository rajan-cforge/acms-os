"""Migrate Weaviate vectors to include privacy_level property.

Since Weaviate doesn't support schema changes on existing collections,
we need to batch-update all existing vectors to include privacy_level='INTERNAL'.

This script:
1. Fetches all vectors from ACMS_MemoryItems_v1
2. Updates each with privacy_level='INTERNAL'
3. Verifies all vectors have privacy_level
"""

import asyncio
import sys
from typing import List, Dict, Any

sys.path.insert(0, '/path/to/acms')

from src.storage.weaviate_client import WeaviateClient
from src.storage.database import get_session
from src.storage.models import MemoryItem
from sqlalchemy import select


async def migrate_weaviate_privacy():
    """Migrate all Weaviate vectors to include privacy_level."""

    print("🚀 Starting Weaviate privacy migration...")

    # Connect to Weaviate
    client = WeaviateClient()

    try:
        # Get collection
        collection = client._client.collections.get("ACMS_MemoryItems_v1")

        # Fetch all objects
        print("📥 Fetching all vectors from Weaviate...")
        response = collection.iterator(include_vector=False)

        vectors_to_update = []
        for obj in response:
            vectors_to_update.append({
                'uuid': str(obj.uuid),
                'properties': obj.properties
            })

        print(f"Found {len(vectors_to_update)} vectors to update")

        # Update each vector with privacy_level='INTERNAL'
        print("🔄 Updating vectors with privacy_level='INTERNAL'...")
        updated_count = 0
        failed_count = 0

        for vec in vectors_to_update:
            try:
                # Add privacy_level to properties
                updated_props = vec['properties'].copy()
                updated_props['privacy_level'] = 'INTERNAL'

                # Update vector
                collection.data.update(
                    uuid=vec['uuid'],
                    properties=updated_props
                )
                updated_count += 1

                if updated_count % 50 == 0:
                    print(f"  ✓ Updated {updated_count}/{len(vectors_to_update)} vectors...")

            except Exception as e:
                print(f"  ✗ Failed to update {vec['uuid']}: {e}")
                failed_count += 1

        print(f"\n✅ Migration complete!")
        print(f"  - Updated: {updated_count}")
        print(f"  - Failed: {failed_count}")
        print(f"  - Total: {len(vectors_to_update)}")

        # Verify migration
        print("\n🔍 Verifying migration...")
        response = collection.query.fetch_objects(limit=5)
        for obj in response.objects:
            has_privacy = 'privacy_level' in obj.properties
            privacy_val = obj.properties.get('privacy_level', 'MISSING')
            print(f"  Sample: {obj.properties.get('memory_id', 'unknown')[:8]}... privacy_level={privacy_val} ({'✓' if has_privacy else '✗'})")

        return updated_count, failed_count

    finally:
        client.close()


if __name__ == "__main__":
    updated, failed = asyncio.run(migrate_weaviate_privacy())

    if failed > 0:
        print(f"\n⚠️  Warning: {failed} vectors failed to update")
        sys.exit(1)
    else:
        print(f"\n🎉 All {updated} vectors successfully migrated!")
        sys.exit(0)
