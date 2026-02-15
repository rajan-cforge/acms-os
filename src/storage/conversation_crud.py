"""
Conversation CRUD Operations - Phase 1, Task 1.2

Database operations for unified chat interface conversations.
Handles creation, retrieval, and message management for live conversations.

Separate from conversation_threads (imported conversations from ChatGPT/Claude).
These are LIVE conversations happening in the ACMS unified interface.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
import logging

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session, selectinload

from src.storage.models import Conversation, ConversationMessage, User
from src.storage.database import get_session

logger = logging.getLogger("acms.conversation_crud")


class ConversationCRUD:
    """CRUD operations for conversations and messages"""

    def __init__(self):
        """Initialize ConversationCRUD"""
        pass

    async def create_conversation(
        self,
        user_id: UUID,
        agent: str,
        title: Optional[str] = None
    ) -> Conversation:
        """Create new conversation.

        Args:
            user_id: User ID
            agent: AI agent (claude, gpt, gemini, claude-code)
            title: Optional title (auto-generated from first message if None)

        Returns:
            Created Conversation object

        Raises:
            ValueError: If user doesn't exist
            ValueError: If agent is invalid
        """
        # Validate agent
        valid_agents = ["claude", "gpt", "gemini", "claude-code"]
        if agent not in valid_agents:
            raise ValueError(f"Invalid agent: {agent}. Must be one of: {valid_agents}")

        async with get_session() as session:
            # Verify user exists
            user = await session.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Create conversation
            conversation = Conversation(
                conversation_id=uuid4(),
                user_id=user_id,
                agent=agent,
                title=title,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

            logger.info(
                f"[ConversationCRUD] Created conversation {conversation.conversation_id} "
                f"for user {user_id} with agent {agent}"
            )

            return conversation

    async def list_conversations(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Conversation], int]:
        """List user's conversations with pagination.

        Args:
            user_id: User ID
            limit: Max conversations to return
            offset: Number of conversations to skip

        Returns:
            Tuple of (conversations list, total count)
        """
        async with get_session() as session:
            # Get total count
            count_query = select(func.count()).select_from(Conversation).where(
                Conversation.user_id == user_id
            )
            total_count = (await session.execute(count_query)).scalar()

            # Get conversations ordered by most recent first
            query = (
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(desc(Conversation.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(query)
            conversations = result.scalars().all()

            logger.info(
                f"[ConversationCRUD] Listed {len(conversations)} conversations "
                f"for user {user_id} (total: {total_count})"
            )

            return (list(conversations), total_count)

    async def group_conversations_by_date(
        self,
        conversations: List[Conversation]
    ) -> Dict[str, List[Conversation]]:
        """Group conversations by time period.

        Groups:
        - Today
        - Yesterday
        - Previous 7 days
        - Previous 30 days
        - Older

        Args:
            conversations: List of conversations

        Returns:
            Dict mapping group name to conversations
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        groups = {
            "Today": [],
            "Yesterday": [],
            "Previous 7 days": [],
            "Previous 30 days": [],
            "Older": []
        }

        for conv in conversations:
            # Ensure created_at is timezone-aware
            created_at = conv.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            if created_at >= today_start:
                groups["Today"].append(conv)
            elif created_at >= yesterday_start:
                groups["Yesterday"].append(conv)
            elif created_at >= week_ago:
                groups["Previous 7 days"].append(conv)
            elif created_at >= month_ago:
                groups["Previous 30 days"].append(conv)
            else:
                groups["Older"].append(conv)

        # Remove empty groups
        return {k: v for k, v in groups.items() if v}

    async def get_conversation(
        self,
        conversation_id: UUID,
        include_messages: bool = True
    ) -> Optional[Conversation]:
        """Get conversation by ID with optional messages.

        Args:
            conversation_id: Conversation ID
            include_messages: If True, load messages with conversation

        Returns:
            Conversation object or None if not found
        """
        async with get_session() as session:
            if include_messages:
                # Eager load messages
                query = (
                    select(Conversation)
                    .options(selectinload(Conversation.messages))
                    .where(Conversation.conversation_id == conversation_id)
                )
            else:
                query = select(Conversation).where(
                    Conversation.conversation_id == conversation_id
                )

            result = await session.execute(query)
            conversation = result.scalar_one_or_none()

            if conversation:
                logger.info(
                    f"[ConversationCRUD] Retrieved conversation {conversation_id} "
                    f"with {len(conversation.messages) if include_messages else 0} messages"
                )
            else:
                logger.warning(f"[ConversationCRUD] Conversation {conversation_id} not found")

            return conversation

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """Add message to conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role (user or assistant)
            content: Message content
            metadata: Optional metadata (cost, tokens, model, etc.)

        Returns:
            Created ConversationMessage object

        Raises:
            ValueError: If conversation doesn't exist
            ValueError: If role is invalid
            ValueError: If content is empty
        """
        # Validate role
        if role not in ["user", "assistant"]:
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

        # Validate content
        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")

        async with get_session() as session:
            # Verify conversation exists
            conversation = await session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")

            # Create message
            message = ConversationMessage(
                message_id=uuid4(),
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_metadata=metadata or {},
                created_at=datetime.now(timezone.utc)
            )

            session.add(message)

            # Update conversation updated_at
            conversation.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(message)

            logger.info(
                f"[ConversationCRUD] Added {role} message to conversation {conversation_id}"
            )

            return message

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """Get messages for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Optional limit on number of messages (most recent first)

        Returns:
            List of messages ordered by created_at
        """
        async with get_session() as session:
            query = (
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.created_at)
            )

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            messages = result.scalars().all()

            logger.info(
                f"[ConversationCRUD] Retrieved {len(messages)} messages "
                f"for conversation {conversation_id}"
            )

            return list(messages)

    async def update_conversation_title(
        self,
        conversation_id: UUID,
        title: str
    ) -> Optional[Conversation]:
        """Update conversation title.

        Args:
            conversation_id: Conversation ID
            title: New title

        Returns:
            Updated Conversation object or None if not found
        """
        async with get_session() as session:
            conversation = await session.get(Conversation, conversation_id)
            if not conversation:
                logger.warning(f"[ConversationCRUD] Conversation {conversation_id} not found")
                return None

            conversation.title = title
            conversation.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(conversation)

            logger.info(f"[ConversationCRUD] Updated title for conversation {conversation_id}")

            return conversation

    async def delete_conversation(
        self,
        conversation_id: UUID
    ) -> bool:
        """Delete conversation and all its messages (cascade).

        Args:
            conversation_id: Conversation ID

        Returns:
            True if deleted, False if not found
        """
        async with get_session() as session:
            conversation = await session.get(Conversation, conversation_id)
            if not conversation:
                logger.warning(f"[ConversationCRUD] Conversation {conversation_id} not found")
                return False

            await session.delete(conversation)
            await session.commit()

            logger.info(f"[ConversationCRUD] Deleted conversation {conversation_id}")

            return True


# Singleton instance
_conversation_crud = None


def get_conversation_crud() -> ConversationCRUD:
    """Get singleton ConversationCRUD instance."""
    global _conversation_crud
    if _conversation_crud is None:
        _conversation_crud = ConversationCRUD()
    return _conversation_crud
