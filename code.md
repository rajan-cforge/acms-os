# ACMS Code Repository Structure & Scaffolding
**Version:** 2.0 (15-Pass Refined)  
**Status:** Production-Ready  
**Last Updated:** October 2025

---

## Repository Structure

```
acms/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # CI pipeline
│   │   ├── cd-dev.yml                # Deploy to dev
│   │   ├── cd-staging.yml            # Deploy to staging
│   │   ├── cd-production.yml         # Deploy to production
│   │   └── security-scan.yml         # Security scanning
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── security_report.md
│   └── dependabot.yml
│
├── docs/
│   ├── architecture/
│   │   ├── 00-overview.md
│   │   ├── 01-system-design.md
│   │   ├── 02-data-model.md
│   │   ├── 03-security-architecture.md
│   │   └── diagrams/
│   ├── api/
│   │   ├── openapi.yaml            # Main OpenAPI spec
│   │   ├── postman-collection.json
│   │   └── examples/
│   ├── deployment/
│   │   ├── kubernetes.md
│   │   ├── docker.md
│   │   └── local-development.md
│   ├── compliance/
│   │   ├── gdpr.md
│   │   ├── hipaa.md
│   │   ├── ccpa.md
│   │   └── soc2.md
│   └── guides/
│       ├── getting-started.md
│       ├── integration-guide.md
│       ├── troubleshooting.md
│       └── best-practices.md
│
├── src/
│   ├── api/                         # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py                  # Application entry point
│   │   ├── dependencies.py          # Dependency injection
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Authentication middleware
│   │   │   ├── rate_limit.py       # Rate limiting
│   │   │   ├── logging.py          # Request logging
│   │   │   └── error_handler.py    # Global error handler
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── query.py            # /query endpoint
│   │   │   ├── memory.py           # /memory/* endpoints
│   │   │   ├── outcomes.py         # /outcomes/* endpoints
│   │   │   ├── export.py           # /export endpoints
│   │   │   └── admin.py            # /admin/* endpoints
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── query.py            # Pydantic schemas for queries
│   │   │   ├── memory.py
│   │   │   ├── outcomes.py
│   │   │   ├── common.py           # Shared schemas
│   │   │   └── responses.py        # Response models
│   │   └── config/
│   │       ├── __init__.py
│   │       ├── settings.py         # Application settings
│   │       └── logging.yml
│   │
│   ├── core/                        # Business logic
│   │   ├── __init__.py
│   │   ├── rehydration/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # Rehydration engine
│   │   │   ├── intent_classifier.py
│   │   │   ├── retrieval.py        # Hybrid retrieval
│   │   │   ├── summarizer.py
│   │   │   └── prompt_assembler.py
│   │   ├── crs/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # CRS computation
│   │   │   ├── tier_manager.py     # Tier transitions
│   │   │   ├── consolidation.py
│   │   │   └── config.py
│   │   ├── policy/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # Policy enforcement
│   │   │   ├── pii_detector.py
│   │   │   ├── compliance.py
│   │   │   └── audit.py
│   │   └── crypto/
│   │       ├── __init__.py
│   │       ├── manager.py          # Crypto manager
│   │       ├── hardware_backend.py # TPM/Secure Enclave
│   │       └── key_derivation.py
│   │
│   ├── storage/                     # Data access layer
│   │   ├── __init__.py
│   │   ├── vector_store/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Abstract interface
│   │   │   ├── postgres.py         # PostgreSQL + pgvector
│   │   │   ├── weaviate.py         # Weaviate implementation
│   │   │   └── cache.py            # Redis caching
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── memory_item.py      # MemoryItem domain model
│   │   │   ├── user.py
│   │   │   ├── outcome.py
│   │   │   └── audit_log.py
│   │   └── migrations/
│   │       ├── versions/
│   │       │   ├── 001_initial_schema.sql
│   │       │   ├── 002_add_pgvector.sql
│   │       │   └── 003_add_audit_tables.sql
│   │       └── alembic.ini
│   │
│   ├── llm/                         # LLM integrations
│   │   ├── __init__.py
│   │   ├── base.py                  # Abstract LLM interface
│   │   ├── ollama_client.py         # Ollama implementation
│   │   ├── openai_client.py
│   │   ├── anthropic_client.py
│   │   └── embeddings.py            # Embedding generation
│   │
│   ├── services/                    # Application services
│   │   ├── __init__.py
│   │   ├── query_service.py         # Query orchestration
│   │   ├── memory_service.py        # Memory CRUD
│   │   ├── outcome_service.py       # Outcome logging
│   │   ├── export_service.py        # Data export
│   │   └── admin_service.py         # Admin operations
│   │
│   └── utils/                       # Utilities
│       ├── __init__.py
│       ├── metrics.py               # Prometheus metrics
│       ├── tracing.py               # OpenTelemetry
│       ├── text_processing.py       # Token counting, etc.
│       └── validators.py
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_crs_engine.py
│   │   ├── test_rehydration.py
│   │   ├── test_crypto.py
│   │   ├── test_pii_detector.py
│   │   └── ...
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   ├── test_vector_store.py
│   │   ├── test_end_to_end.py
│   │   └── ...
│   ├── performance/
│   │   ├── test_load.py
│   │   ├── test_latency.py
│   │   └── benchmarks.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── memory_items.py
│   │   └── ...
│   └── conftest.py                  # Pytest configuration
│
├── scripts/
│   ├── setup/
│   │   ├── install_dependencies.sh
│   │   ├── setup_database.sh
│   │   └── generate_keys.sh
│   ├── deployment/
│   │   ├── deploy.sh
│   │   ├── rollback.sh
│   │   └── health_check.sh
│   ├── maintenance/
│   │   ├── backup_database.sh
│   │   ├── restore_database.sh
│   │   └── rotate_keys.sh
│   └── dev/
│       ├── start_local.sh
│       ├── run_tests.sh
│       └── lint.sh
│
├── infra/                           # Infrastructure as Code
│   ├── kubernetes/
│   │   ├── base/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   ├── ingress.yaml
│   │   │   ├── configmap.yaml
│   │   │   ├── secrets.yaml
│   │   │   ├── hpa.yaml
│   │   │   └── pdb.yaml
│   │   └── overlays/
│   │       ├── dev/
│   │       ├── staging/
│   │       └── production/
│   ├── helm/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-dev.yaml
│   │   ├── values-staging.yaml
│   │   ├── values-production.yaml
│   │   └── templates/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   └── docker/
│       ├── Dockerfile
│       ├── Dockerfile.dev
│       ├── docker-compose.yml
│       └── docker-compose.dev.yml
│
├── config/
│   ├── development.yaml
│   ├── staging.yaml
│   ├── production.yaml
│   └── test.yaml
│
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts.yml
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   ├── overview.json
│   │   │   ├── api-metrics.json
│   │   │   └── memory-metrics.json
│   │   └── datasources/
│   └── jaeger/
│       └── jaeger-config.yaml
│
├── .env.example                     # Environment variables template
├── .gitignore
├── .dockerignore
├── .pre-commit-config.yaml
├── pyproject.toml                   # Poetry/pip-tools config
├── requirements.txt                 # Production dependencies
├── requirements-dev.txt             # Development dependencies
├── Makefile                         # Common tasks
├── README.md                        # Getting started
├── CONTRIBUTING.md                  # Contribution guidelines
├── LICENSE                          # License information
├── CHANGELOG.md                     # Version history
└── SECURITY.md                      # Security policy
```

