"""
Gemini Importer - Hybrid ZIP + API Approach
Imports Gemini conversation history from ZIP exports with context preservation

Gemini Export Format:
- ZIP file containing individual JSON files (one per conversation)
- Simpler structure than ChatGPT (no complex mapping)
- Messages have: role (user/model), parts (array), create_time
- Can also fetch via Google Generative AI API (future enhancement)
"""

import json
import asyncio
import zipfile
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4, UUID

from src.storage.database import get_db_pool
from src.embeddings.openai_embeddings import OpenAIEmbeddings
from src.storage.conversation_vectors import ConversationVectorStorage


class GeminiImporter:
    """Import Gemini conversation history from ZIP exports"""

    def __init__(self):
        self.pool = None
        self.embeddings = None
        self.vector_storage = None

    async def initialize(self):
        """Initialize database connection, embedding service, and vector storage"""
        self.pool = await get_db_pool()
        self.embeddings = OpenAIEmbeddings()
        self.vector_storage = ConversationVectorStorage()

        # Setup Weaviate collections for conversations
        self.vector_storage.setup_collections()

    async def import_from_zip(
        self,
        zip_path: str,
        user_id: str = "00000000-0000-0000-0000-000000000001"
    ) -> Dict[str, Any]:
        """
        Import Gemini conversations from ZIP export file

        Args:
            zip_path: Path to Gemini ZIP export
            user_id: User ID to associate conversations with

        Returns:
            Dict with import statistics:
            - conversations_imported: Number of conversations processed
            - turns_created: Number of conversation turns stored
            - errors: Number of errors encountered
        """
        stats = {
            "conversations_imported": 0,
            "turns_created": 0,
            "errors": 0,
            "skipped": 0
        }

        try:
            # Extract and process ZIP
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Get all JSON files in ZIP
                json_files = [f for f in zf.namelist() if f.endswith('.json')]

                print(f"Found {len(json_files)} JSON files in ZIP")

                for json_file in json_files:
                    try:
                        # Read JSON content
                        with zf.open(json_file) as f:
                            conv_data = json.load(f)

                        # Process conversation
                        turn_count = await self._process_conversation(conv_data, user_id)

                        if turn_count > 0:
                            stats["conversations_imported"] += 1
                            stats["turns_created"] += turn_count
                        else:
                            stats["skipped"] += 1

                    except Exception as e:
                        print(f"Error processing {json_file}: {e}")
                        stats["errors"] += 1

            return stats

        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file")
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {zip_path}")

    async def _process_conversation(
        self,
        conv: Dict[str, Any],
        user_id: str
    ) -> int:
        """
        Process a single Gemini conversation and store as thread + turns

        Args:
            conv: Conversation dictionary from Gemini export
            user_id: User ID

        Returns:
            Number of turns created (0 if skipped due to duplicate)
        """
        # Extract conversation metadata
        conv_id = conv.get('id', str(uuid4()))
        title = conv.get('title', 'Untitled Conversation')
        messages = conv.get('messages', [])

        if not messages:
            print(f"Skipping conversation '{title}' - no messages")
            return 0

        # Parse timestamps
        create_time_str = conv.get('create_time', datetime.utcnow().isoformat())
        update_time_str = conv.get('update_time', create_time_str)

        try:
            # Handle ISO format timestamps
            created_at = datetime.fromisoformat(create_time_str.replace('Z', '+00:00'))
            updated_at = datetime.fromisoformat(update_time_str.replace('Z', '+00:00'))
        except Exception:
            created_at = datetime.utcnow()
            updated_at = created_at

        # Check for duplicate (by original_thread_id)
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow(
                """
                SELECT thread_id FROM conversation_threads
                WHERE source = 'gemini' AND original_thread_id = $1
                """,
                conv_id
            )

            if existing:
                print(f"Skipping duplicate conversation: {title}")
                return 0

        # Build full conversation text for thread embedding
        full_conversation = f"{title}\n\n"
        for msg in messages:
            role = self._normalize_role(msg.get('role', 'user'))
            content = self._extract_message_content(msg)
            full_conversation += f"{role}: {content}\n\n"

        # Generate thread embedding
        thread_embedding = self.embeddings.generate_embedding(full_conversation)

        # Store in Weaviate
        thread_vector_id = self.vector_storage.store_thread_vector(
            thread_id=str(uuid4()),  # Will be replaced by actual thread_id
            title=title,
            content=full_conversation,
            embedding=thread_embedding,
            source='gemini',
            original_thread_id=conv_id,
            created_at=created_at,
            metadata=conv.get('metadata', {}),
            tags=['gemini', 'conversation']
        )

        # Create conversation_threads record
        async with self.pool.acquire() as conn:
            thread_id = await conn.fetchval(
                """
                INSERT INTO conversation_threads (
                    thread_id, user_id, source, title, original_thread_id,
                    turn_count, created_at, imported_at, embedding_vector_id, metadata_json
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8, $9)
                RETURNING thread_id
                """,
                UUID(thread_vector_id),
                UUID(user_id),
                'gemini',
                title,
                conv_id,
                len(messages),
                created_at,
                thread_vector_id,
                json.dumps(conv.get('metadata', {}))
            )

        # Process each message as a turn
        turn_count = 0
        for idx, msg in enumerate(messages, 1):
            try:
                await self._process_turn(
                    thread_id=thread_id,
                    turn_number=idx,
                    message=msg,
                    user_id=user_id
                )
                turn_count += 1
            except Exception as e:
                print(f"Error processing turn {idx}: {e}")
                # Continue with other turns

        return turn_count

    async def _process_turn(
        self,
        thread_id: UUID,
        turn_number: int,
        message: Dict[str, Any],
        user_id: str
    ):
        """
        Process a single message turn

        Args:
            thread_id: Parent thread ID
            turn_number: Turn sequence number
            message: Message dictionary from Gemini
            user_id: User ID
        """
        # Extract message content
        msg_id = message.get('id', str(uuid4()))
        role = self._normalize_role(message.get('role', 'user'))
        content = self._extract_message_content(message)

        # Parse timestamp
        create_time_str = message.get('create_time', datetime.utcnow().isoformat())
        try:
            created_at = datetime.fromisoformat(create_time_str.replace('Z', '+00:00'))
        except Exception:
            created_at = datetime.utcnow()

        # Generate turn embedding
        turn_embedding = self.embeddings.generate_embedding(content)

        # Store in Weaviate
        turn_vector_id = self.vector_storage.store_turn_vector(
            turn_id=str(uuid4()),  # Will be replaced by actual turn_id
            thread_id=str(thread_id),
            turn_number=turn_number,
            role=role,
            content=content,
            embedding=turn_embedding,
            source='gemini',
            created_at=created_at,
            metadata=message.get('metadata', {}),
            tags=['gemini', 'conversation_turn', role]
        )

        # Create conversation_turns record
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_turns (
                    turn_id, thread_id, turn_number, role, content,
                    original_message_id, created_at, embedding_vector_id, metadata_json
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                UUID(turn_vector_id),
                thread_id,
                turn_number,
                role,
                content,
                msg_id,
                created_at,
                turn_vector_id,
                json.dumps(message.get('metadata', {}))
            )

    def _normalize_role(self, role: str) -> str:
        """
        Normalize Gemini role names to standard format

        Gemini uses 'model' for AI responses, normalize to 'assistant'
        for consistency with ChatGPT/Claude
        """
        role = role.lower()
        if role == 'model':
            return 'assistant'
        return role

    def _extract_message_content(self, message: Dict[str, Any]) -> str:
        """
        Extract text content from Gemini message parts

        Gemini messages have 'parts' array with text and potentially other content types
        """
        parts = message.get('parts', [])

        text_parts = []
        for part in parts:
            if isinstance(part, dict) and 'text' in part:
                text_parts.append(part['text'])
            elif isinstance(part, str):
                text_parts.append(part)

        # Join parts with double newline for readability
        return '\n\n'.join(text_parts) if text_parts else ""

    async def import_from_api(
        self,
        api_key: str,
        user_id: str = "00000000-0000-0000-0000-000000000001",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Import Gemini conversations via Google Generative AI API (future enhancement)

        Note: This is a stub for future implementation when Google provides
        a conversation history API endpoint.

        Args:
            api_key: Google Generative AI API key
            user_id: User ID to associate conversations with
            limit: Maximum conversations to fetch

        Returns:
            Dict with import statistics
        """
        # TODO: Implement when Google adds conversation history API
        raise NotImplementedError(
            "API import not yet available. Gemini doesn't currently provide "
            "a conversation history API endpoint. Use ZIP export instead."
        )
