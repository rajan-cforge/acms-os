"""Database connection management with connection pooling.

Provides async PostgreSQL connection pool using asyncpg.
Connection pool configuration: max 20 connections.
"""

import os
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from src.storage.models import Base

# Database configuration from environment
# Prefer DATABASE_URL, fallback to individual vars
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Parse from DATABASE_URL
    # Format: postgresql://user:pass@host:port/db
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL)
    DB_HOST = parsed.hostname or "localhost"
    DB_PORT = parsed.port or 5432
    DB_NAME = parsed.path.lstrip("/") or "acms"
    DB_USER = parsed.username or "acms"
    DB_PASSWORD = parsed.password or ""
else:
    # Fallback to individual env vars (for local development)
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    DB_NAME = os.getenv("POSTGRES_DB", "acms")
    DB_USER = os.getenv("POSTGRES_USER", "acms")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# Connection pool settings
MAX_POOL_SIZE = 20
MIN_POOL_SIZE = 5
POOL_TIMEOUT = 30  # seconds

# Global connection pool
_pool: Optional[asyncpg.Pool] = None
_engine = None
_session_factory = None


async def get_db_pool() -> asyncpg.Pool:
    """Get or create the database connection pool.

    Returns:
        asyncpg.Pool: Connection pool instance
    """
    global _pool

    if _pool is None:
        dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        _pool = await asyncpg.create_pool(
            dsn,
            min_size=MIN_POOL_SIZE,
            max_size=MAX_POOL_SIZE,
            timeout=POOL_TIMEOUT,
            command_timeout=60,
        )

    return _pool


async def close_db_pool():
    """Close the database connection pool."""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None


def get_engine():
    """Get or create SQLAlchemy async engine.

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    global _engine

    if _engine is None:
        database_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        _engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL logging
            poolclass=AsyncAdaptedQueuePool,  # Use proper connection pooling
            pool_size=10,  # Core pool size
            max_overflow=20,  # Allow 20 additional connections when needed
            pool_pre_ping=True,  # Verify connections before using them
            pool_recycle=3600,  # Recycle connections after 1 hour
            future=True,
        )

    return _engine


def get_session_factory():
    """Get or create SQLAlchemy session factory.

    Returns:
        async_sessionmaker: Session factory
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _session_factory


@asynccontextmanager
async def get_db_connection():
    """Get a raw asyncpg connection from the pool.

    Yields:
        asyncpg.Connection: Raw database connection

    Example:
        async with get_db_connection() as conn:
            rows = await conn.fetch("SELECT * FROM table")
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        yield conn


@asynccontextmanager
async def get_session():
    """Get a database session from the pool.

    Yields:
        AsyncSession: Database session

    Example:
        async with get_session() as session:
            result = await session.execute(query)
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db():
    """Initialize database schema (create all tables).

    This should be called after migrations in production.
    For development, use Alembic migrations instead.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables():
    """Drop all tables (DANGER: use only in testing).

    WARNING: This will delete all data!
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def check_connection() -> bool:
    """Check if database connection is working.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        print(f"Database connection check failed: {e}")
        return False


async def get_connection_info() -> dict:
    """Get connection pool information.

    Returns:
        dict: Connection pool statistics
    """
    pool = await get_db_pool()

    return {
        "size": pool.get_size(),
        "max_size": pool.get_max_size(),
        "min_size": pool.get_min_size(),
        "free_size": pool.get_idle_size(),
        "host": DB_HOST,
        "port": DB_PORT,
        "database": DB_NAME,
    }


if __name__ == "__main__":
    # Test connection
    async def test():
        print("Testing database connection...")
        connected = await check_connection()
        if connected:
            print("✅ Database connection successful")
            info = await get_connection_info()
            print(f"Connection pool info: {info}")
        else:
            print("❌ Database connection failed")
        await close_db_pool()

    asyncio.run(test())