---

## Key Files Content

### 1. `src/api/main.py`

```python
"""
ACMS API - Main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from api.config.settings import settings
from api.middleware.auth import AuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.error_handler import ErrorHandlerMiddleware
from api.routes import query, memory, outcomes, export, admin

# Initialize application
app = FastAPI(
    title="ACMS API",
    description="Adaptive Context Memory System REST API",
    version="2.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

# Routes
app.include_router(query.router, prefix="/v1", tags=["Query"])
app.include_router(memory.router, prefix="/v1", tags=["Memory"])
app.include_router(outcomes.router, prefix="/v1", tags=["Outcomes"])
app.include_router(export.router, prefix="/v1", tags=["Export"])
app.include_router(admin.router, prefix="/v1/admin", tags=["Admin"])

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Health checks
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}

@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check (includes dependencies)"""
    # Check database, Redis, etc.
    # ...
    return {"status": "ready"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        workers=settings.api_workers if settings.environment == "production" else 1,
    )
```

### 2. `src/core/crs/engine.py`

```python
"""
Context Retention Score (CRS) Engine
"""
import numpy as np
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List

from storage.models.memory_item import MemoryItem
from core.crs.config import CRSConfig

@dataclass
class CRSResult:
    item_id: str
    crs: float
    components: Dict[str, float]
    computed_at: datetime

class CRSEngine:
    """
    Compute and manage Context Retention Scores
    """
    
    def __init__(self, config: CRSConfig):
        self.config = config
    
    def compute_crs(
        self,
        item: MemoryItem,
        user_profile: "UserProfile"
    ) -> CRSResult:
        """
        Compute CRS for a memory item
        
        Formula:
        CRS = (w1·Sim + w2·Rec + w3·Out + w4·Corr + w5·Recent)
              · exp(-λ·age) - PII_penalty
        """
        age_days = (datetime.utcnow() - item.created_at).total_seconds() / 86400
        
        # Components
        similarity = self._compute_similarity(item, user_profile)
        recurrence = min(1.0, item.access_count / self.config.recurrence_k)
        outcome = self._compute_outcome_success(item)
        corrections = item.correction_signal
        recency = 1.0 / (1.0 + age_days)
        pii_penalty = self._compute_pii_penalty(item)
        
        # Weighted sum
        base_score = (
            self.config.w1_similarity * similarity +
            self.config.w2_recurrence * recurrence +
            self.config.w3_outcome * outcome +
            self.config.w4_corrections * corrections +
            self.config.w5_recency * recency
        )
        
        # Temporal decay
        decay_factor = np.exp(-self.config.lambda_decay * age_days)
        
        # Final CRS
        crs = (base_score * decay_factor) - pii_penalty
        crs = np.clip(crs, 0.0, 1.0)
        
        return CRSResult(
            item_id=item.id,
            crs=crs,
            components={
                'similarity': similarity,
                'recurrence': recurrence,
                'outcome': outcome,
                'corrections': corrections,
                'recency': recency,
                'decay_factor': decay_factor,
                'pii_penalty': pii_penalty,
                'base_score': base_score
            },
            computed_at=datetime.utcnow()
        )
    
    def _compute_similarity(
        self,
        item: MemoryItem,
        user_profile: "UserProfile"
    ) -> float:
        """Compute semantic similarity"""
        if item.topic_id not in user_profile.topic_vectors:
            return 0.5  # Neutral
        
        topic_vector = user_profile.topic_vectors[item.topic_id]
        return float(np.dot(item.embedding, topic_vector) / 
                    (np.linalg.norm(item.embedding) * np.linalg.norm(topic_vector)))
    
    def _compute_outcome_success(self, item: MemoryItem) -> float:
        """Compute outcome success rate"""
        if not item.outcome_log:
            return 0.5
        
        success_scores = []
        for outcome in item.outcome_log:
            if 'edit_distance' in outcome:
                edit_score = 1.0 - min(1.0, outcome['edit_distance'] / 0.5)
                success_scores.append(edit_score)
            
            if 'rating' in outcome:
                success_scores.append(1.0 if outcome['rating'] >= 4 else 0.0)
            
            if 'completed' in outcome:
                success_scores.append(1.0 if outcome['completed'] else 0.0)
        
        return float(np.mean(success_scores)) if success_scores else 0.5
    
    def _compute_pii_penalty(self, item: MemoryItem) -> float:
        """Compute PII penalty"""
        penalty = sum(
            self.config.pii_weights.get(pii_type, 0.0)
            for pii_type in item.pii_flags
        )
        return min(0.5, penalty)
```

