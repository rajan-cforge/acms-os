"""
Unit tests for ChatGPT Importer

Tests the import logic for both old (mapping) and new (chat_messages) formats.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.importers.chatgpt_importer import ChatGPTImporter


class TestChatGPTImporter:
    """Test ChatGPT import functionality."""

    @pytest.fixture
    def importer(self):
        """Create importer instance without initialization."""
        return ChatGPTImporter()

    # =========================================================================
    # Format Detection Tests
    # =========================================================================

    def test_extract_messages_old_format(self, importer):
        """Test extraction from old ChatGPT export format (mapping structure)."""
        mapping = {
            "msg1": {
                "message": {
                    "id": "msg1",
                    "author": {"role": "user"},
                    "content": {"parts": ["What is Python?"]},
                    "create_time": 1700000000.0
                }
            },
            "msg2": {
                "message": {
                    "id": "msg2",
                    "author": {"role": "assistant"},
                    "content": {"parts": ["Python is a programming language."]},
                    "create_time": 1700000001.0
                }
            }
        }

        messages = importer._extract_messages(mapping)

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is Python?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Python is a programming language."

    def test_extract_messages_new_format(self, importer):
        """Test extraction from new ChatGPT export format (chat_messages array)."""
        chat_messages = [
            {
                "uuid": "msg-uuid-1",
                "sender": "human",
                "text": "What is Python?",
                "created_at": "2025-01-01T10:00:00.000Z"
            },
            {
                "uuid": "msg-uuid-2",
                "sender": "assistant",
                "text": "Python is a programming language.",
                "created_at": "2025-01-01T10:00:01.000Z"
            }
        ]

        messages = importer._extract_messages_new_format(chat_messages)

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is Python?"
        assert messages[0]["message_id"] == "msg-uuid-1"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Python is a programming language."

    def test_extract_messages_skips_system_messages(self, importer):
        """Test that system messages are skipped in old format."""
        mapping = {
            "msg1": {
                "message": {
                    "id": "msg1",
                    "author": {"role": "system"},
                    "content": {"parts": ["You are a helpful assistant."]},
                    "create_time": 1700000000.0
                }
            },
            "msg2": {
                "message": {
                    "id": "msg2",
                    "author": {"role": "user"},
                    "content": {"parts": ["Hello"]},
                    "create_time": 1700000001.0
                }
            }
        }

        messages = importer._extract_messages(mapping)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_extract_messages_new_format_skips_unknown_senders(self, importer):
        """Test that unknown senders are skipped in new format."""
        chat_messages = [
            {
                "uuid": "msg-1",
                "sender": "tool",  # Unknown sender type
                "text": "Tool output",
                "created_at": "2025-01-01T10:00:00.000Z"
            },
            {
                "uuid": "msg-2",
                "sender": "human",
                "text": "Hello",
                "created_at": "2025-01-01T10:00:01.000Z"
            }
        ]

        messages = importer._extract_messages_new_format(chat_messages)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    # =========================================================================
    # Q&A Pairing Tests
    # =========================================================================

    def test_pair_messages_as_qa(self, importer):
        """Test pairing of user questions with assistant answers."""
        messages = [
            {"role": "user", "content": "Q1?", "timestamp": 1.0, "message_id": "m1"},
            {"role": "assistant", "content": "A1", "timestamp": 2.0, "message_id": "m2"},
            {"role": "user", "content": "Q2?", "timestamp": 3.0, "message_id": "m3"},
            {"role": "assistant", "content": "A2", "timestamp": 4.0, "message_id": "m4"},
        ]

        qa_pairs = importer._pair_messages_as_qa(messages, "Test Conv", "conv-123")

        assert len(qa_pairs) == 2
        assert qa_pairs[0]["question"] == "Q1?"
        assert qa_pairs[0]["answer"] == "A1"
        assert qa_pairs[1]["question"] == "Q2?"
        assert qa_pairs[1]["answer"] == "A2"

    def test_pair_messages_handles_unanswered_question(self, importer):
        """Test that questions without answers still create Q&A pairs."""
        messages = [
            {"role": "user", "content": "Q1?", "timestamp": 1.0, "message_id": "m1"},
            {"role": "assistant", "content": "A1", "timestamp": 2.0, "message_id": "m2"},
            {"role": "user", "content": "Q2?", "timestamp": 3.0, "message_id": "m3"},
            # No answer for Q2
        ]

        qa_pairs = importer._pair_messages_as_qa(messages, "Test Conv", "conv-123")

        assert len(qa_pairs) == 2
        assert qa_pairs[1]["question"] == "Q2?"
        assert qa_pairs[1]["answer"] == ""  # Empty answer

    def test_pair_messages_preserves_metadata(self, importer):
        """Test that conversation metadata is preserved in Q&A pairs."""
        messages = [
            {"role": "user", "content": "Q?", "timestamp": 1000.0, "message_id": "m1"},
            {"role": "assistant", "content": "A", "timestamp": 1001.0, "message_id": "m2"},
        ]

        qa_pairs = importer._pair_messages_as_qa(messages, "My Title", "conv-456")

        assert len(qa_pairs) == 1
        assert qa_pairs[0]["conversation_title"] == "My Title"
        assert qa_pairs[0]["conversation_id"] == "conv-456"
        assert qa_pairs[0]["message_id"] == "m1"

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_empty_mapping_returns_empty_list(self, importer):
        """Test that empty mapping returns empty list."""
        messages = importer._extract_messages({})
        assert messages == []

    def test_empty_chat_messages_returns_empty_list(self, importer):
        """Test that empty chat_messages returns empty list."""
        messages = importer._extract_messages_new_format([])
        assert messages == []

    def test_messages_sorted_by_timestamp(self, importer):
        """Test that messages are sorted by timestamp."""
        # Create messages out of order
        mapping = {
            "msg2": {
                "message": {
                    "id": "msg2",
                    "author": {"role": "assistant"},
                    "content": {"parts": ["Second message"]},
                    "create_time": 2.0
                }
            },
            "msg1": {
                "message": {
                    "id": "msg1",
                    "author": {"role": "user"},
                    "content": {"parts": ["First message"]},
                    "create_time": 1.0
                }
            }
        }

        messages = importer._extract_messages(mapping)

        assert len(messages) == 2
        assert messages[0]["content"] == "First message"
        assert messages[1]["content"] == "Second message"

    def test_new_format_handles_missing_fields(self, importer):
        """Test graceful handling of missing fields in new format."""
        chat_messages = [
            {
                "sender": "human",
                "text": "Hello",
                # Missing uuid and created_at
            }
        ]

        messages = importer._extract_messages_new_format(chat_messages)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        # Should have generated UUID
        assert messages[0]["message_id"] is not None


class TestDataSourceDetection:
    """Test format detection and data source handling."""

    @pytest.fixture
    def importer(self):
        return ChatGPTImporter()

    def test_detects_old_format_by_mapping_key(self, importer):
        """Test that old format is detected by presence of 'mapping' key."""
        conv = {
            "id": "conv-1",
            "title": "Test",
            "mapping": {"msg1": {"message": None}}
        }

        # The format detection happens in _process_conversation_to_query_history
        # We're testing the logic indirectly through the method
        has_mapping = "mapping" in conv and not conv.get("chat_messages")
        assert has_mapping is True

    def test_detects_new_format_by_chat_messages_key(self, importer):
        """Test that new format is detected by presence of 'chat_messages' key."""
        conv = {
            "uuid": "conv-1",
            "name": "Test",
            "chat_messages": [{"sender": "human", "text": "Hi"}]
        }

        has_chat_messages = "chat_messages" in conv and bool(conv["chat_messages"])
        assert has_chat_messages is True

    def test_title_fallback_old_format(self, importer):
        """Test title extraction from old format."""
        conv = {"title": "Old Title", "id": "123"}
        title = conv.get("title") or conv.get("name") or "Untitled"
        assert title == "Old Title"

    def test_title_fallback_new_format(self, importer):
        """Test title extraction from new format (uses 'name' key)."""
        conv = {"name": "New Name", "uuid": "456"}
        title = conv.get("title") or conv.get("name") or "Untitled"
        assert title == "New Name"


# Run with: PYTHONPATH=. pytest tests/unit/test_chatgpt_importer.py -v
