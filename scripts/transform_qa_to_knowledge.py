#!/usr/bin/env python3
"""
Transform Q&A Memories into Knowledge Facts

This background job:
1. Reads Q&A pairs from ACMS_MemoryItems_v1 (the polluted collection)
2. Uses OpenAI to extract knowledge facts from each Q&A
3. Stores extracted facts in ACMS_Knowledge_v1 (clean collection)
4. Tracks progress in PostgreSQL to allow resume

Usage:
    # Process 100 memories (for testing)
    python scripts/transform_qa_to_knowledge.py --limit 100

    # Process all memories (will take ~50-100 hours)
    python scripts/transform_qa_to_knowledge.py --all

    # Resume from last checkpoint
    python scripts/transform_qa_to_knowledge.py --resume

Rate Limits:
    - OpenAI: ~3500 requests/minute for gpt-3.5-turbo
    - We process 1 memory/second to be safe (~3600/hour)
    - 94K memories = ~26 hours at this rate
"""

import os
import sys
import json
import time
import logging
import argparse
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

from openai import OpenAI
import weaviate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/qa_transform.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "localhost")
WEAVIATE_PORT = int(os.getenv("WEAVIATE_PORT", "40480"))
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "40481"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BATCH_SIZE = 50
RATE_LIMIT_DELAY = 0.5  # seconds between API calls

# Extraction prompt
EXTRACTION_PROMPT = """You are a knowledge extraction system. Given a Q&A pair, extract standalone knowledge facts.

Rules:
1. Extract ONLY factual information that would be useful to remember
2. Convert questions into declarative statements
3. Remove conversational fluff
4. Return 0-3 facts (0 if the Q&A has no useful knowledge)
5. Each fact should be self-contained (understandable without context)

Q&A Input:
{qa_content}

Output format (JSON array of strings):
["fact 1", "fact 2"]

If no useful facts, return: []
"""