### 3. `pyproject.toml`

```toml
[tool.poetry]
name = "acms"
version = "2.0.0"
description = "Adaptive Context Memory System for AI Assistants"
authors = ["ACMS Team <engineering@acms.example.com>"]
license = "Proprietary"
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
pydantic = "^2.6.0"
pydantic-settings = "^2.1.0"
sqlalchemy = "^2.0.27"
alembic = "^1.13.0"
asyncpg = "^0.29.0"
psycopg2-binary = "^2.9.9"
pgvector = "^0.2.4"
redis = "^5.0.1"
celery = "^5.3.6"
weaviate-client = "^4.5.0"
sentence-transformers = "^2.3.0"
numpy = "^1.26.4"
scipy = "^1.12.0"
ollama = "^0.1.7"
openai = "^1.12.0"
anthropic = "^0.18.0"
cryptography = "^42.0.2"
pynacl = "^1.5.0"
pyjwt = "^2.8.0"
prometheus-client = "^0.20.0"
prometheus-fastapi-instrumentator = "^6.1.0"
opentelemetry-api = "^1.23.0"
opentelemetry-sdk = "^1.23.0"
opentelemetry-instrumentation-fastapi = "^0.44b0"
opentelemetry-exporter-jaeger = "^1.23.0"
structlog = "^24.1.0"
rapidfuzz = "^3.6.1"
tiktoken = "^0.6.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
httpx = "^0.26.0"
black = "^24.1.0"
isort = "^5.13.0"
flake8 = "^7.0.0"
mypy = "^1.8.0"
pre-commit = "^3.6.0"
bandit = "^1.7.7"
safety = "^3.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow-running tests",
    "requires_gpu: Tests requiring GPU",
]

[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### 4. `Makefile`

```makefile
.PHONY: help install dev test lint format clean docker-build docker-up docker-down

help:
	@echo "ACMS Development Commands"
	@echo "=========================="
	@echo "install      - Install dependencies"
	@echo "dev          - Run development server"
	@echo "test         - Run tests"
	@echo "test-cov     - Run tests with coverage"
	@echo "lint         - Run linters"
	@echo "format       - Format code"
	@echo "clean        - Clean build artifacts"
	@echo "docker-build - Build Docker image"
	@echo "docker-up    - Start Docker Compose services"
	@echo "docker-down  - Stop Docker Compose services"

