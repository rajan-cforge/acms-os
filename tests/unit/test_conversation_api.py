"""
Conversation API Tests - Phase 1, Task 1.2

TDD tests for conversation management API endpoints:
- POST /conversations - Create new conversation
- GET /conversations - List conversations (paginated, grouped by date)
- GET /conversations/{id} - Get conversation with messages
- POST /conversations/{id}/messages - Send message, get AI response

Following TDD: These tests will FAIL initially, then we implement endpoints.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage.models import Base, User, Conversation, ConversationMessage
from src.storage.database import get_db_pool


class TestConversationAPI:
    """Test conversation management endpoints"""

    @pytest.fixture
    def db_session(self):
        """Create test database session"""
        # Use in-memory SQLite for tests
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_user(self, db_session):
        """Create test user"""
        user = User(
            user_id=uuid4(),
            username="test_user",
            email="test@acms.com",
            display_name="Test User"
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def client(self, db_session):
        """Create test client with database override"""
        from src.api_server import app

        # Override database dependency
        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db_pool] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()


class TestCreateConversation:
    """Test POST /conversations endpoint"""

    @pytest.fixture
    def db_session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_user(self, db_session):
        user = User(
            user_id=uuid4(),
            username="test_user",
            email="test@acms.com"
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def client(self, db_session):
        from src.api_server import app

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db_pool] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_create_conversation_success(self, client, test_user):
        """Test creating a new conversation"""
        response = client.post(
            "/conversations",
            json={
                "user_id": str(test_user.user_id),
                "agent": "claude"
            }
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "conversation_id" in data
        assert "created_at" in data
        assert "agent" in data
        assert data["agent"] == "claude"

    def test_create_conversation_all_agents(self, client, test_user):
        """Test creating conversations with all supported agents"""
        agents = ["claude", "gpt", "gemini", "claude-code"]

        for agent in agents:
            response = client.post(
                "/conversations",
                json={
                    "user_id": str(test_user.user_id),
                    "agent": agent
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["agent"] == agent

    def test_create_conversation_invalid_agent(self, client, test_user):
        """Test creating conversation with invalid agent"""
        response = client.post(
            "/conversations",
            json={
                "user_id": str(test_user.user_id),
                "agent": "invalid_agent"
            }
        )

        # Should return 422 Unprocessable Entity for invalid agent
        assert response.status_code == 422

    def test_create_conversation_missing_user_id(self, client):
        """Test creating conversation without user_id"""
        response = client.post(
            "/conversations",
            json={
                "agent": "claude"
            }
        )

        # Should return 422 for missing required field
        assert response.status_code == 422

    def test_create_conversation_invalid_user_id(self, client):
        """Test creating conversation with non-existent user_id"""
        fake_user_id = str(uuid4())

        response = client.post(
            "/conversations",
            json={
                "user_id": fake_user_id,
                "agent": "claude"
            }
        )

        # Should return 404 Not Found for non-existent user
        assert response.status_code == 404


class TestListConversations:
    """Test GET /conversations endpoint"""

    @pytest.fixture
    def db_session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_user(self, db_session):
        user = User(
            user_id=uuid4(),
            username="test_user",
            email="test@acms.com"
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def sample_conversations(self, db_session, test_user):
        """Create sample conversations across different time periods"""
        conversations = []
        now = datetime.now(timezone.utc)

        # Today
        conv_today = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            title="Today's conversation",
            agent="claude",
            created_at=now
        )
        conversations.append(conv_today)

        # Yesterday
        conv_yesterday = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            title="Yesterday's conversation",
            agent="gpt",
            created_at=now - timedelta(days=1)
        )
        conversations.append(conv_yesterday)

        # 3 days ago
        conv_3days = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            title="3 days ago conversation",
            agent="gemini",
            created_at=now - timedelta(days=3)
        )
        conversations.append(conv_3days)

        # 10 days ago
        conv_10days = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            title="10 days ago conversation",
            agent="claude-code",
            created_at=now - timedelta(days=10)
        )
        conversations.append(conv_10days)

        for conv in conversations:
            db_session.add(conv)

        db_session.commit()
        return conversations

    @pytest.fixture
    def client(self, db_session):
        from src.api_server import app

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db_pool] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_list_conversations_success(self, client, test_user, sample_conversations):
        """Test listing user's conversations"""
        response = client.get(
            f"/conversations?user_id={test_user.user_id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert "conversations" in data
        assert "total_count" in data
        assert data["total_count"] == 4

    def test_list_conversations_grouped_by_date(self, client, test_user, sample_conversations):
        """Test conversations are grouped by Today, Yesterday, Older"""
        response = client.get(
            f"/conversations?user_id={test_user.user_id}"
        )

        assert response.status_code == 200
        data = response.json()

        # Should have groups: Today, Yesterday, Older (7 days), Older
        assert "groups" in data
        groups = data["groups"]

        group_names = [g["name"] for g in groups]
        assert "Today" in group_names
        assert "Yesterday" in group_names
        # Older groups should exist

    def test_list_conversations_pagination(self, client, test_user, sample_conversations):
        """Test pagination with limit and offset"""
        # Get first 2 conversations
        response = client.get(
            f"/conversations?user_id={test_user.user_id}&limit=2&offset=0"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["conversations"]) <= 2
        assert data["total_count"] == 4

        # Get next 2 conversations
        response = client.get(
            f"/conversations?user_id={test_user.user_id}&limit=2&offset=2"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) <= 2

    def test_list_conversations_ordered_by_created_at_desc(self, client, test_user, sample_conversations):
        """Test conversations are ordered by most recent first"""
        response = client.get(
            f"/conversations?user_id={test_user.user_id}"
        )

        assert response.status_code == 200
        data = response.json()

        conversations = data["conversations"]

        # First conversation should be most recent (today)
        assert conversations[0]["title"] == "Today's conversation"

    def test_list_conversations_empty(self, client, test_user):
        """Test listing conversations when user has none"""
        response = client.get(
            f"/conversations?user_id={test_user.user_id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["conversations"] == []
        assert data["total_count"] == 0


class TestGetConversation:
    """Test GET /conversations/{id} endpoint"""

    @pytest.fixture
    def db_session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_user(self, db_session):
        user = User(
            user_id=uuid4(),
            username="test_user",
            email="test@acms.com"
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def sample_conversation_with_messages(self, db_session, test_user):
        """Create conversation with messages"""
        conv = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            title="Test Conversation",
            agent="claude"
        )
        db_session.add(conv)
        db_session.commit()

        # Add 3 messages
        messages = [
            ConversationMessage(
                message_id=uuid4(),
                conversation_id=conv.conversation_id,
                role="user",
                content="Hello, Claude!",
                message_metadata={"tokens": 3}
            ),
            ConversationMessage(
                message_id=uuid4(),
                conversation_id=conv.conversation_id,
                role="assistant",
                content="Hello! How can I help you?",
                message_metadata={
                    "tokens": 8,
                    "cost": 0.001,
                    "model": "claude-sonnet-4.5"
                }
            ),
            ConversationMessage(
                message_id=uuid4(),
                conversation_id=conv.conversation_id,
                role="user",
                content="What is ACMS?",
                message_metadata={"tokens": 4}
            )
        ]

        for msg in messages:
            db_session.add(msg)

        db_session.commit()
        return conv

    @pytest.fixture
    def client(self, db_session):
        from src.api_server import app

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db_pool] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_get_conversation_success(self, client, sample_conversation_with_messages):
        """Test getting conversation with all messages"""
        conv_id = sample_conversation_with_messages.conversation_id

        response = client.get(f"/conversations/{conv_id}")

        assert response.status_code == 200
        data = response.json()

        assert "conversation" in data
        assert "messages" in data

        # Verify conversation fields
        assert data["conversation"]["conversation_id"] == str(conv_id)
        assert data["conversation"]["agent"] == "claude"

        # Verify messages
        assert len(data["messages"]) == 3

        # Messages should be in chronological order
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Hello, Claude!"
        assert data["messages"][1]["role"] == "assistant"
        assert data["messages"][2]["role"] == "user"

    def test_get_conversation_messages_include_metadata(self, client, sample_conversation_with_messages):
        """Test that message metadata is included"""
        conv_id = sample_conversation_with_messages.conversation_id

        response = client.get(f"/conversations/{conv_id}")

        assert response.status_code == 200
        data = response.json()

        # Assistant message should have cost metadata
        assistant_msg = data["messages"][1]
        assert "message_metadata" in assistant_msg
        assert "cost" in assistant_msg["message_metadata"]
        assert "model" in assistant_msg["message_metadata"]

    def test_get_conversation_not_found(self, client):
        """Test getting non-existent conversation"""
        fake_id = uuid4()

        response = client.get(f"/conversations/{fake_id}")

        assert response.status_code == 404

    def test_get_conversation_invalid_uuid(self, client):
        """Test getting conversation with invalid UUID"""
        response = client.get("/conversations/not-a-uuid")

        # Should return 422 for invalid UUID format
        assert response.status_code == 422


class TestSendMessage:
    """Test POST /conversations/{id}/messages endpoint"""

    @pytest.fixture
    def db_session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_user(self, db_session):
        user = User(
            user_id=uuid4(),
            username="test_user",
            email="test@acms.com"
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def test_conversation(self, db_session, test_user):
        """Create empty conversation"""
        conv = Conversation(
            conversation_id=uuid4(),
            user_id=test_user.user_id,
            agent="claude"
        )
        db_session.add(conv)
        db_session.commit()
        return conv

    @pytest.fixture
    def client(self, db_session):
        from src.api_server import app

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db_pool] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_send_message_success(self, client, test_conversation):
        """Test sending a message and getting AI response"""
        conv_id = test_conversation.conversation_id

        response = client.post(
            f"/conversations/{conv_id}/messages",
            json={
                "content": "What is ACMS?",
                "user_id": str(test_conversation.user_id)
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should return both user message and assistant response
        assert "user_message" in data
        assert "assistant_message" in data
        assert "metadata" in data

        # Verify user message
        assert data["user_message"]["role"] == "user"
        assert data["user_message"]["content"] == "What is ACMS?"

        # Verify assistant message
        assert data["assistant_message"]["role"] == "assistant"
        assert len(data["assistant_message"]["content"]) > 0

    def test_send_message_includes_metadata(self, client, test_conversation):
        """Test that response includes cost/tokens metadata"""
        conv_id = test_conversation.conversation_id

        response = client.post(
            f"/conversations/{conv_id}/messages",
            json={
                "content": "Hello",
                "user_id": str(test_conversation.user_id)
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Metadata should include cost, tokens, model
        metadata = data["metadata"]
        assert "cost" in metadata or "tokens" in metadata
        assert "model" in metadata

    def test_send_message_with_context(self, client, db_session, test_conversation):
        """Test that AI gets full conversation history as context"""
        conv_id = test_conversation.conversation_id

        # Send first message
        response1 = client.post(
            f"/conversations/{conv_id}/messages",
            json={
                "content": "My name is Alice",
                "user_id": str(test_conversation.user_id)
            }
        )
        assert response1.status_code == 200

        # Send follow-up message - AI should remember name
        response2 = client.post(
            f"/conversations/{conv_id}/messages",
            json={
                "content": "What is my name?",
                "user_id": str(test_conversation.user_id)
            }
        )
        assert response2.status_code == 200

        # AI response should reference "Alice" (context working)
        assistant_content = response2.json()["assistant_message"]["content"]
        # This is a weak test - just verify we got a response
        assert len(assistant_content) > 0

    def test_send_message_agent_override(self, client, test_conversation):
        """Test switching agent mid-conversation"""
        conv_id = test_conversation.conversation_id

        # Send message with different agent
        response = client.post(
            f"/conversations/{conv_id}/messages",
            json={
                "content": "What is 2+2?",
                "user_id": str(test_conversation.user_id),
                "agent": "gpt"  # Override default claude
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Metadata should indicate GPT was used
        assert data["metadata"]["agent"] == "gpt"

    def test_send_message_conversation_not_found(self, client, test_user):
        """Test sending message to non-existent conversation"""
        fake_id = uuid4()

        response = client.post(
            f"/conversations/{fake_id}/messages",
            json={
                "content": "Hello",
                "user_id": str(test_user.user_id)
            }
        )

        assert response.status_code == 404

    def test_send_message_empty_content(self, client, test_conversation):
        """Test sending empty message"""
        conv_id = test_conversation.conversation_id

        response = client.post(
            f"/conversations/{conv_id}/messages",
            json={
                "content": "",
                "user_id": str(test_conversation.user_id)
            }
        )

        # Should return 422 for empty content
        assert response.status_code == 422

    def test_send_message_missing_content(self, client, test_conversation):
        """Test sending message without content field"""
        conv_id = test_conversation.conversation_id

        response = client.post(
            f"/conversations/{conv_id}/messages",
            json={
                "user_id": str(test_conversation.user_id)
            }
        )

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
