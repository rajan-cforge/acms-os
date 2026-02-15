"""Configuration for ACMS MCP Server."""
import os
from pathlib import Path


class MCPConfig:
    """Configuration for MCP server."""

    # Server info
    SERVER_NAME = "acms-memory-server"
    SERVER_VERSION = "1.0.0"

    # Project paths
    PROJECT_ROOT = Path("/path/to/acms")

    # Database configuration (from Phase 2A)
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "40432"))
    POSTGRES_USER = os.getenv("POSTGRES_USER", "acms")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "acms_dev_password")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "acms")

    # Weaviate configuration
    WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "localhost")
    WEAVIATE_PORT = int(os.getenv("WEAVIATE_PORT", "40480"))
    WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "40481"))

    # Memory configuration
    DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"  # Fixed UUID for default user
    DEFAULT_MEMORY_TIER = "SHORT"
    MAX_SEARCH_RESULTS = 100

    # MCP server configuration
    MCP_SERVER_TIMEOUT = 30  # seconds

    @classmethod
    def get_database_url(cls) -> str:
        """Get PostgreSQL database URL."""
        return f"postgresql+asyncpg://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"

    @classmethod
    def get_weaviate_url(cls) -> str:
        """Get Weaviate HTTP URL."""
        return f"http://{cls.WEAVIATE_HOST}:{cls.WEAVIATE_PORT}"
