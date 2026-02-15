"""
Test Suite for Gemini Importer (Hybrid Approach - ZIP + API)
Tests import of Gemini conversations from both local ZIP exports and API

Gemini export format differs from ChatGPT:
- Exports as ZIP containing JSON files (one per conversation)
- Can also fetch via API (Google Generative AI API)
- Simpler structure than ChatGPT (no complex mapping)
- Each message has: role (user/model), parts (text array), create_time
"""

import pytest
import json
import os
import tempfile
import zipfile
from datetime import datetime
from uuid import UUID


@pytest.fixture
def sample_gemini_conversation():
    """Sample Gemini conversation JSON (from ZIP export)"""
    return {
        "id": "conv_gemini_12345",
        "title": "Understanding async in Python",
        "create_time": "2024-10-20T14:30:00Z",
        "update_time": "2024-10-20T14:35:00Z",
        "messages": [
            {
                "id": "msg_1",
                "role": "user",
                "parts": [
                    {"text": "Explain async/await in Python"}
                ],
                "create_time": "2024-10-20T14:30:00Z"
            },
            {
                "id": "msg_2",
                "role": "model",
                "parts": [
                    {"text": "Async/await in Python enables asynchronous programming by allowing functions to pause execution..."}
                ],
                "create_time": "2024-10-20T14:30:15Z"
            }
        ],
        "metadata": {
            "model": "gemini-1.5-pro",
            "language": "en"
        }
    }


@pytest.fixture
def sample_gemini_zip(sample_gemini_conversation):
    """Create a temporary Gemini ZIP export with sample conversations"""
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "gemini_export.zip")

    # Create ZIP with conversation JSON files
    with zipfile.ZipFile(zip_path, 'w') as zf:
        # Add conversation file
        conv_json = json.dumps(sample_gemini_conversation, indent=2)
        zf.writestr("conversation_1.json", conv_json)

        # Add another conversation for multi-conversation test
        conv2 = sample_gemini_conversation.copy()
        conv2['id'] = "conv_gemini_67890"
        conv2['title'] = "Python decorators explained"
        zf.writestr("conversation_2.json", json.dumps(conv2, indent=2))

    yield zip_path

    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
    if os.path.exists(temp_dir):
        os.rmdir(temp_dir)


