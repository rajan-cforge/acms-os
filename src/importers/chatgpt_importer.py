"""
ChatGPT Importer - Unified Query History Storage
Imports ChatGPT conversation history as Q&A pairs into query_history table.

Version 2.0 (December 2025):
- Primary method: import_to_query_history() - writes to unified query_history table
- Legacy method: import_conversations() - writes to conversation_threads (deprecated)

Usage:
    importer = ChatGPTImporter()
    await importer.initialize()

    # Preferred: Import to query_history
    stats = await importer.import_to_query_history('/path/to/conversations.json', user_id)

    # Legacy: Import to conversation_threads (deprecated)
    stats = await importer.import_conversations('/path/to/conversations.json', user_id)
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from src.storage.database import get_db_pool
from src.embeddings.openai_embeddings import OpenAIEmbeddings
from src.storage.conversation_vectors import ConversationVectorStorage

logger = logging.getLogger(__name__)


class ChatGPTImporter:
    """Import ChatGPT conversation history into ACMS.

    Primary method: import_to_query_history() - unified Q&A storage
    """

    def __init__(self):
        self.pool = None
        self.embeddings = None
        self.vector_storage = None

    async def initialize(self, skip_vectors: bool = False):
        """Initialize database connection and optionally embedding/vector services.

        Args:
            skip_vectors: If True, skip Weaviate/embeddings initialization.
                         Use this for query_history imports that don't need vectors.
        """
        self.pool = await get_db_pool()

        if not skip_vectors:
            self.embeddings = OpenAIEmbeddings()
            self.vector_storage = ConversationVectorStorage()
            # Setup Weaviate collections for conversations
            self.vector_storage.setup_collections()
        else:
            logger.info("[ChatGPT Import] Skipping vector storage initialization")

    async def import_to_query_history(
        self,
        file_path: str,
        user_id: str = "00000000-0000-0000-0000-000000000001",
        tenant_id: str = "default",
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Import ChatGPT conversations as Q&A pairs into query_history table.

        This is the PREFERRED method for importing ChatGPT data.
        Each user question + assistant answer becomes one row in query_history.

        Args:
            file_path: Path to ChatGPT conversations.json export file
            user_id: User ID to associate Q&A with
            tenant_id: Tenant ID for multi-tenancy
            skip_duplicates: Skip Q&A pairs that already exist (based on question hash)

        Returns:
            Dict with import statistics:
            - qa_pairs_imported: Number of Q&A pairs stored
            - conversations_processed: Number of conversations processed
            - duplicates_skipped: Number of duplicates skipped
            - errors: Number of errors encountered
        """
        stats = {
            "qa_pairs_imported": 0,
            "conversations_processed": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "data_source": "chatgpt_import"
        }

        logger.info(f"[ChatGPT Import] Starting import from {file_path}")

        try:
            # Load JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle both formats: list of conversations or {"conversations": [...]}
            if isinstance(data, list):
                conversations = data
            else:
                conversations = data.get("conversations", [])

            logger.info(f"[ChatGPT Import] Found {len(conversations)} conversations")

            for conv in conversations:
                try:
                    qa_count, dup_count = await self._process_conversation_to_query_history(
                        conv=conv,
                        user_id=user_id,
                        tenant_id=tenant_id,
                        skip_duplicates=skip_duplicates
                    )
                    stats["qa_pairs_imported"] += qa_count
                    stats["duplicates_skipped"] += dup_count
                    stats["conversations_processed"] += 1
                except Exception as e:
                    logger.error(f"[ChatGPT Import] Error processing conversation: {e}")
                    stats["errors"] += 1

            logger.info(
                f"[ChatGPT Import] Complete: {stats['qa_pairs_imported']} Q&A pairs imported, "
                f"{stats['duplicates_skipped']} duplicates skipped, "
                f"{stats['errors']} errors"
            )

            return stats

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")

    async def _process_conversation_to_query_history(
        self,
        conv: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        skip_duplicates: bool
    ) -> tuple:
        """
        Process a single conversation and store Q&A pairs in query_history.

        Args:
            conv: Conversation dictionary from ChatGPT export
            user_id: User ID
            tenant_id: Tenant ID
            skip_duplicates: Skip if question already exists

        Returns:
            Tuple of (qa_pairs_imported, duplicates_skipped)
        """
        # Handle both old format (mapping) and new format (chat_messages)
        title = conv.get("title") or conv.get("name") or "Untitled Conversation"
        conversation_id = conv.get("id") or conv.get("uuid") or str(uuid4())

        # Detect format and extract messages
        if "chat_messages" in conv and conv["chat_messages"]:
            # New format: chat_messages array with sender/text fields
            messages = self._extract_messages_new_format(conv["chat_messages"])
        elif "mapping" in conv:
            # Old format: nested mapping structure
            messages = self._extract_messages(conv.get("mapping", {}))
        else:
            messages = []

        if not messages:
            return 0, 0

        # Pair user questions with assistant answers
        qa_pairs = self._pair_messages_as_qa(messages, title, conversation_id)

        qa_imported = 0
        duplicates_skipped = 0

        async with self.pool.acquire() as conn:
            for qa in qa_pairs:
                # Check for duplicate if requested
                if skip_duplicates:
                    existing = await conn.fetchrow(
                        """
                        SELECT query_id FROM query_history
                        WHERE user_id = $1
                        AND data_source = 'chatgpt_import'
                        AND metadata->>'original_message_id' = $2
                        """,
                        user_id, qa["message_id"]
                    )
                    if existing:
                        duplicates_skipped += 1
                        continue

                # Insert Q&A pair into query_history
                query_id = str(uuid4())
                await conn.execute(
                    """
                    INSERT INTO query_history (
                        query_id, user_id, question, answer,
                        response_source, created_at, data_source,
                        tenant_id, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    query_id,
                    user_id,
                    qa["question"],
                    qa["answer"],
                    "chatgpt",  # response_source = the AI that answered
                    qa["created_at"],
                    "chatgpt_import",  # data_source = how we got this data
                    tenant_id,
                    json.dumps({
                        "conversation_title": title,
                        "conversation_id": conversation_id,
                        "original_message_id": qa["message_id"],
                        "import_source": "chatgpt_export"
                    })
                )
                qa_imported += 1

        return qa_imported, duplicates_skipped

    def _pair_messages_as_qa(
        self,
        messages: List[Dict[str, Any]],
        title: str,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Pair user messages with assistant responses as Q&A pairs.

        Args:
            messages: List of messages sorted by timestamp
            title: Conversation title
            conversation_id: Original conversation ID

        Returns:
            List of Q&A dictionaries with question, answer, timestamps
        """
        qa_pairs = []
        i = 0

        while i < len(messages):
            msg = messages[i]

            if msg["role"] == "user":
                question = msg["content"]
                question_time = msg["timestamp"]
                message_id = msg["message_id"]

                # Look for next assistant response
                answer = ""
                answer_time = question_time

                if i + 1 < len(messages) and messages[i + 1]["role"] == "assistant":
                    answer = messages[i + 1]["content"]
                    answer_time = messages[i + 1]["timestamp"]
                    i += 1  # Skip the answer message

                # Create Q&A pair
                created_at = datetime.fromtimestamp(question_time) if question_time > 0 else datetime.utcnow()

                qa_pairs.append({
                    "question": question,
                    "answer": answer,
                    "created_at": created_at,
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                    "conversation_title": title
                })

            i += 1

        return qa_pairs

    async def import_conversations(
        self,
        file_path: str,
        user_id: str = "00000000-0000-0000-0000-000000000001"
    ) -> Dict[str, Any]:
        """
        Import ChatGPT conversations from JSON export file

        Args:
            file_path: Path to conversations.json file
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

            # Process each conversation
            # Handle both formats: list of conversations or {"conversations": [...]}
            if isinstance(data, list):
                conversations = data
            else:
                conversations = data.get("conversations", [])

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
            conv: Conversation dictionary from ChatGPT export
            user_id: User ID

        Returns:
            Number of turns created
        """
        title = conv.get("title", "Untitled Conversation")
        create_time = conv.get("create_time", 0)
        update_time = conv.get("update_time", create_time)
        conversation_id = conv.get("id", None)
        mapping = conv.get("mapping", {})

        # Extract messages from mapping structure
        messages = self._extract_messages(mapping)

        # Check for duplicate conversation
        if conversation_id:
            async with self.pool.acquire() as conn:
                existing = await conn.fetchrow(
                    """
                    SELECT thread_id FROM conversation_threads
                    WHERE user_id = $1 AND source = 'chatgpt' AND original_thread_id = $2
                    """,
                    user_id, conversation_id
                )
                if existing:
                    print(f"Skipping duplicate conversation: {title}")
                    return 0

        # Generate full conversation text for thread embedding
        full_conversation = self._format_full_conversation(messages, title)

        # Generate thread embedding
        thread_embedding = self.embeddings.generate_embedding(full_conversation)

        # Create conversation_threads record first (need thread_id for Weaviate)
        thread_id = str(uuid4())
        created_at = datetime.fromtimestamp(create_time) if create_time > 0 else datetime.utcnow()

        # Store thread embedding in Weaviate and get vector ID
        thread_vector_id = await self._store_weaviate_embedding(
            embedding=thread_embedding,
            content=full_conversation,
            metadata={
                "type": "conversation_thread",
                "source": "chatgpt",
                "title": title,
                "turn_count": len(messages),
                "thread_id": thread_id,
                "user_id": user_id,
                "created_at": created_at
            }
        )

        metadata = {
            "create_time": create_time,
            "update_time": update_time,
            "source": "chatgpt"
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
                "chatgpt",
                title,
                conversation_id,
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
                message=message,
                user_id=user_id
            )
            turn_count += 1

        return turn_count

    def _extract_messages(self, mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract messages from ChatGPT's nested mapping structure

        Args:
            mapping: Mapping dictionary from ChatGPT export

        Returns:
            List of messages sorted by create_time
        """
        messages = []

        for msg_id, msg_data in mapping.items():
            # Check if message exists and has required fields
            if not msg_data or "message" not in msg_data:
                continue

            message = msg_data["message"]

            # Skip if no message content
            if not message:
                continue

            # Extract fields
            author = message.get("author", {})
            role = author.get("role")
            content = message.get("content", {})
            parts = content.get("parts", [])
            create_time = message.get("create_time", 0)
            message_id = message.get("id", msg_id)

            # Skip if no content or role
            if not parts or not role:
                continue

            # Skip system messages
            if role not in ["user", "assistant"]:
                continue

            # Combine all parts into single text
            text = " ".join([str(part) for part in parts if part])

            if text:
                messages.append({
                    "role": role,
                    "content": text,
                    "timestamp": create_time,
                    "message_id": message_id
                })

        # Sort by timestamp
        messages.sort(key=lambda m: m["timestamp"])

        return messages

    def _extract_messages_new_format(self, chat_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract messages from new ChatGPT export format (chat_messages array).

        New format uses:
        - sender: "human" or "assistant" (instead of role: "user"/"assistant")
        - text: the message content (instead of content.parts)
        - uuid: message ID
        - created_at: ISO timestamp

        Args:
            chat_messages: List of message dictionaries from new ChatGPT export

        Returns:
            List of messages in standardized format for pairing
        """
        messages = []

        for msg in chat_messages:
            sender = msg.get("sender", "")
            text = msg.get("text", "")
            message_id = msg.get("uuid", str(uuid4()))
            created_at = msg.get("created_at", "")

            # Map sender to role
            if sender == "human":
                role = "user"
            elif sender == "assistant":
                role = "assistant"
            else:
                continue  # Skip system or unknown messages

            if not text:
                continue

            # Parse timestamp from ISO format
            timestamp = 0
            if created_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    timestamp = dt.timestamp()
                except (ValueError, TypeError):
                    pass

            messages.append({
                "role": role,
                "content": text,
                "timestamp": timestamp,
                "message_id": message_id
            })

        # Sort by timestamp
        messages.sort(key=lambda m: m["timestamp"])

        return messages

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
        message: Dict[str, Any],
        user_id: str = "00000000-0000-0000-0000-000000000001"
    ):
        """
        Store individual conversation turn with embedding

        Args:
            thread_id: Parent thread ID
            turn_number: Turn order number
            message: Message dictionary
            user_id: User ID
        """
        content = message["content"]
        role = message["role"]
        timestamp = message["timestamp"]
        message_id = message["message_id"]
        turn_id = str(uuid4())
        turn_created_at = datetime.fromtimestamp(timestamp) if timestamp > 0 else datetime.utcnow()

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
                "thread_id": thread_id,
                "turn_id": turn_id,
                "user_id": user_id,
                "source": "chatgpt",
                "created_at": turn_created_at
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
                turn_id,
                thread_id,
                turn_number,
                role,
                content,
                message_id,
                turn_created_at,
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
                source=metadata.get("source", "chatgpt"),
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
                source=metadata.get("source", "chatgpt"),
                content=content,
                created_at=metadata.get("created_at", datetime.utcnow())
            )
        else:
            # Unknown type, return placeholder
            vector_id = f"weaviate_unknown_{str(uuid4())[:8]}"

        return vector_id
