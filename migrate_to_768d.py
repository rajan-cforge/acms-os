"""Migration script to upgrade from 384d to 768d embeddings.

⚠️  WARNING: This will DELETE all existing embeddings in Weaviate!
    PostgreSQL metadata will be preserved, but vector search won't work
    until memories are re-embedded with OpenAI.

Run this ONCE before using OpenAI embeddings.
"""

import sys
from src.storage.weaviate_client import WeaviateClient


def migrate_to_768d():
    """Delete old 384d collection and create new 768d collection."""

    print("\n⚠️  MIGRATION: 384d → 768d embeddings")
    print("="*60)
    print("This will DELETE the existing ACMS_MemoryItems_v1 collection")
    print("with 384-dimensional embeddings and recreate it for 768d.")
    print()
    print("What will happen:")
    print("  ✅ PostgreSQL data (content, metadata) - PRESERVED")
    print("  ❌ Weaviate vectors (384d embeddings) - DELETED")
    print("  ✅ New Weaviate collection (768d) - CREATED")
    print()
    print("After migration:")
    print("  - Existing memories won't be searchable until re-embedded")
    print("  - New memories will use OpenAI 768d embeddings")
    print("="*60)

    response = input("\nType 'yes' to continue: ")
    if response.lower() != 'yes':
        print("❌ Migration cancelled")
        return False

    print("\n🔄 Connecting to Weaviate...")
    client = WeaviateClient()

    # Check if old collection exists
    collection_name = "ACMS_MemoryItems_v1"
    if client.collection_exists(collection_name):
        print(f"📊 Found existing collection: {collection_name}")

        # Get count before deletion
        count = client.count_vectors(collection_name)
        print(f"   - Contains {count} vectors (384d)")

        # Delete collection
        print(f"\n🗑️  Deleting {collection_name}...")
        client._client.collections.delete(collection_name)
        print(f"✅ Deleted {collection_name}")
    else:
        print(f"ℹ️  Collection {collection_name} doesn't exist (clean install)")

    # Create new collection with 768d support
    print(f"\n🆕 Creating new {collection_name} with 768d support...")
    client.create_acms_collection()
    print(f"✅ Created {collection_name} (768 dimensions)")

    # Verify
    schema = client.get_collection_schema(collection_name)
    print(f"\n✅ Migration complete!")
    print(f"   Collection: {schema['name']}")
    print(f"   Description: {schema['description']}")

    client.close()

    print("\n📝 Next steps:")
    print("   1. Existing memories in PostgreSQL are safe")
    print("   2. New memories will automatically use OpenAI 768d embeddings")
    print("   3. To make old memories searchable, you'll need to re-embed them")
    print("      (This can be done later with a re-embedding script)")

    return True


if __name__ == "__main__":
    try:
        success = migrate_to_768d()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