@pytest.mark.asyncio
async def test_gemini_importer_creates_conversation_thread(sample_gemini_zip):
    """
    Test 1: Creates conversation_threads record from Gemini ZIP export

    Expected behavior:
    - Extract JSON files from ZIP
    - Parse Gemini conversation format
    - Create 1 record in conversation_threads table
    - Store title, timestamps, source='gemini'
    - Return import stats
    """
    from src.importers.gemini_importer import GeminiImporter
    from src.storage.database import get_db_pool

    importer = GeminiImporter()
    await importer.initialize()

    result = await importer.import_from_zip(sample_gemini_zip)

    # Verify stats
    assert 'conversations_imported' in result
    assert 'turns_created' in result
    assert 'errors' in result

    assert result['conversations_imported'] >= 1, "Should import at least 1 conversation"
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
            WHERE source = 'gemini'
            ORDER BY imported_at DESC
            LIMIT 1
            """
        )

    assert len(threads) >= 1, "Should have at least 1 conversation thread"

    thread = threads[0]
    assert thread['source'] == 'gemini'
    assert 'async' in thread['title'].lower() or 'decorator' in thread['title'].lower()
    assert thread['turn_count'] == 2, "Should have 2 turns"
    assert thread['created_at'] is not None
    assert thread['imported_at'] is not None

    # Verify metadata
    metadata = thread['metadata_json']
    assert metadata is not None
    if isinstance(metadata, str):
        metadata = json.loads(metadata)

    assert 'model' in metadata or 'gemini' in str(metadata).lower()


@pytest.mark.asyncio
async def test_gemini_importer_creates_conversation_turns(sample_gemini_zip):
    """
    Test 2: Creates conversation_turns records in correct order

    Expected behavior:
    - Store each user/model message as separate turn
    - Preserve turn order (turn_number: 1, 2, 3...)
    - Store role (user/model)
    - Preserve original content from parts array
    """
    from src.importers.gemini_importer import GeminiImporter
    from src.storage.database import get_db_pool

    importer = GeminiImporter()
    await importer.initialize()

    await importer.import_from_zip(sample_gemini_zip)

    # Get conversation thread
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        thread = await conn.fetchrow(
            "SELECT thread_id FROM conversation_threads WHERE source = 'gemini' ORDER BY imported_at DESC LIMIT 1"
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
    assert 'async/await' in turn1['content'].lower() or 'explain' in turn1['content'].lower()
    assert turn1['original_message_id'] is not None

    # Verify turn 2 (model/assistant)
    turn2 = turns[1]
    assert turn2['turn_number'] == 2
    assert turn2['role'] in ['model', 'assistant']  # Should normalize to 'assistant'
    assert 'asynchronous' in turn2['content'].lower() or 'async' in turn2['content'].lower()


@pytest.mark.asyncio
async def test_gemini_importer_generates_dual_embeddings(sample_gemini_zip):
    """
    Test 3: Generates embeddings for both thread and individual turns

    Expected behavior:
    - Generate full conversation embedding (stored in conversation_threads)
    - Generate individual turn embeddings (stored in conversation_turns)
    - Use OpenAI embeddings (consistent with ChatGPT importer)
    - Store in Weaviate for unified search
    """
    from src.importers.gemini_importer import GeminiImporter
    from src.storage.database import get_db_pool

    importer = GeminiImporter()
    await importer.initialize()

    await importer.import_from_zip(sample_gemini_zip)

    # Check thread embedding
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        thread = await conn.fetchrow(
            "SELECT thread_id, embedding_vector_id FROM conversation_threads WHERE source = 'gemini' ORDER BY imported_at DESC LIMIT 1"
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
async def test_gemini_importer_handles_multi_turn_conversations():
    """
    Test 4: Handles multi-turn Gemini conversations (5+ turns)

    Expected behavior:
    - Extract all turns in order
    - Preserve context across turns
    - Handle user→model→user→model pattern
    - Handle Gemini's parts array structure
    """
    from src.importers.gemini_importer import GeminiImporter
    from src.storage.database import get_db_pool

    # Create multi-turn Gemini conversation
    multi_turn_conv = {
        "id": "conv_gemini_multi",
        "title": "Python best practices discussion",
        "create_time": "2024-10-20T10:00:00Z",
        "update_time": "2024-10-20T10:15:00Z",
        "messages": [
            {
                "id": "msg_1",
                "role": "user",
                "parts": [{"text": "What are Python best practices?"}],
                "create_time": "2024-10-20T10:00:00Z"
            },
            {
                "id": "msg_2",
                "role": "model",
                "parts": [{"text": "Key Python best practices include: PEP 8 style guide, type hints..."}],
                "create_time": "2024-10-20T10:00:15Z"
            },
            {
                "id": "msg_3",
                "role": "user",
                "parts": [{"text": "Can you elaborate on type hints?"}],
                "create_time": "2024-10-20T10:05:00Z"
            },
            {
                "id": "msg_4",
                "role": "model",
                "parts": [{"text": "Type hints in Python 3.5+ allow you to annotate function parameters..."}],
                "create_time": "2024-10-20T10:05:30Z"
            },
            {
                "id": "msg_5",
                "role": "user",
                "parts": [{"text": "Show me examples"}],
                "create_time": "2024-10-20T10:10:00Z"
            },
            {
                "id": "msg_6",
                "role": "model",
                "parts": [{"text": "Here are examples of type hints: def greet(name: str) -> str: ..."}],
                "create_time": "2024-10-20T10:10:45Z"
            }
        ],
        "metadata": {
            "model": "gemini-1.5-pro"
        }
    }

    # Create temp ZIP with multi-turn conversation
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "gemini_multi.zip")

    with zipfile.ZipFile(zip_path, 'w') as zf:
        conv_json = json.dumps(multi_turn_conv, indent=2)
        zf.writestr("multi_turn.json", conv_json)

    try:
        importer = GeminiImporter()
        await importer.initialize()

        result = await importer.import_from_zip(zip_path)

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
                WHERE source = 'gemini'
                AND title = 'Python best practices discussion'
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

            # Verify alternating user/model pattern
            expected_roles = ['user', 'assistant', 'user', 'assistant', 'user', 'assistant']
            actual_roles = [turn['role'] for turn in turns]
            assert actual_roles == expected_roles, "Roles should be normalized (model→assistant)"

    finally:
        # Cleanup
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


@pytest.mark.asyncio
async def test_gemini_importer_prevents_duplicate_imports(sample_gemini_zip):
    """
    Test 5: Prevents duplicate imports using unique constraint

    Expected behavior:
    - First import succeeds
    - Second import with same data should skip (no duplicates)
    - Use original_thread_id (Gemini conversation ID) for deduplication
    - Return appropriate stats showing skipped conversations
    """
    from src.importers.gemini_importer import GeminiImporter

    importer = GeminiImporter()
    await importer.initialize()

    # First import
    result1 = await importer.import_from_zip(sample_gemini_zip)
    assert result1['conversations_imported'] >= 1
    assert result1['errors'] == 0

    # Second import (should skip duplicates)
    result2 = await importer.import_from_zip(sample_gemini_zip)
    assert result2['conversations_imported'] == 0, "Should skip duplicate conversations"
    # Skipped conversations should be tracked (not counted as errors)


@pytest.mark.asyncio
async def test_gemini_importer_handles_invalid_zip():
    """
    Test 6: Gracefully handles invalid ZIP files

    Expected behavior:
    - Catch ZIP extraction errors
    - Catch JSON parsing errors within ZIP
    - Return error in stats or raise appropriate exception
    - Don't crash the import process
    """
    from src.importers.gemini_importer import GeminiImporter

    # Create invalid ZIP file
    fd, path = tempfile.mkstemp(suffix='.zip')
    with os.fdopen(fd, 'w') as f:
        f.write("This is not a valid ZIP file")

    try:
        importer = GeminiImporter()
        await importer.initialize()

        # Should raise appropriate exception
        with pytest.raises((zipfile.BadZipFile, ValueError, Exception)):
            await importer.import_from_zip(path)

    finally:
        # Cleanup
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.asyncio
async def test_gemini_importer_handles_multipart_messages():
    """
    Test 7: Handles Gemini messages with multiple parts

    Expected behavior:
    - Gemini messages can have multiple parts (text, images, etc.)
    - Concatenate text parts with proper formatting
    - Preserve all text content
    - Handle non-text parts gracefully (skip or note in metadata)
    """
    from src.importers.gemini_importer import GeminiImporter
    from src.storage.database import get_db_pool

    # Create conversation with multipart messages
    multipart_conv = {
        "id": "conv_gemini_multipart",
        "title": "Multipart message test",
        "create_time": "2024-10-20T12:00:00Z",
        "update_time": "2024-10-20T12:05:00Z",
        "messages": [
            {
                "id": "msg_1",
                "role": "user",
                "parts": [
                    {"text": "Part 1: Introduction"},
                    {"text": "Part 2: Details"},
                    {"text": "Part 3: Question"}
                ],
                "create_time": "2024-10-20T12:00:00Z"
            },
            {
                "id": "msg_2",
                "role": "model",
                "parts": [
                    {"text": "Response to all parts: ..."}
                ],
                "create_time": "2024-10-20T12:00:15Z"
            }
        ],
        "metadata": {
            "model": "gemini-1.5-pro"
        }
    }

    # Create temp ZIP
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "gemini_multipart.zip")

    with zipfile.ZipFile(zip_path, 'w') as zf:
        conv_json = json.dumps(multipart_conv, indent=2)
        zf.writestr("multipart.json", conv_json)

    try:
        importer = GeminiImporter()
        await importer.initialize()

        result = await importer.import_from_zip(zip_path)

        # Verify import succeeded
        assert result['conversations_imported'] == 1
        assert result['turns_created'] == 2

        # Verify content concatenation
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            turn = await conn.fetchrow(
                """
                SELECT content
                FROM conversation_turns ct
                JOIN conversation_threads th ON ct.thread_id = th.thread_id
                WHERE th.source = 'gemini'
                AND th.title = 'Multipart message test'
                AND ct.turn_number = 1
                """
            )

            assert turn is not None
            # All three parts should be present
            assert 'Part 1: Introduction' in turn['content']
            assert 'Part 2: Details' in turn['content']
            assert 'Part 3: Question' in turn['content']

    finally:
        # Cleanup
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


@pytest.mark.asyncio
async def test_gemini_importer_normalizes_role_names():
    """
    Test 8: Normalizes Gemini role names to standard format

    Expected behavior:
    - Gemini uses 'model' for AI responses
    - Should normalize to 'assistant' for consistency with ChatGPT/Claude
    - Preserve 'user' role as-is
    - Store in conversation_turns with normalized roles
    """
    from src.importers.gemini_importer import GeminiImporter
    from src.storage.database import get_db_pool

    importer = GeminiImporter()
    await importer.initialize()

    # Use fixture with Gemini 'model' role
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "gemini_roles.zip")

    conv = {
        "id": "conv_roles",
        "title": "Role normalization test",
        "create_time": "2024-10-20T13:00:00Z",
        "update_time": "2024-10-20T13:01:00Z",
        "messages": [
            {
                "id": "m1",
                "role": "user",
                "parts": [{"text": "Hello"}],
                "create_time": "2024-10-20T13:00:00Z"
            },
            {
                "id": "m2",
                "role": "model",  # Gemini uses 'model' not 'assistant'
                "parts": [{"text": "Hi there!"}],
                "create_time": "2024-10-20T13:00:05Z"
            }
        ]
    }

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("roles.json", json.dumps(conv, indent=2))

    try:
        await importer.import_from_zip(zip_path)

        # Verify role normalization
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            turns = await conn.fetch(
                """
                SELECT role
                FROM conversation_turns ct
                JOIN conversation_threads th ON ct.thread_id = th.thread_id
                WHERE th.source = 'gemini'
                AND th.title = 'Role normalization test'
                ORDER BY ct.turn_number
                """
            )

            assert len(turns) == 2
            assert turns[0]['role'] == 'user'
            assert turns[1]['role'] == 'assistant', "Gemini 'model' should be normalized to 'assistant'"

    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
