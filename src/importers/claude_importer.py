"""
Claude Importer - Full Conversation Thread Storage
Imports Claude conversation history with context preservation
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from src.storage.database import get_db_pool
from src.embeddings.openai_embeddings import OpenAIEmbeddings
from src.storage.conversation_vectors import ConversationVectorStorage


class ClaudeImporter:
    """Import Claude conversation history as full threads"""

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

    async def import_conversations(
        self,
        file_path: str,
        user_id: str = "00000000-0000-0000-0000-000000000001"
    ) -> Dict[str, Any]:
        """
        Import Claude conversations from JSON export file

        Args:
            file_path: Path to Claude export JSON file
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
            "errors": 0
        }

        try:
            # Load JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Claude export format is an array of conversation objects
            conversations = data if isinstance(data, list) else [data]

            for conv in conversations:
                try:
                    turn_count = await self._process_conversation(conv, user_id)
                    stats["conversations_imported"] += 1
                    stats["turns_created"] += turn_count
                except Exception as e:
                    print(f"Error processing conversation: {e}")
                    stats["errors"] += 1

            return stats

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")

    async def _process_conversation(
        self,
        conv: Dict[str, Any],
        user_id: str
    ) -> int:
        """
        Process a single conversation and store as thread + turns

        Args:
            conv: Conversation dictionary from Claude export
            user_id: User ID

        Returns:
            Number of turns created
        """
        # Extract conversation metadata
        title = conv.get("name", "Untitled Conversation")
        conversation_uuid = conv.get("uuid", None)
        created_at_str = conv.get("created_at", None)
        updated_at_str = conv.get("updated_at", None)
        chat_messages = conv.get("chat_messages", [])

        # Parse timestamps
        created_at = self._parse_timestamp(created_at_str) if created_at_str else datetime.utcnow()
        updated_at = self._parse_timestamp(updated_at_str) if updated_at_str else created_at

        # Extract messages
        messages = self._extract_messages(chat_messages)

        if not messages:
            print(f"Skipping conversation with no valid messages: {title}")
            return 0

        # Check for duplicate conversation
        if conversation_uuid:
            async with self.pool.acquire() as conn:
                existing = await conn.fetchrow(
                    """
                    SELECT thread_id FROM conversation_threads
                    WHERE user_id = $1 AND source = 'claude' AND original_thread_id = $2
                    """,
                    user_id, conversation_uuid
                )
                if existing:
                    print(f"Skipping duplicate conversation: {title}")
                    return 0

        # Generate full conversation text for thread embedding
        full_conversation = self._format_full_conversation(messages, title)

        # Generate thread embedding
        thread_embedding = self.embeddings.generate_embedding(full_conversation)

        # Store thread embedding in Weaviate and get vector ID
        thread_vector_id = await self._store_weaviate_embedding(
            embedding=thread_embedding,
            content=full_conversation,
            metadata={
                "type": "conversation_thread",
                "source": "claude",
                "title": title,
                "turn_count": len(messages)
            }
        )

        # Create conversation_threads record
        thread_id = str(uuid4())

        metadata = {
            "uuid": conversation_uuid,
            "created_at": created_at_str,
            "updated_at": updated_at_str,
            "source": "claude"
        }

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_threads (
                    thread_id, user_id, source, title, original_thread_id,
                    created_at, turn_count, embedding_vector_id, metadata_json
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                thread_id,
                user_id,
                "claude",
                title,
                conversation_uuid,
                created_at,
                len(messages),
                thread_vector_id,
                json.dumps(metadata)
            )

        # Store each turn
        turn_count = 0
        for idx, message in enumerate(messages, start=1):
            await self._store_conversation_turn(
                thread_id=thread_id,
                turn_number=idx,
                message=message
            )
            turn_count += 1

        return turn_count

    def _extract_messages(self, chat_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract messages from Claude's chat_messages array

        Args:
            chat_messages: List of message dictionaries from Claude export

        Returns:
            List of normalized messages sorted by timestamp
        """
        messages = []

        for msg in chat_messages:
            # Extract fields
            message_uuid = msg.get("uuid", None)
            text = msg.get("text", "")
            sender = msg.get("sender", "")  # "human" or "assistant"
            created_at_str = msg.get("created_at", None)

            # Skip if no text or sender
            if not text or not sender:
                continue

            # Skip system messages (only human and assistant)
            if sender not in ["human", "assistant"]:
                continue

            # Normalize role (human -> user for consistency)
            role = "user" if sender == "human" else "assistant"

            # Parse timestamp
            created_at = self._parse_timestamp(created_at_str) if created_at_str else datetime.utcnow()

            messages.append({
                "role": role,
                "content": text,
                "timestamp": created_at,
                "message_id": message_uuid
            })

        # Sort by timestamp
        messages.sort(key=lambda m: m["timestamp"])

        return messages

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse Claude timestamp string to datetime

        Args:
            timestamp_str: ISO 8601 timestamp string (e.g., "2024-01-15T10:30:00Z")

        Returns:
            datetime object
        """
        try:
            # Handle both with and without 'Z' suffix
            if timestamp_str.endswith('Z'):
                return datetime.fromisoformat(timestamp_str[:-1])
            return datetime.fromisoformat(timestamp_str)
        except Exception:
            return datetime.utcnow()

    def _format_full_conversation(
        self,
        messages: List[Dict[str, Any]],
        title: str
    ) -> str:
        """
        Format full conversation for thread-level embedding

        Args:
            messages: List of messages
            title: Conversation title

        Returns:
            Formatted conversation text
        """
        formatted = f"Conversation: {title}\n\n"

        for msg in messages:
            role_prefix = "User" if msg["role"] == "user" else "Assistant"
            formatted += f"{role_prefix}: {msg['content']}\n\n"

        return formatted.strip()

    async def _store_conversation_turn(
        self,
        thread_id: str,
        turn_number: int,
        message: Dict[str, Any]
    ):
        """
        Store individual conversation turn with embedding

        Args:
            thread_id: Parent thread ID
            turn_number: Turn order number
            message: Message dictionary
        """
        content = message["content"]
        role = message["role"]
        timestamp = message["timestamp"]
        message_id = message["message_id"]

        # Generate turn embedding
        turn_embedding = self.embeddings.generate_embedding(content)

        # Store turn embedding in Weaviate
        turn_vector_id = await self._store_weaviate_embedding(
            embedding=turn_embedding,
            content=content,
            metadata={
                "type": "conversation_turn",
                "role": role,
                "turn_number": turn_number,
                "thread_id": thread_id
            }
        )

        # Store in database
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_turns (
                    turn_id, thread_id, turn_number, role, content,
                    original_message_id, created_at, embedding_vector_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                str(uuid4()),
                thread_id,
                turn_number,
                role,
                content,
                message_id,
                timestamp,
                turn_vector_id
            )

    async def _store_weaviate_embedding(
        self,
        embedding: List[float],
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store embedding in Weaviate vector database

        Args:
            embedding: Embedding vector
            content: Text content
            metadata: Metadata dictionary (contains type, source, title, turn_count, role, etc.)

        Returns:
            Weaviate object ID (vector_id)
        """
        embedding_type = metadata.get("type")  # "conversation_thread" or "conversation_turn"

        if embedding_type == "conversation_thread":
            # Store thread embedding
            vector_id = self.vector_storage.store_thread_vector(
                embedding=embedding,
                thread_id=metadata.get("thread_id", ""),
                user_id=metadata.get("user_id", "00000000-0000-0000-0000-000000000001"),
                source=metadata.get("source", "claude"),
                title=metadata.get("title", "Untitled"),
                turn_count=metadata.get("turn_count", 0),
                content=content,
                created_at=metadata.get("created_at", datetime.utcnow()),
                imported_at=datetime.utcnow()
            )
        elif embedding_type == "conversation_turn":
            # Store turn embedding
            vector_id = self.vector_storage.store_turn_vector(
                embedding=embedding,
                turn_id=metadata.get("turn_id", ""),
                thread_id=metadata.get("thread_id", ""),
                user_id=metadata.get("user_id", "00000000-0000-0000-0000-000000000001"),
                role=metadata.get("role", "user"),
                turn_number=metadata.get("turn_number", 1),
                source=metadata.get("source", "claude"),
                content=content,
                created_at=metadata.get("created_at", datetime.utcnow())
            )
        else:
            # Unknown type, return placeholder
            vector_id = f"weaviate_unknown_{str(uuid4())[:8]}"

        return vector_id
