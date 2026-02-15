"""
Conversation Memory Manager - Conversation Continuity Foundation

This service manages conversation state for ChatGPT-like continuity:
- Rolling summary (mid-term memory)
- Last N turns (short-term memory)
- Entity disambiguation state
- Topic tracking

Per spec: ACMS_Conversation_Continuity_Spec.md
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import Conversation, ConversationMessage, User
from src.storage.database import get_session

logger = logging.getLogger("acms.conversation_memory")


@dataclass
class ThreadContext:
    """Context bundle for prompt composition."""
    conversation_id: UUID
    tenant_id: str
    user_id: UUID
    summary: str  # Rolling conversation summary
    entities: Dict[str, Any]  # Entity disambiguation state
    topic_stack: List[str]  # Current topics being discussed
    recent_turns: List[Dict[str, Any]]  # Last N turns
    turn_count: int  # Total turns in conversation


@dataclass
class ConversationState:
    """State stored in conversations.state_json."""
    summary: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    topic_stack: List[str] = field(default_factory=list)
    last_intent: Optional[str] = None
    summary_version: int = 1
    turns_since_summary: int = 0

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ConversationState":
        """Create from JSON dict."""
        return cls(
            summary=data.get("summary", ""),
            entities=data.get("entities", {}),
            topic_stack=data.get("topic_stack", []),
            last_intent=data.get("last_intent"),
            summary_version=data.get("summary_version", 1),
            turns_since_summary=data.get("turns_since_summary", 0)
        )

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON dict."""
        return {
            "summary": self.summary,
            "entities": self.entities,
            "topic_stack": self.topic_stack,
            "last_intent": self.last_intent,
            "summary_version": self.summary_version,
            "turns_since_summary": self.turns_since_summary
        }


