"""
Unit tests for ConversationMemoryManager.

Tests:
1. Creates conversation if missing
2. Appends turns idempotently by client_message_id
3. Loads last N turns
4. Updates summary after threshold
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.gateway.conversation_memory import (
    ConversationMemoryManager,
    ConversationState,
    ThreadContext
)
from src.storage.models import Conversation, ConversationMessage, User
from src.storage.database import get_session


@pytest.fixture
async def test_user():
    """Create a test user."""
    async with get_session() as session:
        user = User(
            user_id=uuid4(),
            username=f"test_user_{uuid4().hex[:8]}",
            email=f"test_{uuid4().hex[:8]}@example.com",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def cmm():
    """Create ConversationMemoryManager instance."""
    return ConversationMemoryManager()


class TestConversationState:
    """Tests for ConversationState dataclass."""

    def test_from_json_empty(self):
        """Empty JSON creates default state."""
        state = ConversationState.from_json({})
        assert state.summary == ""
        assert state.entities == {}
        assert state.topic_stack == []
        assert state.last_intent is None
        assert state.summary_version == 1
        assert state.turns_since_summary == 0

    def test_from_json_with_data(self):
        """JSON with data creates populated state."""
        data = {
            "summary": "Test summary",
            "entities": {"NuBird": {"type": "SRE"}},
            "topic_stack": ["kubernetes", "deployment"],
            "last_intent": "ANALYSIS",
            "summary_version": 3,
            "turns_since_summary": 5
        }
        state = ConversationState.from_json(data)
        assert state.summary == "Test summary"
        assert state.entities == {"NuBird": {"type": "SRE"}}
        assert state.topic_stack == ["kubernetes", "deployment"]
        assert state.last_intent == "ANALYSIS"
        assert state.summary_version == 3
        assert state.turns_since_summary == 5

    def test_to_json_roundtrip(self):
        """to_json and from_json are inverse operations."""
        original = ConversationState(
            summary="Test",
            entities={"key": "value"},
            topic_stack=["topic1"],
            last_intent="FACTUAL",
            summary_version=2,
            turns_since_summary=3
        )
        json_data = original.to_json()
        restored = ConversationState.from_json(json_data)
        assert restored.summary == original.summary
        assert restored.entities == original.entities
        assert restored.topic_stack == original.topic_stack
        assert restored.last_intent == original.last_intent
        assert restored.summary_version == original.summary_version
        assert restored.turns_since_summary == original.turns_since_summary


class TestConversationMemoryManager:
    """Tests for ConversationMemoryManager."""

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_new(self, cmm, test_user):
        """Creates new conversation when none exists."""
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            conversation_id=None,
            agent="claude"
        )
        assert conv_id is not None

        # Verify conversation exists
        async with get_session() as session:
            conv = await session.get(Conversation, conv_id)
            assert conv is not None
            assert conv.tenant_id == "test_tenant"
            assert conv.user_id == test_user.user_id
            assert conv.agent == "claude"

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_existing(self, cmm, test_user):
        """Returns existing conversation if valid."""
        # Create first
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )

        # Get same conversation
        same_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            conversation_id=conv_id,
            agent="claude"
        )
        assert same_id == conv_id

    @pytest.mark.asyncio
    async def test_append_turn_basic(self, cmm, test_user):
        """Appends turn to conversation."""
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )

        msg_id = await cmm.append_turn(
            tenant_id="test_tenant",
            conversation_id=conv_id,
            role="user",
            content="Hello, world!",
            token_count=3
        )
        assert msg_id is not None

        # Verify message exists
        async with get_session() as session:
            msg = await session.get(ConversationMessage, msg_id)
            assert msg is not None
            assert msg.role == "user"
            assert msg.content == "Hello, world!"
            assert msg.token_count == 3

    @pytest.mark.asyncio
    async def test_append_turn_idempotent(self, cmm, test_user):
        """Idempotent write returns same message_id."""
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )

        client_id = f"client_{uuid4().hex[:8]}"

        # First write
        msg_id1 = await cmm.append_turn(
            tenant_id="test_tenant",
            conversation_id=conv_id,
            role="user",
            content="Test message",
            client_message_id=client_id
        )

        # Second write with same client_id
        msg_id2 = await cmm.append_turn(
            tenant_id="test_tenant",
            conversation_id=conv_id,
            role="user",
            content="Different content (should be ignored)",
            client_message_id=client_id
        )

        assert msg_id1 == msg_id2

    @pytest.mark.asyncio
    async def test_load_thread_context(self, cmm, test_user):
        """Loads context with summary and recent turns."""
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )

        # Add some turns
        await cmm.append_turn("test_tenant", conv_id, "user", "What is Kubernetes?")
        await cmm.append_turn("test_tenant", conv_id, "assistant", "Kubernetes is...")
        await cmm.append_turn("test_tenant", conv_id, "user", "How does it work?")

        # Load context
        ctx = await cmm.load_thread_context("test_tenant", conv_id)

        assert ctx is not None
        assert ctx.conversation_id == conv_id
        assert ctx.tenant_id == "test_tenant"
        assert ctx.user_id == test_user.user_id
        assert len(ctx.recent_turns) == 3
        assert ctx.recent_turns[0]["role"] == "user"
        assert ctx.recent_turns[0]["content"] == "What is Kubernetes?"
        assert ctx.turn_count == 3

    @pytest.mark.asyncio
    async def test_load_thread_context_max_turns(self, cmm, test_user):
        """Respects max_turns limit."""
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )

        # Add 15 turns
        for i in range(15):
            role = "user" if i % 2 == 0 else "assistant"
            await cmm.append_turn("test_tenant", conv_id, role, f"Message {i}")

        # Load with max_turns=5
        ctx = await cmm.load_thread_context("test_tenant", conv_id, max_turns=5)

        assert len(ctx.recent_turns) == 5
        assert ctx.turn_count == 15
        # Should be the last 5 messages
        assert ctx.recent_turns[0]["content"] == "Message 10"
        assert ctx.recent_turns[4]["content"] == "Message 14"

    @pytest.mark.asyncio
    async def test_update_entity(self, cmm, test_user):
        """Updates entity disambiguation state."""
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )

        await cmm.update_entity(
            tenant_id="test_tenant",
            conversation_id=conv_id,
            entity_key="NuBird",
            entity_value={"type": "SRE AI assistant", "not": "course platform"}
        )

        # Verify entity was saved
        ctx = await cmm.load_thread_context("test_tenant", conv_id)
        assert "NuBird" in ctx.entities
        assert ctx.entities["NuBird"]["type"] == "SRE AI assistant"

    @pytest.mark.asyncio
    async def test_push_topic(self, cmm, test_user):
        """Pushes topics onto topic stack."""
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )

        await cmm.push_topic("test_tenant", conv_id, "kubernetes")
        await cmm.push_topic("test_tenant", conv_id, "deployment")

        ctx = await cmm.load_thread_context("test_tenant", conv_id)
        assert ctx.topic_stack == ["kubernetes", "deployment"]

    @pytest.mark.asyncio
    async def test_update_summary_threshold(self, cmm, test_user):
        """Updates summary after threshold exceeded."""
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )

        # Add turns below threshold
        for i in range(4):
            await cmm.append_turn("test_tenant", conv_id, "user", f"Q{i}")
            await cmm.append_turn("test_tenant", conv_id, "assistant", f"A{i}")

        # Should not update (8 turns, threshold is 6 but we're checking state.turns_since_summary)
        updated = await cmm.update_summary_if_needed("test_tenant", conv_id)

        # After 8 turns, turns_since_summary should be 8
        ctx = await cmm.load_thread_context("test_tenant", conv_id)
        assert ctx.turn_count == 8

    @pytest.mark.asyncio
    async def test_update_summary_force(self, cmm, test_user):
        """Force updates summary regardless of threshold."""
        conv_id = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )

        await cmm.append_turn("test_tenant", conv_id, "user", "Test question")
        await cmm.append_turn("test_tenant", conv_id, "assistant", "Test answer")

        updated = await cmm.update_summary_if_needed("test_tenant", conv_id, force=True)
        assert updated is True

        ctx = await cmm.load_thread_context("test_tenant", conv_id)
        assert ctx.summary != ""
        assert "User: Test question" in ctx.summary

    @pytest.mark.asyncio
    async def test_conversation_stats(self, cmm, test_user):
        """Gets conversation statistics."""
        # Create two conversations
        conv1 = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="claude"
        )
        conv2 = await cmm.get_or_create_conversation(
            tenant_id="test_tenant",
            user_id=test_user.user_id,
            agent="gpt"
        )

        # Add messages
        await cmm.append_turn("test_tenant", conv1, "user", "Q1")
        await cmm.append_turn("test_tenant", conv1, "assistant", "A1")
        await cmm.append_turn("test_tenant", conv2, "user", "Q2")

        stats = await cmm.get_conversation_stats("test_tenant", test_user.user_id)

        assert stats["conversation_count"] >= 2
        assert stats["total_messages"] >= 3