class QATransformer:
    """Transform Q&A memories into knowledge facts."""

    def __init__(self):
        """Initialize connections."""
        # Weaviate connection with proper ports
        self.weaviate = weaviate.connect_to_local(
            host=WEAVIATE_HOST,
            port=WEAVIATE_PORT,
            grpc_port=WEAVIATE_GRPC_PORT
        )

        # OpenAI client
        self.openai = OpenAI(api_key=OPENAI_API_KEY)

        # Stats
        self.stats = {
            "processed": 0,
            "facts_extracted": 0,
            "skipped": 0,
            "errors": 0,
            "start_time": datetime.now().isoformat()
        }

        # Progress tracking
        self.progress_file = "/tmp/qa_transform_progress.json"
        self.processed_ids = self._load_progress()

        logger.info(f"Initialized QATransformer. Already processed: {len(self.processed_ids)}")

    def _load_progress(self) -> set:
        """Load previously processed IDs for resume."""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                return set(data.get("processed_ids", []))
        return set()

    def _save_progress(self):
        """Save progress for resume capability."""
        with open(self.progress_file, 'w') as f:
            json.dump({
                "processed_ids": list(self.processed_ids),
                "stats": self.stats,
                "last_update": datetime.now().isoformat()
            }, f)

    def get_qa_memories(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Fetch Q&A memories from polluted collection."""
        try:
            collection = self.weaviate.collections.get("ACMS_MemoryItems_v1")

            # Query memories that look like Q&A
            results = collection.query.fetch_objects(
                limit=limit,
                offset=offset,
                include_vector=True
            )

            memories = []
            for obj in results.objects:
                content = obj.properties.get("content", "")
                # Filter for Q&A format
                if self._is_qa_format(content):
                    memories.append({
                        "id": str(obj.uuid),
                        "content": content,
                        "vector": obj.vector,
                        "properties": obj.properties
                    })

            logger.info(f"Fetched {len(memories)} Q&A memories (offset={offset})")
            return memories

        except Exception as e:
            logger.error(f"Error fetching memories: {e}")
            return []

    def _is_qa_format(self, content: str) -> bool:
        """Check if content is Q&A format."""
        content_lower = content.lower()
        return (
            ("q:" in content_lower and "a:" in content_lower) or
            ("question:" in content_lower and "answer:" in content_lower) or
            ("user:" in content_lower and "assistant:" in content_lower)
        )

    def extract_knowledge(self, qa_content: str) -> List[str]:
        """Use OpenAI to extract knowledge facts from Q&A."""
        try:
            response = self.openai.chat.completions.create(
                model="gpt-3.5-turbo",  # Cheaper, faster for extraction
                messages=[
                    {"role": "system", "content": "You extract knowledge facts from Q&A pairs. Output JSON array only."},
                    {"role": "user", "content": EXTRACTION_PROMPT.format(qa_content=qa_content)}
                ],
                temperature=0.1,
                max_tokens=500
            )

            # Parse response
            content = response.choices[0].message.content.strip()

            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            facts = json.loads(content)
            return facts if isinstance(facts, list) else []

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extraction response: {e}")
            return []
        except Exception as e:
            logger.error(f"OpenAI extraction error: {e}")
            self.stats["errors"] += 1
            return []

    def store_knowledge_fact(self, fact: str, source_id: str, original_properties: Dict) -> Optional[str]:
        """Store extracted fact in ACMS_Knowledge_v1."""
        try:
            # Generate embedding for the fact
            # Use dimensions=768 to match ACMS_Knowledge_v1 collection
            embedding_response = self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=fact,
                dimensions=768
            )
            vector = embedding_response.data[0].embedding

            # Create unique ID based on content hash
            content_hash = hashlib.sha256(fact.encode()).hexdigest()[:16]
            fact_id = str(uuid4())

            # Get or create knowledge collection
            collection = self.weaviate.collections.get("ACMS_Knowledge_v1")

            # Store in Weaviate
            # Use RFC3339 format with timezone for Weaviate
            created_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

            collection.data.insert(
                properties={
                    "content": fact,
                    "source_type": "extracted_from_qa",
                    "source_id": source_id,
                    "content_hash": content_hash,
                    "user_id": original_properties.get("user_id", ""),
                    "privacy_level": original_properties.get("privacy_level", "INTERNAL"),
                    "created_at": created_at,
                    "confidence": 0.8,  # Extracted facts have high confidence
                    "tags": ["auto_extracted", "from_qa"]
                },
                vector=vector,
                uuid=fact_id
            )

            self.stats["facts_extracted"] += 1
            return fact_id

        except Exception as e:
            logger.error(f"Error storing fact: {e}")
            return None

    def process_memory(self, memory: Dict) -> int:
        """Process a single Q&A memory. Returns number of facts extracted."""
        memory_id = memory["id"]

        # Skip if already processed
        if memory_id in self.processed_ids:
            self.stats["skipped"] += 1
            return 0

        content = memory["content"]

        # Extract knowledge facts
        facts = self.extract_knowledge(content)

        # Store each fact
        facts_stored = 0
        for fact in facts:
            if len(fact) > 20:  # Skip very short facts
                result = self.store_knowledge_fact(
                    fact=fact,
                    source_id=memory_id,
                    original_properties=memory.get("properties", {})
                )
                if result:
                    facts_stored += 1

        # Mark as processed
        self.processed_ids.add(memory_id)
        self.stats["processed"] += 1

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

        return facts_stored

    def run(self, limit: Optional[int] = None, resume: bool = True):
        """Run the transformation job."""
        logger.info("=" * 60)
        logger.info("Starting Q&A → Knowledge transformation")
        logger.info(f"Limit: {limit or 'ALL'}, Resume: {resume}")
        logger.info("=" * 60)

        if not resume:
            self.processed_ids = set()

        offset = 0
        total_processed = 0
        target = limit or float('inf')

        try:
            while total_processed < target:
                # Fetch batch
                memories = self.get_qa_memories(limit=BATCH_SIZE, offset=offset)

                if not memories:
                    logger.info("No more memories to process")
                    break

                # Process batch
                for memory in memories:
                    if total_processed >= target:
                        break

                    facts = self.process_memory(memory)
                    total_processed += 1

                    # Progress update every 10 memories
                    if total_processed % 10 == 0:
                        self._save_progress()
                        logger.info(
                            f"Progress: {total_processed} processed, "
                            f"{self.stats['facts_extracted']} facts extracted, "
                            f"{self.stats['errors']} errors"
                        )

                offset += BATCH_SIZE

        except KeyboardInterrupt:
            logger.info("Interrupted by user. Saving progress...")
        finally:
            self._save_progress()
            self._print_summary()

    def _print_summary(self):
        """Print final summary."""
        logger.info("=" * 60)
        logger.info("TRANSFORMATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total processed: {self.stats['processed']}")
        logger.info(f"Facts extracted: {self.stats['facts_extracted']}")
        logger.info(f"Skipped (already done): {self.stats['skipped']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Progress saved to: {self.progress_file}")
        logger.info("=" * 60)

    def close(self):
        """Clean up connections."""
        self.weaviate.close()


def main():
    parser = argparse.ArgumentParser(description="Transform Q&A memories to knowledge facts")
    parser.add_argument("--limit", type=int, default=100, help="Number of memories to process")
    parser.add_argument("--all", action="store_true", help="Process all memories")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from checkpoint")
    parser.add_argument("--fresh", action="store_true", help="Start fresh (ignore checkpoint)")

    args = parser.parse_args()

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set!")
        sys.exit(1)

    transformer = QATransformer()

    try:
        limit = None if args.all else args.limit
        resume = not args.fresh
        transformer.run(limit=limit, resume=resume)
    finally:
        transformer.close()


if __name__ == "__main__":
    main()