class ConversationMemoryManager:
    """
    Manages conversation state for continuity.

    Responsibilities:
    1. Load conversation state (summary, entities, last N turns)
    2. Persist new turns (idempotent on client_message_id)
    3. Maintain rolling summary every N turns
    4. Track entity disambiguations
    """

    # Configuration
    MAX_RECENT_TURNS = 10  # Number of recent turns to include in context
    SUMMARY_THRESHOLD = 6  # Update summary after this many turns

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize ConversationMemoryManager.

        Args:
            session: Optional SQLAlchemy async session. If None, will create per-operation.
        """
        self._session = session

    async def get_or_create_conversation(
        self,
        tenant_id: str,
        user_id: UUID,
        conversation_id: Optional[UUID] = None,
        agent: str = "claude"
    ) -> UUID:
        """
        Get existing conversation or create a new one.

        Args:
            tenant_id: Tenant/organization ID
            user_id: User ID
            conversation_id: Optional existing conversation ID
            agent: AI agent (claude, gpt, gemini, claude-code)

        Returns:
            Conversation ID (existing or newly created)

        Raises:
            ValueError: If user doesn't exist
        """
        async with get_session() as session:
            # If conversation_id provided, verify it exists and belongs to user
            if conversation_id:
                conv = await session.get(Conversation, conversation_id)
                if conv and conv.user_id == user_id and conv.tenant_id == tenant_id:
                    logger.debug(f"Using existing conversation {conversation_id}")
                    return conversation_id
                elif conv:
                    logger.warning(
                        f"Conversation {conversation_id} access denied for user {user_id}"
                    )
                    # Fall through to create new conversation

            # Create new conversation
            new_conv = Conversation(
                conversation_id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                agent=agent,
                state_json={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(new_conv)
            await session.commit()

            logger.info(
                f"Created new conversation {new_conv.conversation_id} "
                f"for user {user_id} tenant {tenant_id}"
            )
            return new_conv.conversation_id

    async def load_thread_context(
        self,
        tenant_id: str,
        conversation_id: UUID,
        max_turns: int = None
    ) -> Optional[ThreadContext]:
        """
        Load conversation context for prompt composition.

        Args:
            tenant_id: Tenant/organization ID
            conversation_id: Conversation ID
            max_turns: Max recent turns to load (default: MAX_RECENT_TURNS)

        Returns:
            ThreadContext with summary, entities, and recent turns, or None if not found
        """
        max_turns = max_turns or self.MAX_RECENT_TURNS

        async with get_session() as session:
            # Load conversation with messages
            query = (
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(
                    and_(
                        Conversation.conversation_id == conversation_id,
                        Conversation.tenant_id == tenant_id
                    )
                )
            )
            result = await session.execute(query)
            conv = result.scalar_one_or_none()

            if not conv:
                logger.warning(f"Conversation {conversation_id} not found")
                return None

            # Parse state
            state = ConversationState.from_json(conv.state_json or {})

            # Get recent turns (already ordered by created_at in relationship)
            all_messages = conv.messages or []
            recent_messages = all_messages[-max_turns:] if len(all_messages) > max_turns else all_messages

            recent_turns = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "message_id": str(msg.message_id)
                }
                for msg in recent_messages
            ]

            logger.debug(
                f"Loaded context for conversation {conversation_id}: "
                f"{len(recent_turns)} turns, summary_len={len(state.summary)}"
            )

            return ThreadContext(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                user_id=conv.user_id,
                summary=state.summary,
                entities=state.entities,
                topic_stack=state.topic_stack,
                recent_turns=recent_turns,
                turn_count=len(all_messages)
            )

    async def append_turn(
        self,
        tenant_id: str,
        conversation_id: UUID,
        role: str,
        content: str,
        client_message_id: Optional[str] = None,
        token_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Append a turn to the conversation (idempotent).

        Args:
            tenant_id: Tenant/organization ID
            conversation_id: Conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            client_message_id: Optional client-generated ID for idempotency
            token_count: Optional token count
            metadata: Optional message metadata

        Returns:
            Message ID (new or existing if idempotent)

        Raises:
            ValueError: If conversation doesn't exist
        """
        async with get_session() as session:
            # Check for idempotent write
            if client_message_id:
                existing = await session.execute(
                    select(ConversationMessage).where(
                        and_(
                            ConversationMessage.tenant_id == tenant_id,
                            ConversationMessage.conversation_id == conversation_id,
                            ConversationMessage.client_message_id == client_message_id
                        )
                    )
                )
                existing_msg = existing.scalar_one_or_none()
                if existing_msg:
                    logger.debug(
                        f"Idempotent: returning existing message {existing_msg.message_id}"
                    )
                    return existing_msg.message_id

            # Verify conversation exists
            conv = await session.get(Conversation, conversation_id)
            if not conv or conv.tenant_id != tenant_id:
                raise ValueError(f"Conversation {conversation_id} not found")

            # Create message
            message = ConversationMessage(
                message_id=uuid4(),
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                client_message_id=client_message_id,
                role=role,
                content=content,
                token_count=token_count,
                message_metadata=metadata or {},
                created_at=datetime.now(timezone.utc)
            )
            session.add(message)

            # Update conversation timestamp and increment turns_since_summary
            conv.updated_at = datetime.now(timezone.utc)
            state = ConversationState.from_json(conv.state_json or {})
            state.turns_since_summary += 1
            conv.state_json = state.to_json()

            await session.commit()

            logger.info(
                f"Appended {role} turn to conversation {conversation_id}, "
                f"message_id={message.message_id}"
            )
            return message.message_id

    async def update_summary_if_needed(
        self,
        tenant_id: str,
        conversation_id: UUID,
        force: bool = False
    ) -> bool:
        """
        Update rolling summary if threshold exceeded.

        Args:
            tenant_id: Tenant/organization ID
            conversation_id: Conversation ID
            force: Force update regardless of threshold

        Returns:
            True if summary was updated, False otherwise
        """
        async with get_session() as session:
            # Load conversation with messages
            query = (
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(
                    and_(
                        Conversation.conversation_id == conversation_id,
                        Conversation.tenant_id == tenant_id
                    )
                )
            )
            result = await session.execute(query)
            conv = result.scalar_one_or_none()

            if not conv:
                logger.warning(f"Conversation {conversation_id} not found")
                return False

            state = ConversationState.from_json(conv.state_json or {})

            # Check if update needed
            if not force and state.turns_since_summary < self.SUMMARY_THRESHOLD:
                logger.debug(
                    f"Summary update not needed: {state.turns_since_summary} < {self.SUMMARY_THRESHOLD}"
                )
                return False

            # Generate summary from recent turns
            # For now, simple concatenation. In production, use LLM to compress.
            all_messages = conv.messages or []
            if not all_messages:
                return False

            # Simple summary: last 20 turns compressed
            turns_to_summarize = all_messages[-20:]
            summary_parts = []

            for msg in turns_to_summarize:
                prefix = "User" if msg.role == "user" else "Assistant"
                # Truncate long messages
                content_preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                summary_parts.append(f"{prefix}: {content_preview}")

            new_summary = "\n".join(summary_parts)

            # Update state
            state.summary = new_summary
            state.turns_since_summary = 0
            state.summary_version += 1
            conv.state_json = state.to_json()

            await session.commit()

            logger.info(
                f"Updated summary for conversation {conversation_id}, "
                f"version={state.summary_version}, len={len(new_summary)}"
            )
            return True

    async def update_entity(
        self,
        tenant_id: str,
        conversation_id: UUID,
        entity_key: str,
        entity_value: Any
    ) -> None:
        """
        Update entity disambiguation state.

        Example: When user says "not that NuBird, the SRE one",
        update entities["NuBird"] = {"type": "SRE AI assistant", "not": "course platform"}

        Args:
            tenant_id: Tenant/organization ID
            conversation_id: Conversation ID
            entity_key: Entity name (e.g., "NuBird")
            entity_value: Entity disambiguation info
        """
        async with get_session() as session:
            conv = await session.get(Conversation, conversation_id)
            if not conv or conv.tenant_id != tenant_id:
                logger.warning(f"Conversation {conversation_id} not found")
                return

            state = ConversationState.from_json(conv.state_json or {})
            state.entities[entity_key] = entity_value
            conv.state_json = state.to_json()
            conv.updated_at = datetime.now(timezone.utc)

            await session.commit()

            logger.info(
                f"Updated entity '{entity_key}' in conversation {conversation_id}"
            )

    async def push_topic(
        self,
        tenant_id: str,
        conversation_id: UUID,
        topic: str
    ) -> None:
        """
        Push a topic onto the topic stack.

        Args:
            tenant_id: Tenant/organization ID
            conversation_id: Conversation ID
            topic: Topic to push
        """
        async with get_session() as session:
            conv = await session.get(Conversation, conversation_id)
            if not conv or conv.tenant_id != tenant_id:
                return

            state = ConversationState.from_json(conv.state_json or {})

            # Avoid duplicates at top of stack
            if not state.topic_stack or state.topic_stack[-1] != topic:
                state.topic_stack.append(topic)
                # Keep stack manageable
                if len(state.topic_stack) > 10:
                    state.topic_stack = state.topic_stack[-10:]

            conv.state_json = state.to_json()
            conv.updated_at = datetime.now(timezone.utc)

            await session.commit()

    async def get_conversation_stats(
        self,
        tenant_id: str,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get conversation statistics for a user.

        Args:
            tenant_id: Tenant/organization ID
            user_id: User ID

        Returns:
            Stats dict with conversation_count, total_turns, etc.
        """
        async with get_session() as session:
            # Count conversations
            conv_count = await session.execute(
                select(func.count()).select_from(Conversation).where(
                    and_(
                        Conversation.tenant_id == tenant_id,
                        Conversation.user_id == user_id
                    )
                )
            )
            total_conversations = conv_count.scalar() or 0

            # Count messages
            msg_count = await session.execute(
                select(func.count()).select_from(ConversationMessage).where(
                    and_(
                        ConversationMessage.tenant_id == tenant_id,
                        ConversationMessage.conversation_id.in_(
                            select(Conversation.conversation_id).where(
                                and_(
                                    Conversation.tenant_id == tenant_id,
                                    Conversation.user_id == user_id
                                )
                            )
                        )
                    )
                )
            )
            total_messages = msg_count.scalar() or 0

            return {
                "tenant_id": tenant_id,
                "user_id": str(user_id),
                "conversation_count": total_conversations,
                "total_messages": total_messages
            }


# Module-level singleton
_conversation_memory_manager: Optional[ConversationMemoryManager] = None


def get_conversation_memory_manager() -> ConversationMemoryManager:
    """Get singleton ConversationMemoryManager instance."""
    global _conversation_memory_manager
    if _conversation_memory_manager is None:
        _conversation_memory_manager = ConversationMemoryManager()
    return _conversation_memory_manager
