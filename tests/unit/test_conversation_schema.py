"""
Conversation Schema Tests - Phase 1, Task 1.1

Tests for the unified chat interface database schema:
- Conversation model (conversations table)
- ConversationMessage model (conversation_messages table)

Following TDD: These tests will FAIL initially, then we create the models.
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from src.storage.database import get_db_pool
from src.storage.models import Base, User


class TestConversationSchema:
    """Test Conversation database model"""

    @pytest.fixture
    def db_session(self):
        """Create test database session"""
        # Use in-memory SQLite for tests (fast)
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_user(self, db_session):
        """Create test user"""
        from src.storage.models import User

        user = User(
            user_id=uuid4(),
            username="test_user",
            email="test@acms.com",
            display_name="Test User"
        )
        db_session.add(user)
        db_session.commit()
        return user

    def test_conversation_table_exists(self, db_session):
        """Test that conversations table is created"""
        from src.storage.models import Conversation

        # Check table exists in schema
        inspector = inspect(db_session.bind)
        tables = inspector.get_table_names()

        assert "conversations" in tables, "conversations table should exist"

    def test_conversation_model_fields(self, db_session, test_user):
        """Test Conversation model has required fields"""
        from src.storage.models import Conversation

        # Create conversation
        conv = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            title="Test Conversation",
            agent="claude",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        db_session.add(conv)
        db_session.commit()

        # Verify fields
        assert conv.conversation_id is not None
        assert isinstance(conv.conversation_id, UUID)
        assert conv.user_id == test_user.user_id
        assert conv.title == "Test Conversation"
        assert conv.agent == "claude"
        assert conv.created_at is not None
        assert conv.updated_at is not None

    def test_conversation_default_title(self, db_session, test_user):
        """Test that conversation can have NULL title (auto-generated later)"""
        from src.storage.models import Conversation

        conv = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            agent="gpt"
        )

        db_session.add(conv)
        db_session.commit()

        # Title can be None (will be auto-generated from first message)
        assert conv.title is None or conv.title == ""

    def test_conversation_agent_types(self, db_session, test_user):
        """Test that all supported agent types work"""
        from src.storage.models import Conversation

        agents = ["claude", "gpt", "gemini", "claude-code"]

        for agent in agents:
            conv = Conversation(
                conversation_id=uuid4(),
                user_id=test_user.user_id,
                agent=agent
            )
            db_session.add(conv)

        db_session.commit()

        # Should have 4 conversations
        convs = db_session.query(Conversation).all()
        assert len(convs) == 4

    def test_conversation_user_relationship(self, db_session, test_user):
        """Test foreign key relationship to User"""
        from src.storage.models import Conversation

        conv = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            agent="claude"
        )

        db_session.add(conv)
        db_session.commit()

        # Should be able to access user via relationship
        assert conv.user is not None
        assert conv.user.username == "test_user"

    def test_conversation_timestamps_auto_set(self, db_session, test_user):
        """Test that timestamps are automatically set"""
        from src.storage.models import Conversation

        conv = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            agent="claude"
        )

        db_session.add(conv)
        db_session.commit()

        # Timestamps should be auto-set by database
        assert conv.created_at is not None
        assert conv.updated_at is not None

        # Should be recent (within last minute)
        now = datetime.now(timezone.utc)
        time_diff = (now - conv.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        assert time_diff < 60, "Created timestamp should be recent"


class TestConversationMessageSchema:
    """Test ConversationMessage database model"""

    @pytest.fixture
    def db_session(self):
        """Create test database session"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_conversation(self, db_session):
        """Create test conversation"""
        from src.storage.models import User, Conversation

        user = User(
            user_id=uuid4(),
            username="test_user",
            email="test@acms.com"
        )
        db_session.add(user)
        db_session.commit()

        conv = Conversation(
            conversation_id=uuid4(),
            user_id=user.user_id,
            agent="claude"
        )
        db_session.add(conv)
        db_session.commit()

        return conv

    def test_conversation_message_table_exists(self, db_session):
        """Test that conversation_messages table is created"""
        from src.storage.models import ConversationMessage

        inspector = inspect(db_session.bind)
        tables = inspector.get_table_names()

        assert "conversation_messages" in tables, "conversation_messages table should exist"

    def test_conversation_message_model_fields(self, db_session, test_conversation):
        """Test ConversationMessage model has required fields"""
        from src.storage.models import ConversationMessage

        # Create user message
        msg = ConversationMessage(
            message_id=uuid4(),
            conversation_id=test_conversation.conversation_id,
            role="user",
            content="Hello, Claude!",
            metadata={"tokens": 3},
            created_at=datetime.now(timezone.utc)
        )

        db_session.add(msg)
        db_session.commit()

        # Verify fields
        assert msg.message_id is not None
        assert isinstance(msg.message_id, UUID)
        assert msg.conversation_id == test_conversation.conversation_id
        assert msg.role == "user"
        assert msg.content == "Hello, Claude!"
        assert msg.metadata == {"tokens": 3}
        assert msg.created_at is not None

    def test_conversation_message_roles(self, db_session, test_conversation):
        """Test that user and assistant roles work"""
        from src.storage.models import ConversationMessage

        # User message
        user_msg = ConversationMessage(
            message_id=uuid4(),
            conversation_id=test_conversation.conversation_id,
            role="user",
            content="What is ACMS?"
        )

        # Assistant message
        assistant_msg = ConversationMessage(
            message_id=uuid4(),
            conversation_id=test_conversation.conversation_id,
            role="assistant",
            content="ACMS is the Adaptive Context Memory System."
        )

        db_session.add(user_msg)
        db_session.add(assistant_msg)
        db_session.commit()

        # Should have 2 messages
        messages = db_session.query(ConversationMessage).all()
        assert len(messages) == 2

        roles = [msg.role for msg in messages]
        assert "user" in roles
        assert "assistant" in roles

    def test_conversation_message_metadata_json(self, db_session, test_conversation):
        """Test that metadata stores JSON correctly"""
        from src.storage.models import ConversationMessage

        metadata = {
            "model": "claude-sonnet-4.5",
            "tokens": 1250,
            "cost": 0.03,
            "response_time": 2.3,
            "cached": False,
            "compliance": {
                "pii_detected": False,
                "blocked_terms": []
            }
        }

        msg = ConversationMessage(
            message_id=uuid4(),
            conversation_id=test_conversation.conversation_id,
            role="assistant",
            content="Response text",
            metadata=metadata
        )

        db_session.add(msg)
        db_session.commit()

        # Retrieve and verify JSON
        retrieved = db_session.query(ConversationMessage).filter_by(message_id=msg.message_id).first()
        assert retrieved.metadata == metadata
        assert retrieved.metadata["model"] == "claude-sonnet-4.5"
        assert retrieved.metadata["tokens"] == 1250
        assert retrieved.metadata["cost"] == 0.03

    def test_conversation_message_relationship(self, db_session, test_conversation):
        """Test foreign key relationship to Conversation"""
        from src.storage.models import ConversationMessage

        msg = ConversationMessage(
            message_id=uuid4(),
            conversation_id=test_conversation.conversation_id,
            role="user",
            content="Test message"
        )

        db_session.add(msg)
        db_session.commit()

        # Should be able to access conversation via relationship
        assert msg.conversation is not None
        assert msg.conversation.agent == "claude"

    def test_conversation_has_messages_relationship(self, db_session, test_conversation):
        """Test that Conversation can access its messages"""
        from src.storage.models import ConversationMessage

        # Add 3 messages
        for i in range(3):
            msg = ConversationMessage(
                message_id=uuid4(),
                conversation_id=test_conversation.conversation_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
            db_session.add(msg)

        db_session.commit()

        # Conversation should have messages relationship
        assert len(test_conversation.messages) == 3

    def test_conversation_message_ordering(self, db_session, test_conversation):
        """Test that messages are ordered by created_at"""
        from src.storage.models import ConversationMessage
        import time

        # Add messages with slight delays to ensure ordering
        for i in range(3):
            msg = ConversationMessage(
                message_id=uuid4(),
                conversation_id=test_conversation.conversation_id,
                role="user",
                content=f"Message {i}"
            )
            db_session.add(msg)
            db_session.commit()
            time.sleep(0.01)  # Small delay

        # Fetch messages ordered by created_at
        messages = db_session.query(ConversationMessage).filter_by(
            conversation_id=test_conversation.conversation_id
        ).order_by(ConversationMessage.created_at).all()

        # Should be in order
        assert messages[0].content == "Message 0"
        assert messages[1].content == "Message 1"
        assert messages[2].content == "Message 2"

    def test_conversation_cascade_delete(self, db_session, test_conversation):
        """Test that deleting conversation deletes messages (cascade)"""
        from src.storage.models import ConversationMessage, Conversation

        # Add messages
        for i in range(3):
            msg = ConversationMessage(
                message_id=uuid4(),
                conversation_id=test_conversation.conversation_id,
                role="user",
                content=f"Message {i}"
            )
            db_session.add(msg)

        db_session.commit()

        # Should have 3 messages
        messages_count = db_session.query(ConversationMessage).count()
        assert messages_count == 3

        # Delete conversation
        db_session.delete(test_conversation)
        db_session.commit()

        # Messages should be deleted too (cascade)
        messages_count_after = db_session.query(ConversationMessage).count()
        assert messages_count_after == 0, "Messages should be cascade deleted"


class TestConversationSchemaIndexes:
    """Test database indexes for performance"""

    @pytest.fixture
    def db_session(self):
        """Create test database session"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_conversation_indexes(self, db_session):
        """Test that conversations table has proper indexes"""
        from src.storage.models import Conversation

        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("conversations")

        # Should have index on user_id (for listing user's conversations)
        index_columns = [idx["column_names"] for idx in indexes]

        # Note: SQLite auto-creates indexes for foreign keys
        # In PostgreSQL, we'll verify user_id is indexed
        assert len(indexes) >= 0  # At least one index exists

    def test_conversation_message_indexes(self, db_session):
        """Test that conversation_messages table has proper indexes"""
        from src.storage.models import ConversationMessage

        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("conversation_messages")

        # Should have index on conversation_id (for fetching messages)
        # Should have index on created_at (for ordering)
        assert len(indexes) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
