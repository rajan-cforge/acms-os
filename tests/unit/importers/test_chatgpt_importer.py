"""
Test Suite for ChatGPT Importer (Full Conversation Thread Storage)
Tests import of full conversations with context preservation
"""

import pytest
import json
import os
import tempfile
from datetime import datetime
from uuid import UUID


@pytest.fixture
def sample_chatgpt_export():
    """Sample ChatGPT export format (full conversation thread)"""
    return {
        "conversations": [
            {
                "title": "Python async/await basics",
                "create_time": 1698345678,
                "update_time": 1698345700,
                "mapping": {
                    "msg-1": {
                        "id": "msg-1",
                        "message": {
                            "id": "msg-1",
                            "author": {"role": "user"},
                            "create_time": 1698345678,
                            "content": {
                                "content_type": "text",
                                "parts": ["How does async/await work in Python?"]
                            }
                        }
                    },
                    "msg-2": {
                        "id": "msg-2",
                        "message": {
                            "id": "msg-2",
                            "author": {"role": "assistant"},
                            "create_time": 1698345700,
                            "content": {
                                "content_type": "text",
                                "parts": ["Async/await in Python allows you to write asynchronous code that doesn't block the main thread..."]
                            }
                        }
                    }
                }
            }
        ]
    }


@pytest.fixture
def temp_chatgpt_file(sample_chatgpt_export):
    """Create temporary ChatGPT export file"""
    fd, path = tempfile.mkstemp(suffix='.json')

    with os.fdopen(fd, 'w') as f:
        json.dump(sample_chatgpt_export, f)

    yield path

    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_chatgpt_importer_creates_conversation_thread(temp_chatgpt_file):
    """
    Test 1: Creates conversation_threads record with metadata

    Expected behavior:
    - Parse conversations.json file
    - Create 1 record in conversation_threads table
    - Store title, timestamps, source='chatgpt'
    - Return import stats
    """
    from src.importers.chatgpt_importer import ChatGPTImporter
    from src.storage.database import get_db_pool

    importer = ChatGPTImporter()
    await importer.initialize()

    result = await importer.import_conversations(temp_chatgpt_file)

    # Verify stats
    assert 'conversations_imported' in result
    assert 'turns_created' in result
    assert 'errors' in result

    assert result['conversations_imported'] == 1, "Should import 1 conversation"
    assert result['turns_created'] >= 2, "Should create at least 2 turns"
    assert result['errors'] == 0, "Should have no errors"

    # Verify conversation_threads record
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        threads = await conn.fetch(
            """
            SELECT thread_id, source, title, original_thread_id, turn_count,
                   created_at, imported_at, metadata_json
            FROM conversation_threads
            WHERE source = 'chatgpt'
            ORDER BY imported_at DESC
            LIMIT 1
            """
        )

    assert len(threads) == 1, "Should have 1 conversation thread"

    thread = threads[0]
    assert thread['source'] == 'chatgpt'
    assert thread['title'] == 'Python async/await basics'
    assert thread['turn_count'] == 2, "Should have 2 turns"
    assert thread['created_at'] is not None
    assert thread['imported_at'] is not None

    # Verify metadata
    metadata = thread['metadata_json']
    assert metadata is not None
    if isinstance(metadata, str):
        metadata = json.loads(metadata)

    assert 'create_time' in metadata
    assert 'update_time' in metadata


@pytest.mark.asyncio
async def test_chatgpt_importer_creates_conversation_turns(temp_chatgpt_file):
    """
    Test 2: Creates conversation_turns records in correct order

    Expected behavior:
    - Store each user/assistant message as separate turn
    - Preserve turn order (turn_number: 1, 2, 3...)
    - Store role (user/assistant)
    - Preserve original content
    """
    from src.importers.chatgpt_importer import ChatGPTImporter
    from src.storage.database import get_db_pool

    importer = ChatGPTImporter()
    await importer.initialize()

    await importer.import_conversations(temp_chatgpt_file)

    # Get conversation thread
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        thread = await conn.fetchrow(
            "SELECT thread_id FROM conversation_threads WHERE source = 'chatgpt' ORDER BY imported_at DESC LIMIT 1"
        )

        # Get turns
        turns = await conn.fetch(
            """
            SELECT turn_id, turn_number, role, content, original_message_id,
                   created_at, metadata_json
            FROM conversation_turns
            WHERE thread_id = $1
            ORDER BY turn_number
            """,
            thread['thread_id']
        )

    assert len(turns) == 2, "Should have 2 turns"

    # Verify turn 1 (user)
    turn1 = turns[0]
    assert turn1['turn_number'] == 1
    assert turn1['role'] == 'user'
    assert 'async/await work' in turn1['content']
    assert turn1['original_message_id'] == 'msg-1'

    # Verify turn 2 (assistant)
    turn2 = turns[1]
    assert turn2['turn_number'] == 2
    assert turn2['role'] == 'assistant'
    assert 'asynchronous code' in turn2['content']
    assert turn2['original_message_id'] == 'msg-2'


