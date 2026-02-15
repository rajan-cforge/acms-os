#!/usr/bin/env python3
"""Create ACMS_Knowledge_v2 schema in Weaviate.

This collection stores structured knowledge entries with:
- Intent analysis (the "why")
- Entity extraction
- Topic clustering (dynamic)
- Key facts

Usage:
    python3 scripts/create_knowledge_v2_schema.py
"""

import requests
import json

WEAVIATE_URL = "http://localhost:40480"

SCHEMA = {
    "class": "ACMS_Knowledge_v2",
    "description": "Structured knowledge entries with intent, entities, and relationships",
    "vectorizer": "none",  # We generate embeddings externally
    "vectorIndexConfig": {
        "distance": "cosine"
    },
    "properties": [
        # Core Content
        {
            "name": "canonical_query",
            "dataType": ["text"],
            "description": "Normalized, cleaned version of the question"
        },
        {
            "name": "answer_summary",
            "dataType": ["text"],
            "description": "Condensed 2-3 sentence summary of the answer"
        },
        {
            "name": "full_answer",
            "dataType": ["text"],
            "description": "Complete answer for reference"
        },

        # Intent & Context (THE "WHY")
        {
            "name": "primary_intent",
            "dataType": ["text"],
            "description": "What the user is fundamentally trying to achieve"
        },
        {
            "name": "problem_domain",
            "dataType": ["text"],
            "description": "The area/field this relates to"
        },
        {
            "name": "why_context",
            "dataType": ["text"],
            "description": "Human-readable explanation of WHY the user is asking"
        },
        {
            "name": "user_context_signals",
            "dataType": ["text[]"],
            "description": "Inferred context clues about the user"
        },

        # Entities & Relationships (stored as JSON strings)
        {
            "name": "entities_json",
            "dataType": ["text"],
            "description": "JSON array of extracted entities"
        },
        {
            "name": "relations_json",
            "dataType": ["text"],
            "description": "JSON array of entity relationships"
        },

        # Topic Clustering (Dynamic)
        {
            "name": "topic_cluster",
            "dataType": ["text"],
            "description": "Primary topic cluster slug (dynamically discovered)"
        },
        {
            "name": "related_topics",
            "dataType": ["text[]"],
            "description": "Related topic clusters"
        },

        # Extracted Facts
        {
            "name": "key_facts",
            "dataType": ["text[]"],
            "description": "Atomic facts extracted from the answer"
        },

        # Metadata
        {
            "name": "user_id",
            "dataType": ["text"],
            "description": "User identifier"
        },
        {
            "name": "source_query_id",
            "dataType": ["text"],
            "description": "Link to original query in query_history"
        },
        {
            "name": "extraction_model",
            "dataType": ["text"],
            "description": "Model used for extraction (claude-sonnet-4)"
        },
        {
            "name": "extraction_confidence",
            "dataType": ["number"],
            "description": "Confidence score of the extraction"
        },
        {
            "name": "created_at",
            "dataType": ["text"],
            "description": "ISO timestamp of creation"
        },
        {
            "name": "usage_count",
            "dataType": ["int"],
            "description": "How often this knowledge has been retrieved"
        },
        {
            "name": "feedback_score",
            "dataType": ["number"],
            "description": "Aggregate user feedback score"
        }
    ]
}


def main():
    print("=" * 60)
    print("Creating ACMS_Knowledge_v2 Schema")
    print("=" * 60)

    # Check if collection already exists
    response = requests.get(f"{WEAVIATE_URL}/v1/schema/ACMS_Knowledge_v2")
    if response.status_code == 200:
        print("\n⚠️  ACMS_Knowledge_v2 already exists!")
        user_input = input("Delete and recreate? (yes/no): ")
        if user_input.lower() == "yes":
            delete_resp = requests.delete(f"{WEAVIATE_URL}/v1/schema/ACMS_Knowledge_v2")
            if delete_resp.status_code in [200, 204]:
                print("✓ Deleted existing collection")
            else:
                print(f"✗ Failed to delete: {delete_resp.text}")
                return
        else:
            print("Aborted.")
            return

    # Create the collection
    response = requests.post(
        f"{WEAVIATE_URL}/v1/schema",
        json=SCHEMA
    )

    if response.status_code in [200, 201]:
        print("\n✅ ACMS_Knowledge_v2 created successfully!")
        print(f"\nProperties ({len(SCHEMA['properties'])}):")
        for prop in SCHEMA['properties']:
            print(f"  - {prop['name']}: {prop['dataType'][0]}")
    else:
        print(f"\n✗ Failed to create: {response.status_code}")
        print(response.text)
        return

    # Verify
    print("\n" + "=" * 60)
    print("Verifying...")
    verify = requests.get(f"{WEAVIATE_URL}/v1/schema/ACMS_Knowledge_v2")
    if verify.status_code == 200:
        data = verify.json()
        print(f"✓ Collection verified: {data['class']}")
        print(f"✓ Properties: {len(data['properties'])}")
    else:
        print(f"✗ Verification failed: {verify.status_code}")


if __name__ == "__main__":
    main()