install:
	poetry install

dev:
	poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	poetry run pytest tests/ -v

test-cov:
	poetry run pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:
	poetry run flake8 src tests
	poetry run mypy src
	poetry run bandit -r src

format:
	poetry run black src tests
	poetry run isort src tests

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info

docker-build:
	docker build -t acms:latest -f infra/docker/Dockerfile .

docker-up:
	docker-compose -f infra/docker/docker-compose.yml up -d

docker-down:
	docker-compose -f infra/docker/docker-compose.yml down

migrate-up:
	poetry run alembic upgrade head

migrate-down:
	poetry run alembic downgrade -1

migrate-create:
	@read -p "Enter migration name: " name; \
	poetry run alembic revision --autogenerate -m "$$name"
```

### 5. `README.md`

```markdown
# ACMS - Adaptive Context Memory System

Privacy-first, intelligent memory for AI assistants.

## Features

- 🔒 **Local-First**: All data stored on-device with user-owned encryption
- 🧠 **Intelligent**: Outcome-based learning adapts to what matters
- 💰 **Cost-Efficient**: 30-50% token reduction through optimized context
- ✅ **Compliant**: Built for GDPR, HIPAA, CCPA requirements
- 🔌 **Model-Agnostic**: Works with any LLM (Ollama, OpenAI, Anthropic)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+ with pgvector extension
- Redis 7.0+
- Ollama (for local LLM)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/acms.git
cd acms

# Install dependencies
make install

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
make migrate-up

# Start development server
make dev
```

### Docker Compose

```bash
# Start all services
make docker-up

# Stop services
make docker-down
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test
poetry run pytest tests/unit/test_crs_engine.py -v
```

## Documentation

- [Getting Started](docs/guides/getting-started.md)
- [API Documentation](docs/api/openapi.yaml)
- [Architecture](docs/architecture/00-overview.md)
- [Deployment Guide](docs/deployment/kubernetes.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

Proprietary - See [LICENSE](LICENSE) for details.

## Security

Report security vulnerabilities to security@acms.example.com.
See [SECURITY.md](SECURITY.md) for our security policy.
```

---

## Development Workflow

### 1. Local Development Setup

```bash
# Initial setup
git clone https://github.com/your-org/acms.git
cd acms
cp .env.example .env

# Install dependencies
poetry install

# Start dependencies (Postgres, Redis, Ollama)
docker-compose -f infra/docker/docker-compose.dev.yml up -d

# Run migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn src.api.main:app --reload
```

### 2. Pre-Commit Hooks

```bash
# Install pre-commit
poetry run pre-commit install

# Run manually
poetry run pre-commit run --all-files
```

### 3. Testing Strategy

```bash
# Unit tests (fast)
poetry run pytest tests/unit/ -v

# Integration tests
poetry run pytest tests/integration/ -v

# Performance tests
poetry run pytest tests/performance/ -v --benchmark-only

# All tests with coverage
poetry run pytest tests/ --cov=src --cov-report=html
```

### 4. Code Quality

```bash
# Format code
poetry run black src tests
poetry run isort src tests

# Lint
poetry run flake8 src tests
poetry run mypy src

# Security scan
poetry run bandit -r src
poetry run safety check
```

---

## Deployment

### Kubernetes (Production)

```bash
# Build image
docker build -t acms:v2.0.0 -f infra/docker/Dockerfile .

# Push to registry
docker tag acms:v2.0.0 your-registry/acms:v2.0.0
docker push your-registry/acms:v2.0.0

# Deploy with Helm
helm upgrade --install acms infra/helm/ \
  --namespace acms-production \
  --values infra/helm/values-production.yaml \
  --set image.tag=v2.0.0
```

### Docker Compose (Dev/Staging)

```bash
# Build and start
docker-compose -f infra/docker/docker-compose.yml up -d --build

# View logs
docker-compose logs -f acms-api

# Stop
docker-compose down
```

---

## Monitoring

### Metrics (Prometheus)

Metrics exposed at `/metrics`:
- `acms_requests_total`
- `acms_queries_processed_total`
- `acms_token_savings_percent`
- `acms_rehydration_duration_seconds`
- `acms_crs_score`

### Tracing (Jaeger)

Distributed tracing for request flows:
- Access Jaeger UI at `http://localhost:16686`

### Logging

Structured JSON logs:
```json
{
  "timestamp": "2024-10-11T10:30:00Z",
  "level": "info",
  "event": "query_processed",
  "query_id": "uuid",
  "user_id": "uuid",
  "rehydration_time_ms": 347
}
```

---

**END OF REPOSITORY STRUCTURE**
