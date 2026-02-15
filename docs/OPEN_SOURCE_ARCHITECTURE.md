# ACMS Open Source Architecture

## Document Information
- **Version**: 1.0.0
- **Date**: February 15, 2026
- **Author**: Software Architect
- **Status**: Design Complete

---

## Executive Summary

This document provides the architecture for open-sourcing ACMS (Adaptive Context Memory System). It addresses seven key design decisions: secrets management, deployment modes, configurable ports, encryption key handling, feature detection, repository structure, and CI/CD pipelines.

ACMS is a privacy-first AI memory system that enables users to maintain context across conversations with multiple AI agents (Claude, GPT, Gemini, Ollama). The open-source version must be secure-by-default, easy to deploy, and extensible for contributors.

---

## Table of Contents

1. [Current Architecture Analysis](#1-current-architecture-analysis)
2. [Secrets and Configuration Management](#2-secrets-and-configuration-management)
3. [Deployment Modes](#3-deployment-modes)
4. [Configurable Port System](#4-configurable-port-system)
5. [Encryption Key Management](#5-encryption-key-management)
6. [Feature Detection System](#6-feature-detection-system)
7. [Repository Structure](#7-repository-structure)
8. [CI/CD Pipeline](#8-cicd-pipeline)
9. [Migration Path](#9-migration-path)
10. [Security Considerations](#10-security-considerations)

---

## 1. Current Architecture Analysis

### 1.1 Technology Stack

| Layer | Technology | Current Port |
|-------|------------|--------------|
| Frontend | Electron (React) | - |
| Backend | FastAPI (Python 3.11) | 40080 |
| Database | PostgreSQL 16 | 40432 |
| Vector DB | Weaviate v4 | 40480/40481 |
| Cache | Redis 7 | 40379 |
| Local LLM | Ollama | 40434 |
| AI Agents | Claude Opus 4.5, GPT-5.1, Gemini 3, Ollama | External APIs |

### 1.2 Current Configuration Sources

The codebase currently retrieves configuration from multiple sources:

1. **Environment Variables** (`os.getenv()`): 34 files use env vars
2. **docker-compose.yml**: Hardcoded values for Docker networking
3. **Hardcoded defaults**: Scattered across modules
4. **`.env.example`**: Partial documentation of required variables

### 1.3 Current Feature Flags

```python
# Existing feature flags found in codebase:
ENABLE_NEW_RETRIEVAL = true           # 3-stage retrieval pipeline
ENABLE_QUERY_AUGMENTATION = false     # LLM-enhanced queries
ENABLE_KNOWLEDGE_PREFLIGHT = true     # Cognitive FOK pattern
ENABLE_KNOWLEDGE_EXTRACTION = true    # Auto-extract knowledge
ENABLE_WEB_SEARCH = true              # Tavily web search
ENABLE_SEMANTIC_CACHE = false         # Vector similarity cache
ENABLE_REDIS_CACHE = false            # Redis query cache
```

---

## 2. Secrets and Configuration Management

### 2.1 Design Principles

1. **Never commit secrets**: All sensitive values externalized
2. **Fail-safe defaults**: System works with minimal config
3. **Single source of truth**: One config loading mechanism
4. **Validation on startup**: Catch misconfigurations early
5. **Hierarchical overrides**: env > .env file > defaults

### 2.2 Configuration Categories

| Category | Examples | Storage |
|----------|----------|---------|
| **Secrets** | API keys, DB passwords, encryption keys | Environment only |
| **Infrastructure** | Ports, hosts, connection pools | Environment + defaults |
| **Feature Flags** | Enable/disable features | Environment + defaults |
| **Runtime** | Log levels, timeouts | Environment + defaults |

### 2.3 New Configuration System

Create a centralized configuration module:

```
src/
  config/
    __init__.py
    settings.py       # Pydantic Settings classes
    validators.py     # Custom validation logic
    defaults.py       # Default values
```

**Implementation (`src/config/settings.py`):**

```python
"""Centralized ACMS Configuration using Pydantic Settings.

Loads configuration from:
1. Environment variables (highest priority)
2. .env file (if present)
3. Default values (lowest priority)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, SecretStr
from typing import Optional, List
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ACMS_DB_",
        case_sensitive=False
    )

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    name: str = Field(default="acms", description="Database name")
    user: str = Field(default="acms", description="Database user")
    password: SecretStr = Field(default="", description="Database password")
    pool_min: int = Field(default=5, ge=1, description="Min pool connections")
    pool_max: int = Field(default=20, ge=1, description="Max pool connections")

    @property
    def url(self) -> str:
        """Generate database URL (password hidden in logs)."""
        pwd = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.user}:{pwd}@{self.host}:{self.port}/{self.name}"


class WeaviateSettings(BaseSettings):
    """Weaviate vector database configuration."""

    model_config = SettingsConfigDict(env_prefix="WEAVIATE_")

    host: str = Field(default="localhost")
    http_port: int = Field(default=8080)
    grpc_port: int = Field(default=50051)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.http_port}"


class RedisSettings(BaseSettings):
    """Redis cache configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    password: Optional[SecretStr] = None
    db: int = Field(default=0)
    max_connections: int = Field(default=10)


class OllamaSettings(BaseSettings):
    """Ollama local LLM configuration."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_")

    host: str = Field(default="localhost")
    port: int = Field(default=11434)
    model: str = Field(default="llama3.2:latest")
    enabled: bool = Field(default=True)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class LLMProviderSettings(BaseSettings):
    """External LLM API configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    # API Keys (all optional - system works with just Ollama)
    openai_api_key: Optional[SecretStr] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[SecretStr] = Field(default=None, alias="ANTHROPIC_API_KEY")
    google_api_key: Optional[SecretStr] = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_api_key: Optional[SecretStr] = Field(default=None, alias="GEMINI_API_KEY")
    tavily_api_key: Optional[SecretStr] = Field(default=None, alias="TAVILY_API_KEY")

    # Default provider (ollama works without API keys)
    default_provider: str = Field(default="ollama", alias="LLM_PROVIDER")


class SecuritySettings(BaseSettings):
    """Security and encryption configuration."""

    model_config = SettingsConfigDict(env_prefix="ACMS_")

    # JWT for authentication
    jwt_secret: Optional[SecretStr] = Field(default=None, alias="ACMS_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_hours: int = Field(default=1)
    refresh_token_ttl_days: int = Field(default=7)

    # Encryption key for sensitive data
    encryption_key: Optional[SecretStr] = Field(default=None, alias="ACMS_ENCRYPTION_KEY")
    auto_generate_keys: bool = Field(default=True, description="Auto-generate missing keys")

    # Token secret for integrations
    token_secret: Optional[SecretStr] = Field(default=None, alias="ACMS_TOKEN_SECRET")


class FeatureFlags(BaseSettings):
    """Feature flag configuration."""

    model_config = SettingsConfigDict(env_prefix="ENABLE_")

    # Core features
    new_retrieval: bool = Field(default=True, alias="ENABLE_NEW_RETRIEVAL")
    knowledge_extraction: bool = Field(default=True, alias="ENABLE_KNOWLEDGE_EXTRACTION")
    knowledge_preflight: bool = Field(default=True, alias="ENABLE_KNOWLEDGE_PREFLIGHT")

    # Optional features (disabled by default for minimal setup)
    query_augmentation: bool = Field(default=False, alias="ENABLE_QUERY_AUGMENTATION")
    web_search: bool = Field(default=False, alias="ENABLE_WEB_SEARCH")
    semantic_cache: bool = Field(default=False, alias="ENABLE_SEMANTIC_CACHE")
    redis_cache: bool = Field(default=False, alias="ENABLE_REDIS_CACHE")

    # Integrations
    gmail_integration: bool = Field(default=False, alias="ENABLE_GMAIL")
    plaid_integration: bool = Field(default=False, alias="ENABLE_PLAID")


class ServerSettings(BaseSettings):
    """API server configuration."""

    model_config = SettingsConfigDict(env_prefix="ACMS_")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080, alias="ACMS_API_PORT")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    jobs_enabled: bool = Field(default=True, alias="ACMS_JOBS_ENABLED")


class Settings(BaseSettings):
    """Root settings aggregating all configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Sub-configurations
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    weaviate: WeaviateSettings = Field(default_factory=WeaviateSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    llm: LLMProviderSettings = Field(default_factory=LLMProviderSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    server: ServerSettings = Field(default_factory=ServerSettings)

    def validate_for_production(self) -> List[str]:
        """Validate settings for production deployment."""
        errors = []

        if self.server.environment == "production":
            if not self.security.jwt_secret:
                errors.append("ACMS_JWT_SECRET required for production")
            if self.security.auto_generate_keys:
                errors.append("Set ACMS_AUTO_GENERATE_KEYS=false for production")
            if "*" in self.server.cors_origins:
                errors.append("Restrict CORS origins for production")

        return errors


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### 2.4 New .env.example

```bash
# ============================================================================
# ACMS Configuration - Copy to .env and customize
# ============================================================================

# ----------------------------------------------------------------------------
# DEPLOYMENT MODE
# Options: development, production, docker
# ----------------------------------------------------------------------------
ENVIRONMENT=development

# ----------------------------------------------------------------------------
# DATABASE (PostgreSQL)
# ----------------------------------------------------------------------------
ACMS_DB_HOST=localhost
ACMS_DB_PORT=5432
ACMS_DB_NAME=acms
ACMS_DB_USER=acms
ACMS_DB_PASSWORD=your_secure_password_here

# ----------------------------------------------------------------------------
# VECTOR DATABASE (Weaviate)
# ----------------------------------------------------------------------------
WEAVIATE_HOST=localhost
WEAVIATE_HTTP_PORT=8080
WEAVIATE_GRPC_PORT=50051

# ----------------------------------------------------------------------------
# CACHE (Redis) - Optional
# Leave empty to disable Redis caching
# ----------------------------------------------------------------------------
REDIS_HOST=localhost
REDIS_PORT=6379
# REDIS_PASSWORD=

# ----------------------------------------------------------------------------
# LOCAL LLM (Ollama) - Recommended for privacy
# Works without any API keys
# ----------------------------------------------------------------------------
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.2:latest
OLLAMA_ENABLED=true

# ----------------------------------------------------------------------------
# EXTERNAL LLM PROVIDERS - All Optional
# System works with just Ollama (no API keys needed)
# ----------------------------------------------------------------------------
# OPENAI_API_KEY=sk-your-key-here
# ANTHROPIC_API_KEY=sk-ant-your-key-here
# GOOGLE_API_KEY=your-google-key-here
# GEMINI_API_KEY=your-gemini-key-here

# Default LLM provider: ollama | openai | anthropic | gemini
LLM_PROVIDER=ollama

# ----------------------------------------------------------------------------
# SECURITY
# For production: Set these explicitly, don't auto-generate
# ----------------------------------------------------------------------------
# ACMS_JWT_SECRET=your-32-byte-hex-secret
# ACMS_ENCRYPTION_KEY=your-base64-encoded-32-byte-key
# ACMS_TOKEN_SECRET=your-token-secret

# Auto-generate missing keys (set to false in production)
ACMS_AUTO_GENERATE_KEYS=true

# ----------------------------------------------------------------------------
# FEATURE FLAGS
# Enable/disable optional features
# ----------------------------------------------------------------------------
ENABLE_NEW_RETRIEVAL=true
ENABLE_KNOWLEDGE_EXTRACTION=true
ENABLE_KNOWLEDGE_PREFLIGHT=true
ENABLE_QUERY_AUGMENTATION=false
ENABLE_WEB_SEARCH=false
ENABLE_SEMANTIC_CACHE=false
ENABLE_REDIS_CACHE=false

# ----------------------------------------------------------------------------
# INTEGRATIONS - All Optional
# ----------------------------------------------------------------------------
# Gmail Integration
ENABLE_GMAIL=false
# GOOGLE_CLIENT_ID=your-oauth-client-id
# GOOGLE_CLIENT_SECRET=your-oauth-client-secret
# GOOGLE_REDIRECT_URI=http://localhost:8080/api/gmail/callback

# Plaid Financial Integration
ENABLE_PLAID=false
# PLAID_CLIENT_ID=your-plaid-client-id
# PLAID_SECRET=your-plaid-secret
# PLAID_ENV=sandbox

# Web Search (Tavily)
# TAVILY_API_KEY=tvly-your-key-here

# ----------------------------------------------------------------------------
# API SERVER
# ----------------------------------------------------------------------------
ACMS_API_PORT=8080
LOG_LEVEL=INFO
ACMS_JOBS_ENABLED=true
```

---

## 3. Deployment Modes

### 3.1 Supported Deployment Modes

| Mode | Use Case | Infrastructure |
|------|----------|----------------|
| **Local (Native)** | Development, single-user | Local services |
| **Docker Compose** | Self-hosted, single-server | Docker containers |
| **Docker Swarm** | Small team deployment | Docker orchestration |
| **Kubernetes** | Enterprise, multi-tenant | K8s cluster |

### 3.2 Mode Detection

```python
# src/config/deployment.py

from enum import Enum
import os


class DeploymentMode(Enum):
    LOCAL = "local"
    DOCKER = "docker"
    DOCKER_SWARM = "swarm"
    KUBERNETES = "kubernetes"


def detect_deployment_mode() -> DeploymentMode:
    """Auto-detect deployment environment."""

    # Kubernetes detection
    if os.path.exists("/var/run/secrets/kubernetes.io"):
        return DeploymentMode.KUBERNETES

    # Docker Swarm detection
    if os.getenv("DOCKER_SWARM_SERVICE_NAME"):
        return DeploymentMode.DOCKER_SWARM

    # Docker detection
    if os.path.exists("/.dockerenv"):
        return DeploymentMode.DOCKER

    return DeploymentMode.LOCAL
```

### 3.3 Docker Compose Profiles

```yaml
# docker-compose.yml with profiles

version: "3.9"

services:
  # Core services (always included)
  postgres:
    image: postgres:16-alpine
    profiles: ["core", "full"]
    environment:
      POSTGRES_DB: ${ACMS_DB_NAME:-acms}
      POSTGRES_USER: ${ACMS_DB_USER:-acms}
      POSTGRES_PASSWORD: ${ACMS_DB_PASSWORD:?Database password required}
    ports:
      - "${ACMS_DB_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${ACMS_DB_USER:-acms}"]
      interval: 10s
      timeout: 5s
      retries: 5

  weaviate:
    image: semitechnologies/weaviate:1.27.4
    profiles: ["core", "full"]
    ports:
      - "${WEAVIATE_HTTP_PORT:-8080}:8080"
      - "${WEAVIATE_GRPC_PORT:-50051}:50051"
    environment:
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'none'
    volumes:
      - weaviate_data:/var/lib/weaviate

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    profiles: ["core", "full"]
    ports:
      - "${ACMS_API_PORT:-8080}:8080"
    environment:
      # Use consolidated env var names
      ACMS_DB_HOST: postgres
      ACMS_DB_PORT: 5432
      WEAVIATE_HOST: weaviate
      WEAVIATE_HTTP_PORT: 8080
    depends_on:
      postgres:
        condition: service_healthy
      weaviate:
        condition: service_started
    env_file:
      - .env

  # Optional services
  redis:
    image: redis:7-alpine
    profiles: ["full", "cache"]
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data

  ollama:
    image: ollama/ollama:latest
    profiles: ["full", "local-llm"]
    ports:
      - "${OLLAMA_PORT:-11434}:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  postgres_data:
  weaviate_data:
  redis_data:
  ollama_data:
```

### 3.4 Deployment Scripts

```bash
# scripts/deploy.sh

#!/bin/bash
set -e

MODE=${1:-core}
echo "Deploying ACMS in $MODE mode..."

case $MODE in
  "minimal")
    # Just database + API (uses external LLM APIs)
    docker compose --profile core up -d postgres weaviate api
    ;;
  "core")
    # Minimal + Ollama for local LLM
    docker compose --profile core --profile local-llm up -d
    ;;
  "full")
    # Everything including Redis cache
    docker compose --profile full up -d
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo "Options: minimal, core, full"
    exit 1
    ;;
esac

echo "Waiting for services..."
sleep 5

# Run migrations
docker compose exec api alembic upgrade head

echo "ACMS deployed successfully!"
echo "API: http://localhost:${ACMS_API_PORT:-8080}"
```

---

## 4. Configurable Port System

### 4.1 Port Mapping Strategy

Replace hardcoded 40xxx ports with configurable defaults:

| Service | Default Port | Environment Variable |
|---------|--------------|---------------------|
| API | 8080 | `ACMS_API_PORT` |
| PostgreSQL | 5432 | `ACMS_DB_PORT` |
| Weaviate HTTP | 8080 | `WEAVIATE_HTTP_PORT` |
| Weaviate gRPC | 50051 | `WEAVIATE_GRPC_PORT` |
| Redis | 6379 | `REDIS_PORT` |
| Ollama | 11434 | `OLLAMA_PORT` |

### 4.2 Migration from 40xxx Ports

For backward compatibility during transition:

```python
# src/config/port_migration.py

import os
import warnings

LEGACY_PORT_MAP = {
    "40080": ("ACMS_API_PORT", 8080),
    "40432": ("ACMS_DB_PORT", 5432),
    "40480": ("WEAVIATE_HTTP_PORT", 8080),
    "40481": ("WEAVIATE_GRPC_PORT", 50051),
    "40379": ("REDIS_PORT", 6379),
    "40434": ("OLLAMA_PORT", 11434),
}

def migrate_legacy_ports():
    """Detect and warn about legacy 40xxx port usage."""
    legacy_detected = []

    for legacy, (new_var, default) in LEGACY_PORT_MAP.items():
        # Check if legacy port is being used
        current = os.getenv(new_var, str(default))
        if legacy in str(current):
            legacy_detected.append(f"  {new_var}: {legacy} -> {default}")

    if legacy_detected:
        warnings.warn(
            "Legacy 40xxx ports detected. Please update to standard ports:\n" +
            "\n".join(legacy_detected),
            DeprecationWarning
        )
```

---

## 5. Encryption Key Management

### 5.1 Key Types and Purposes

| Key | Purpose | Generation |
|-----|---------|------------|
| `ACMS_JWT_SECRET` | JWT token signing | 32-byte hex |
| `ACMS_ENCRYPTION_KEY` | Data encryption (ChaCha20) | 32-byte base64 |
| `ACMS_TOKEN_SECRET` | Integration tokens | 32-byte hex |

### 5.2 Key Generation Strategy

```python
# src/config/keygen.py

import secrets
import base64
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

KEYS_DIR = Path.home() / ".acms" / "keys"


def generate_jwt_secret() -> str:
    """Generate 256-bit JWT secret."""
    return secrets.token_hex(32)


def generate_encryption_key() -> str:
    """Generate 256-bit encryption key (base64)."""
    key_bytes = secrets.token_bytes(32)
    return base64.b64encode(key_bytes).decode('utf-8')


def ensure_keys_exist(auto_generate: bool = True) -> dict:
    """Ensure all required keys exist.

    In development: Auto-generate missing keys
    In production: Fail if keys missing
    """
    keys = {}
    env = os.getenv("ENVIRONMENT", "development")

    # JWT Secret
    jwt_secret = os.getenv("ACMS_JWT_SECRET")
    if not jwt_secret:
        if env == "production" and not auto_generate:
            raise ValueError("ACMS_JWT_SECRET required in production")
        jwt_secret = generate_jwt_secret()
        logger.warning("Generated ephemeral JWT secret (will invalidate on restart)")
    keys["jwt_secret"] = jwt_secret

    # Encryption Key
    enc_key = os.getenv("ACMS_ENCRYPTION_KEY")
    if not enc_key:
        if env == "production" and not auto_generate:
            raise ValueError("ACMS_ENCRYPTION_KEY required in production")
        enc_key = generate_encryption_key()
        logger.warning("Generated ephemeral encryption key (data will be unrecoverable on restart)")
    keys["encryption_key"] = enc_key

    return keys


def save_generated_keys(keys: dict, keys_file: Path = KEYS_DIR / "keys.env"):
    """Save generated keys to secure file (development only)."""
    keys_file.parent.mkdir(parents=True, exist_ok=True)
    keys_file.chmod(0o600)  # Owner read/write only

    with open(keys_file, 'w') as f:
        f.write("# ACMS Generated Keys - DO NOT COMMIT\n")
        f.write(f"ACMS_JWT_SECRET={keys['jwt_secret']}\n")
        f.write(f"ACMS_ENCRYPTION_KEY={keys['encryption_key']}\n")

    logger.info(f"Keys saved to {keys_file}")


# CLI command for key generation
def main():
    """CLI: Generate keys for ACMS setup."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate ACMS encryption keys")
    parser.add_argument("--save", action="store_true", help="Save to ~/.acms/keys/")
    parser.add_argument("--format", choices=["env", "json"], default="env")
    args = parser.parse_args()

    keys = {
        "ACMS_JWT_SECRET": generate_jwt_secret(),
        "ACMS_ENCRYPTION_KEY": generate_encryption_key(),
        "ACMS_TOKEN_SECRET": secrets.token_hex(32),
    }

    if args.format == "env":
        for name, value in keys.items():
            print(f"{name}={value}")
    else:
        import json
        print(json.dumps(keys, indent=2))

    if args.save:
        save_generated_keys(keys)


if __name__ == "__main__":
    main()
```

### 5.3 User-Provided vs Auto-Generated

| Environment | Behavior |
|-------------|----------|
| **Development** | Auto-generate missing keys with warning |
| **Production** | Require explicit keys, fail if missing |
| **Docker** | Generate at first run, persist in volume |

**First-Run Key Generation (Docker):**

```yaml
# docker-compose.yml
services:
  api:
    volumes:
      - acms_keys:/app/keys
    command: >
      sh -c "
        if [ ! -f /app/keys/.initialized ]; then
          python -m src.config.keygen --save
          touch /app/keys/.initialized
        fi
        uvicorn src.api_server:app --host 0.0.0.0 --port 8080
      "
```

---

## 6. Feature Detection System

### 6.1 Feature Categories

| Category | Detection Method | Examples |
|----------|------------------|----------|
| **Required** | Must be available | PostgreSQL, Weaviate |
| **Optional** | Graceful degradation | Redis, Ollama |
| **Integration** | External service | Gmail, Plaid |
| **Experimental** | Explicitly enabled | Query augmentation |

### 6.2 Feature Registry

```python
# src/config/features.py

from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FeatureCategory(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    INTEGRATION = "integration"
    EXPERIMENTAL = "experimental"


@dataclass
class Feature:
    """Feature definition with health check."""
    name: str
    category: FeatureCategory
    description: str
    enabled: bool = False
    healthy: bool = False
    health_check: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    config_key: Optional[str] = None

    async def check_health(self) -> bool:
        """Run health check for this feature."""
        if self.health_check:
            try:
                self.healthy = await self.health_check()
            except Exception as e:
                logger.warning(f"Feature {self.name} health check failed: {e}")
                self.healthy = False
        else:
            self.healthy = self.enabled
        return self.healthy


class FeatureRegistry:
    """Registry of all ACMS features with health tracking."""

    def __init__(self):
        self.features: Dict[str, Feature] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register all known features."""
        # Required features
        self.register(Feature(
            name="database",
            category=FeatureCategory.REQUIRED,
            description="PostgreSQL database for metadata storage",
            health_check=self._check_postgres
        ))

        self.register(Feature(
            name="vector_db",
            category=FeatureCategory.REQUIRED,
            description="Weaviate vector database for semantic search",
            health_check=self._check_weaviate
        ))

        # Optional features
        self.register(Feature(
            name="redis_cache",
            category=FeatureCategory.OPTIONAL,
            description="Redis cache for query results",
            config_key="ENABLE_REDIS_CACHE",
            health_check=self._check_redis
        ))

        self.register(Feature(
            name="ollama",
            category=FeatureCategory.OPTIONAL,
            description="Local LLM via Ollama",
            config_key="OLLAMA_ENABLED",
            health_check=self._check_ollama
        ))

        # Integrations
        self.register(Feature(
            name="gmail",
            category=FeatureCategory.INTEGRATION,
            description="Gmail integration for email context",
            config_key="ENABLE_GMAIL",
            dependencies=["database"]
        ))

        self.register(Feature(
            name="plaid",
            category=FeatureCategory.INTEGRATION,
            description="Plaid integration for financial context",
            config_key="ENABLE_PLAID",
            dependencies=["database"]
        ))

        # Experimental
        self.register(Feature(
            name="query_augmentation",
            category=FeatureCategory.EXPERIMENTAL,
            description="LLM-enhanced query expansion",
            config_key="ENABLE_QUERY_AUGMENTATION"
        ))

    def register(self, feature: Feature):
        """Register a feature."""
        self.features[feature.name] = feature

    def is_enabled(self, name: str) -> bool:
        """Check if feature is enabled."""
        feature = self.features.get(name)
        return feature.enabled if feature else False

    def is_healthy(self, name: str) -> bool:
        """Check if feature is enabled and healthy."""
        feature = self.features.get(name)
        return feature.enabled and feature.healthy if feature else False

    async def initialize(self):
        """Load feature flags from config and run health checks."""
        from src.config.settings import get_settings
        settings = get_settings()

        for feature in self.features.values():
            # Load enabled state from config
            if feature.config_key:
                feature.enabled = getattr(
                    settings.features,
                    feature.config_key.lower().replace("enable_", ""),
                    False
                )
            elif feature.category == FeatureCategory.REQUIRED:
                feature.enabled = True

            # Run health check
            if feature.enabled:
                await feature.check_health()

        # Log feature status
        self._log_status()

    def _log_status(self):
        """Log feature status summary."""
        enabled = [f.name for f in self.features.values() if f.enabled and f.healthy]
        disabled = [f.name for f in self.features.values() if not f.enabled]
        unhealthy = [f.name for f in self.features.values() if f.enabled and not f.healthy]

        logger.info(f"Features enabled: {', '.join(enabled) or 'none'}")
        if unhealthy:
            logger.warning(f"Features unhealthy: {', '.join(unhealthy)}")
        logger.debug(f"Features disabled: {', '.join(disabled)}")

    def get_status(self) -> Dict:
        """Get feature status as dict."""
        return {
            name: {
                "enabled": f.enabled,
                "healthy": f.healthy,
                "category": f.category.value,
                "description": f.description
            }
            for name, f in self.features.items()
        }

    # Health check implementations
    async def _check_postgres(self) -> bool:
        from src.storage.database import get_db_pool
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def _check_weaviate(self) -> bool:
        from src.storage.weaviate_client import get_weaviate_client
        try:
            client = get_weaviate_client()
            return client.is_ready()
        except Exception:
            return False

    async def _check_redis(self) -> bool:
        from src.cache.memory_cache import get_redis_client
        try:
            client = await get_redis_client()
            await client.ping()
            return True
        except Exception:
            return False

    async def _check_ollama(self) -> bool:
        from src.llm.ollama_client import OllamaClient
        try:
            client = OllamaClient()
            models = await client.list_models()
            return len(models) > 0
        except Exception:
            return False


# Singleton instance
_registry: Optional[FeatureRegistry] = None

def get_feature_registry() -> FeatureRegistry:
    global _registry
    if _registry is None:
        _registry = FeatureRegistry()
    return _registry
```

### 6.3 Feature Decorators

```python
# src/config/decorators.py

from functools import wraps
from fastapi import HTTPException
from src.config.features import get_feature_registry


def requires_feature(feature_name: str):
    """Decorator to require a feature for an endpoint."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            registry = get_feature_registry()
            if not registry.is_healthy(feature_name):
                raise HTTPException(
                    status_code=503,
                    detail=f"Feature '{feature_name}' is not available"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Usage example:
@app.get("/api/gmail/messages")
@requires_feature("gmail")
async def get_gmail_messages():
    ...
```

---

## 7. Repository Structure

### 7.1 Proposed Directory Layout

```
acms/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # Main CI pipeline
│   │   ├── release.yml         # Release automation
│   │   └── security.yml        # Security scanning
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
│
├── docs/
│   ├── getting-started/
│   │   ├── quickstart.md
│   │   ├── installation.md
│   │   └── configuration.md
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── data-flow.md
│   │   └── privacy-model.md
│   ├── api/
│   │   └── openapi.yaml
│   ├── deployment/
│   │   ├── docker.md
│   │   ├── kubernetes.md
│   │   └── cloud.md
│   └── contributing/
│       ├── CONTRIBUTING.md
│       ├── code-style.md
│       └── testing.md
│
├── src/
│   ├── api/                    # API endpoints
│   ├── auth/                   # Authentication
│   ├── cache/                  # Caching layer
│   ├── config/                 # Configuration (NEW)
│   ├── core/                   # Core logic
│   ├── embeddings/             # Vector embeddings
│   ├── gateway/                # AI gateway
│   │   └── agents/             # Agent implementations
│   ├── intelligence/           # Knowledge extraction
│   ├── integrations/           # External integrations
│   │   ├── gmail/
│   │   └── plaid/
│   ├── llm/                    # LLM clients
│   ├── memory/                 # Memory system
│   ├── privacy/                # Privacy controls
│   ├── retrieval/              # RAG pipeline
│   ├── storage/                # Database layer
│   └── utils/                  # Utilities
│
├── desktop-app/                # Electron frontend
│   ├── src/
│   ├── tests/
│   └── package.json
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│
├── migrations/                 # SQL migrations
├── scripts/                    # Utility scripts
│   ├── setup.sh
│   ├── deploy.sh
│   └── keygen.py
│
├── examples/
│   ├── basic-usage/
│   ├── custom-agent/
│   └── integration-demo/
│
├── .env.example
├── docker-compose.yml
├── docker-compose.dev.yml
├── Dockerfile.api
├── Makefile
├── pyproject.toml              # Replace requirements.txt
├── README.md
├── LICENSE
├── CHANGELOG.md
└── SECURITY.md
```

### 7.2 Key New Files

**pyproject.toml** (replace requirements.txt):

```toml
[project]
name = "acms"
version = "1.0.0"
description = "Adaptive Context Memory System - Privacy-first AI memory"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
authors = [
    {name = "ACMS Contributors"}
]

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.28.0",
    "weaviate-client>=4.0.0",
    "redis>=5.0.0",
    "anthropic>=0.25.0",
    "openai>=1.0.0",
    "httpx>=0.25.0",
    "cryptography>=41.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "black>=24.0.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]
gmail = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.0.0",
]
plaid = [
    "plaid-python>=23.0.0",
]

[project.scripts]
acms = "src.cli:main"
acms-keygen = "src.config.keygen:main"

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = "test_*.py"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "N", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
```

**Makefile**:

```makefile
.PHONY: help install dev test lint format docker-build docker-up docker-down migrate

help:
	@echo "ACMS Development Commands"
	@echo "========================="
	@echo "install     - Install production dependencies"
	@echo "dev         - Install development dependencies"
	@echo "test        - Run all tests"
	@echo "lint        - Run linting (ruff + mypy)"
	@echo "format      - Format code (black + ruff)"
	@echo "docker-up   - Start Docker services"
	@echo "docker-down - Stop Docker services"
	@echo "migrate     - Run database migrations"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	PYTHONPATH=. pytest tests/ -v --cov=src --cov-report=html

lint:
	ruff check src/
	mypy src/

format:
	black src/ tests/
	ruff check --fix src/

docker-up:
	docker compose --profile core up -d

docker-down:
	docker compose down

migrate:
	alembic upgrade head

keygen:
	python -m src.config.keygen

run:
	uvicorn src.api_server:app --reload --port 8080
```

### 7.3 CODEOWNERS

```
# .github/CODEOWNERS

# Default owners
*                       @acms/maintainers

# Core modules
/src/gateway/           @acms/gateway-team
/src/storage/           @acms/storage-team
/src/intelligence/      @acms/ml-team

# Security-sensitive areas
/src/auth/              @acms/security
/src/privacy/           @acms/security
/src/config/            @acms/security
/.github/workflows/     @acms/security

# Desktop app
/desktop-app/           @acms/frontend

# Documentation
/docs/                  @acms/docs
```

---

## 8. CI/CD Pipeline

### 8.1 GitHub Actions Workflow

**`.github/workflows/ci.yml`**:

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "20"

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install ruff black mypy
          pip install -e ".[dev]"

      - name: Run ruff
        run: ruff check src/

      - name: Run black (check)
        run: black --check src/ tests/

      - name: Run mypy
        run: mypy src/ --ignore-missing-imports

  test-unit:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run unit tests
        run: |
          PYTHONPATH=. pytest tests/unit/ -v \
            --cov=src \
            --cov-report=xml \
            --cov-report=html

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml

  test-integration:
    runs-on: ubuntu-latest
    needs: test-unit
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: acms_test
          POSTGRES_USER: acms
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      weaviate:
        image: semitechnologies/weaviate:1.27.4
        ports:
          - 8080:8080
        env:
          AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run migrations
        env:
          ACMS_DB_HOST: localhost
          ACMS_DB_PORT: 5432
          ACMS_DB_NAME: acms_test
          ACMS_DB_USER: acms
          ACMS_DB_PASSWORD: test_password
        run: alembic upgrade head

      - name: Run integration tests
        env:
          ACMS_DB_HOST: localhost
          WEAVIATE_HOST: localhost
          ENVIRONMENT: test
        run: PYTHONPATH=. pytest tests/integration/ -v

  test-desktop:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Install dependencies
        working-directory: desktop-app
        run: npm ci

      - name: Run tests
        working-directory: desktop-app
        run: npm test

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  build-docker:
    runs-on: ubuntu-latest
    needs: [test-unit, test-integration]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.api
          push: false
          tags: acms:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # Only on main branch pushes
  release:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    needs: [build-docker, security-scan]
    steps:
      - uses: actions/checkout@v4

      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: v${{ github.run_number }}
          release_name: Release ${{ github.run_number }}
          draft: true
```

### 8.2 Security Workflow

**`.github/workflows/security.yml`**:

```yaml
name: Security

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  dependency-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install pip-audit
        run: pip install pip-audit

      - name: Run pip-audit
        run: pip-audit

  codeql:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: python, javascript

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3

  secrets-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Detect secrets with Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 9. Migration Path

### 9.1 Migration Steps

For existing users upgrading from private to open-source version:

1. **Configuration Migration**
   ```bash
   # Run migration script
   python scripts/migrate_config.py

   # This will:
   # - Create new .env from existing config
   # - Map 40xxx ports to standard ports
   # - Generate missing encryption keys
   ```

2. **Database Migration**
   ```bash
   # Backup existing data
   docker exec acms_postgres pg_dump -U acms acms > backup.sql

   # Run migrations
   alembic upgrade head
   ```

3. **Docker Compose Update**
   ```bash
   # Stop existing services
   docker compose down

   # Update compose file
   cp docker-compose.yml docker-compose.legacy.yml
   curl -O https://raw.githubusercontent.com/acms/acms/main/docker-compose.yml

   # Update .env
   cp .env .env.backup
   # Edit .env to use new variable names

   # Start services
   docker compose up -d
   ```

### 9.2 Backward Compatibility

Maintain compatibility for 2 major versions:

```python
# src/config/compat.py

import os
import warnings

# Legacy environment variable mappings
LEGACY_ENV_MAP = {
    "POSTGRES_HOST": "ACMS_DB_HOST",
    "POSTGRES_PORT": "ACMS_DB_PORT",
    "POSTGRES_DB": "ACMS_DB_NAME",
    "POSTGRES_USER": "ACMS_DB_USER",
    "POSTGRES_PASSWORD": "ACMS_DB_PASSWORD",
}

def migrate_legacy_env():
    """Check for and migrate legacy environment variables."""
    migrated = []

    for old_name, new_name in LEGACY_ENV_MAP.items():
        old_value = os.getenv(old_name)
        new_value = os.getenv(new_name)

        if old_value and not new_value:
            os.environ[new_name] = old_value
            migrated.append(f"{old_name} -> {new_name}")

    if migrated:
        warnings.warn(
            f"Legacy environment variables detected and migrated:\n" +
            "\n".join(f"  {m}" for m in migrated) +
            "\n\nPlease update your .env file to use the new variable names.",
            DeprecationWarning
        )
```

---

## 10. Security Considerations

### 10.1 Security Checklist for Open Source

- [x] **No hardcoded secrets**: All secrets via environment
- [x] **Secure defaults**: Fail closed, require explicit opt-in
- [x] **Input validation**: Pydantic models for all inputs
- [x] **Rate limiting**: Built-in rate limiter
- [x] **PII protection**: Preflight gate blocks sensitive data
- [x] **Encryption at rest**: ChaCha20-Poly1305 for sensitive data
- [x] **Audit logging**: Full data flow tracking
- [ ] **RBAC**: Role-based access control (partially implemented)
- [ ] **Multi-tenancy**: Tenant isolation (not yet implemented)

### 10.2 Security Documentation

Create `SECURITY.md`:

```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities to security@acms.dev

Do NOT report security issues via public GitHub issues.

We will respond within 48 hours and provide a timeline for fixes.

## Security Features

- **Encryption**: ChaCha20-Poly1305 AEAD for sensitive data
- **Authentication**: JWT with configurable TTL
- **PII Protection**: Automatic detection and blocking
- **Rate Limiting**: Per-user request limits
- **Audit Trail**: Complete data flow logging

## Best Practices

1. Never commit `.env` files
2. Use strong, unique encryption keys in production
3. Disable `ACMS_AUTO_GENERATE_KEYS` in production
4. Configure CORS origins explicitly
5. Enable HTTPS in production deployments
```

### 10.3 Pre-Release Security Audit

Before public release, perform:

1. **Dependency audit**: `pip-audit`, `npm audit`
2. **Secret scanning**: `gitleaks`, `trufflehog`
3. **Static analysis**: CodeQL, Bandit
4. **Container scanning**: Trivy, Snyk
5. **Manual review**: Focus on auth, encryption, input handling

---

## Summary

This architecture document provides a comprehensive plan for open-sourcing ACMS with:

1. **Centralized configuration** via Pydantic Settings with validation
2. **Multiple deployment modes** from local development to Kubernetes
3. **Configurable ports** with backward compatibility migration
4. **Secure key management** with auto-generation for development
5. **Feature detection system** with health checks and graceful degradation
6. **Contributor-friendly repository** structure with clear ownership
7. **Robust CI/CD** with testing, security scanning, and automated releases

The design prioritizes security-by-default, ease of deployment, and extensibility for the open-source community.