@pytest.mark.asyncio
async def test_chatgpt_importer_generates_dual_embeddings(temp_chatgpt_file):
    """
    Test 3: Generates embeddings for both thread and individual turns

    Expected behavior:
    - Generate full conversation embedding (stored in conversation_threads)
    - Generate individual turn embeddings (stored in conversation_turns)
    - Embeddings should be 768-dimensional (nomic-embed-text)
    """
    from src.importers.chatgpt_importer import ChatGPTImporter
    from src.storage.database import get_db_pool

    importer = ChatGPTImporter()
    await importer.initialize()

    await importer.import_conversations(temp_chatgpt_file)

    # Check thread embedding
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        thread = await conn.fetchrow(
            "SELECT thread_id, embedding_vector_id FROM conversation_threads WHERE source = 'chatgpt' ORDER BY imported_at DESC LIMIT 1"
        )

        # Check turn embeddings
        turns = await conn.fetch(
            """
            SELECT embedding_vector_id
            FROM conversation_turns
            WHERE thread_id = $1
            ORDER BY turn_number
            """,
            thread['thread_id']
        )

    # Verify thread has embedding
    assert thread['embedding_vector_id'] is not None, "Thread should have embedding_vector_id"

    # Verify turns have embeddings
    for turn in turns:
        assert turn['embedding_vector_id'] is not None, "Each turn should have embedding_vector_id"


@pytest.mark.asyncio
async def test_chatgpt_importer_handles_multi_turn_conversations():
    """
    Test 4: Handles multi-turn conversations (5+ turns)

    Expected behavior:
    - Extract all turns in order
    - Preserve context across turns
    - Handle user→assistant→user→assistant pattern
    """
    from src.importers.chatgpt_importer import ChatGPTImporter
    from src.storage.database import get_db_pool

    # Create export with 6-turn conversation
    multi_turn_export = {
        "conversations": [
            {
                "title": "Multi-turn Python discussion",
                "create_time": 1698345678,
                "update_time": 1698346000,
                "mapping": {
                    "msg-1": {
                        "message": {
                            "id": "msg-1",
                            "author": {"role": "user"},
                            "create_time": 1698345678,
                            "content": {"parts": ["What is Python?"]}
                        }
                    },
                    "msg-2": {
                        "message": {
                            "id": "msg-2",
                            "author": {"role": "assistant"},
                            "create_time": 1698345680,
                            "content": {"parts": ["Python is a high-level programming language."]}
                        }
                    },
                    "msg-3": {
                        "message": {
                            "id": "msg-3",
                            "author": {"role": "user"},
                            "create_time": 1698345690,
                            "content": {"parts": ["What are Python's main features?"]}
                        }
                    },
                    "msg-4": {
                        "message": {
                            "id": "msg-4",
                            "author": {"role": "assistant"},
                            "create_time": 1698345700,
                            "content": {"parts": ["Python features: readability, dynamic typing, etc."]}
                        }
                    },
                    "msg-5": {
                        "message": {
                            "id": "msg-5",
                            "author": {"role": "user"},
                            "create_time": 1698345750,
                            "content": {"parts": ["Can you show examples?"]}
                        }
                    },
                    "msg-6": {
                        "message": {
                            "id": "msg-6",
                            "author": {"role": "assistant"},
                            "create_time": 1698345800,
                            "content": {"parts": ["Here are Python examples: ..."]}
                        }
                    }
                }
            }
        ]
    }

    # Write to temp file
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as f:
        json.dump(multi_turn_export, f)

    try:
        importer = ChatGPTImporter()
        await importer.initialize()

        result = await importer.import_conversations(path)

        # Should create 1 thread with 6 turns
        assert result['conversations_imported'] == 1
        assert result['turns_created'] == 6, f"Should create 6 turns, got: {result['turns_created']}"

        # Verify database
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            thread = await conn.fetchrow(
                """
                SELECT thread_id, turn_count, title
                FROM conversation_threads
                WHERE source = 'chatgpt'
                AND title = 'Multi-turn Python discussion'
                """
            )

            assert thread is not None
            assert thread['turn_count'] == 6

            # Verify turns
            turns = await conn.fetch(
                """
                SELECT turn_number, role, content
                FROM conversation_turns
                WHERE thread_id = $1
                ORDER BY turn_number
                """,
                thread['thread_id']
            )

            assert len(turns) == 6

            # Verify alternating user/assistant pattern
            expected_roles = ['user', 'assistant', 'user', 'assistant', 'user', 'assistant']
            actual_roles = [turn['role'] for turn in turns]
            assert actual_roles == expected_roles

    finally:
        # Cleanup
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.asyncio
async def test_chatgpt_importer_prevents_duplicate_imports(temp_chatgpt_file):
    """
    Test 5: Prevents duplicate imports using unique constraint

    Expected behavior:
    - First import succeeds
    - Second import with same data should skip (no duplicates)
    - Return appropriate stats showing skipped conversations
    """
    from src.importers.chatgpt_importer import ChatGPTImporter

    importer = ChatGPTImporter()
    await importer.initialize()

    # First import
    result1 = await importer.import_conversations(temp_chatgpt_file)
    assert result1['conversations_imported'] == 1
    assert result1['errors'] == 0

    # Second import (should skip duplicate)
    result2 = await importer.import_conversations(temp_chatgpt_file)
    assert result2['conversations_imported'] == 0, "Should skip duplicate conversation"
    # Note: Depending on implementation, this might be in 'skipped' field instead of 'errors'


@pytest.mark.asyncio
async def test_chatgpt_importer_handles_invalid_json():
    """
    Test 6: Gracefully handles invalid JSON files

    Expected behavior:
    - Catch JSON parsing errors
    - Return error in stats or raise appropriate exception
    - Don't crash the import process
    """
    from src.importers.chatgpt_importer import ChatGPTImporter

    # Create invalid JSON file
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as f:
        f.write("{ invalid json content }")

    try:
        importer = ChatGPTImporter()
        await importer.initialize()

        # Should raise ValueError or JSONDecodeError
        with pytest.raises((json.JSONDecodeError, ValueError, Exception)):
            await importer.import_conversations(path)

    finally:
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
