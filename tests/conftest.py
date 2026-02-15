"""Pytest fixtures for ACMS storage tests."""

import pytest
import pytest_asyncio
import asyncio
import uuid
from datetime import datetime

from src.storage.database import get_db_pool, close_db_pool, get_engine, get_session
from src.storage.models import User


# Initialize SQLAlchemy engine at module load to establish greenlet context
_test_engine = None


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def initialize_engine():
    """Initialize SQLAlchemy engine before any tests run."""
    global _test_engine
    _test_engine = get_engine()
    yield
    # Cleanup handled by individual fixtures


@pytest_asyncio.fixture(scope="function")
async def db_pool():
    """Get database connection pool for tests."""
    # Initialize SQLAlchemy engine first (fixes greenlet issues)
    engine = get_engine()

    # Get asyncpg pool
    pool = await get_db_pool()
    yield pool

    # Cleanup
    await close_db_pool()
    if engine:
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_pool):
    """Create a test user in the database.

    Returns a User object with valid UUID that can be used in tests.
    """
    user_id = uuid.uuid4()

    async with db_pool.acquire() as conn:
        # Insert test user
        await conn.execute(
            """
            INSERT INTO users (user_id, username, created_at, updated_at, is_active)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
            f"test_user_{user_id.hex[:8]}",
            datetime.now(),
            datetime.now(),
            True
        )

    # Return user data as dict
    return {
        "user_id": str(user_id),
        "username": f"test_user_{user_id.hex[:8]}",
        "created_at": datetime.now(),
        "is_active": True
    }


@pytest_asyncio.fixture(scope="session", autouse=True)
async def default_user():
    """Create default MCP user for testing.

    This fixture creates the default user used by MCP tools.
    Runs once per session and is auto-used.
    """
    from src.mcp.config import MCPConfig
    from uuid import UUID

    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Insert default user
            await conn.execute(
                """
                INSERT INTO users (user_id, username, created_at, updated_at, is_active)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) DO NOTHING
                """,
                UUID(MCPConfig.DEFAULT_USER_ID),
                "default_mcp_user",
                datetime.now(),
                datetime.now(),
                True
            )
    finally:
        await close_db_pool()

    # Return user ID for tests that need it
    return MCPConfig.DEFAULT_USER_ID


@pytest_asyncio.fixture(scope="function")
async def cleanup_test_data(db_pool):
    """Cleanup test data after each test (optional)."""
    yield
    # Cleanup code here if needed
    # For now, we let test database accumulate test data
