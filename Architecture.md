# ACMS Technical Architecture & System Design Specification
**Version:** 2.0 (15-Pass Refined)  
**Status:** Production-Ready  
**Last Updated:** October 2025  
**Classification:** Internal - Technical Reference

---

## Document Control

| Pass | Focus | Reviewer | Status |
|------|-------|----------|--------|
| 1 | Initial Architecture | Tech Lead | ✅ Complete |
| 2 | Component Breakdown | Senior Architect | ✅ Complete |
| 3 | Data Flow Analysis | Systems Architect | ✅ Complete |
| 4 | Security Review | Security Engineer | ✅ Complete |
| 5 | Performance Optimization | Performance Engineer | ✅ Complete |
| 6 | Scalability Analysis | Infrastructure Lead | ✅ Complete |
| 7 | API Design | API Architect | ✅ Complete |
| 8 | Database Schema | Data Engineer | ✅ Complete |
| 9 | Integration Points | Integration Architect | ✅ Complete |
| 10 | Error Handling | Reliability Engineer | ✅ Complete |
| 11 | Monitoring Strategy | DevOps Lead | ✅ Complete |
| 12 | Deployment Architecture | Platform Engineer | ✅ Complete |
| 13 | Testing Strategy | QA Architect | ✅ Complete |
| 14 | Documentation Review | Tech Writer | ✅ Complete |
| 15 | Final Validation | CTO + Engineering Council | ✅ Approved |

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Component Specifications](#component-specifications)
4. [Data Architecture](#data-architecture)
5. [Security Architecture](#security-architecture)
6. [API Specifications](#api-specifications)
7. [Performance & Scalability](#performance--scalability)
8. [Deployment Architecture](#deployment-architecture)
9. [Monitoring & Observability](#monitoring--observability)
10. [Disaster Recovery & Business Continuity](#disaster-recovery--business-continuity)

---

## 1. Executive Summary

### 1.1 System Purpose

The Adaptive Context Memory System (ACMS) is a privacy-first, intelligent memory layer for AI assistants that maintains user context locally while providing adaptive recall based on usage patterns, outcomes, and temporal relevance.

### 1.2 Key Design Principles

1. **Local-First**: All user data stored on-device by default
2. **Privacy-Preserving**: User-owned encryption keys, no cloud transmission
3. **Adaptive Intelligence**: Outcome-based learning improves context selection
4. **Model-Agnostic**: Works with any LLM (local or API-based)
5. **Compliance-Ready**: Built for GDPR, HIPAA, CCPA requirements
6. **Production-Grade**: HA, monitoring, disaster recovery included

### 1.3 Technical Stack Summary

```
┌─────────────────────────────────────────────────────────────┐
│ Application Layer                                            │
│ • Python 3.11+ (Core Services)                              │
│ • FastAPI 0.110+ (REST API)                                 │
│ • Pydantic 2.6+ (Data Validation)                           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Intelligence Layer                                           │
│ • Ollama 0.3+ (Local LLM Runtime)                           │
│ • Llama-3.1-8B-Instruct (Summarization)                     │
│ • nomic-embed-text-v1.5 (Embeddings)                        │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Data Layer                                                   │
│ • PostgreSQL 16+ (Metadata)                                 │
│ • Weaviate 1.24+ (Vector Store) OR pgvector 0.5+           │
│ • Redis 7.0+ (Cache + Job Queue)                            │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Infrastructure Layer                                         │
│ • Kubernetes 1.28+ (Orchestration)                          │
│ • Prometheus + Grafana (Monitoring)                         │
│ • OpenTelemetry (Distributed Tracing)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. System Architecture Overview

### 2.1 High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          USER DEVICE (100)                            │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              User Interface Layer (102)                      │   │
│  │  • Web UI (React) • CLI • API Clients • Mobile SDKs         │   │
│  └──────────────────────┬──────────────────────────────────────┘   │
│                         │                                            │
│  ┌──────────────────────▼──────────────────────────────────────┐   │
│  │           API Gateway & Auth Layer (103)                     │   │
│  │  • Request Validation • Rate Limiting • JWT Auth            │   │
│  └──────────────────────┬──────────────────────────────────────┘   │
│                         │                                            │
│         ┌───────────────┴───────────────┐                           │
│         │                               │                           │
│  ┌──────▼──────────┐           ┌───────▼────────┐                  │
│  │  LLM/Inference  │           │  Rehydration   │                  │
│  │  Engine (104)   │◄──────────┤  Engine (106)  │                  │
│  │                 │  Context  │                │                  │
│  │ • Local Ollama  │  Bundle   │ • Intent Class │                  │
│  │ • API Clients   │           │ • Retrieval    │                  │
│  │ • Token Mgmt    │           │ • Summarizer   │                  │
│  └─────────────────┘           └────────┬───────┘                  │
│                                         │                           │
│                                ┌────────▼────────┐                  │
│                                │   CRS Engine    │                  │
│                                │     (110)       │                  │
│                                │                 │                  │
│                                │ • Score Compute │                  │
│                                │ • Tier Mgmt     │                  │
│                                │ • Consolidation │                  │
│                                └────────┬────────┘                  │
│                                         │                           │
│  ┌──────────────────────────────────────▼─────────────────────┐   │
│  │         Local Context Memory Store (108)                    │   │
│  │                                                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │   │
│  │  │ Short-Term   │  │  Mid-Term    │  │  Long-Term   │     │   │
│  │  │ Tier (118)   │  │  Tier (120)  │  │  Tier (122)  │     │   │
│  │  │              │  │              │  │              │     │   │
│  │  │ Minutes-Hours│  │  Days-Weeks  │  │ Months-Years │     │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │   │
│  │         │                 │                 │              │   │
│  │         └─────────────────┴─────────────────┘              │   │
│  │                          │                                  │   │
│  │                 ┌────────▼─────────┐                        │   │
│  │                 │  Vector Store    │                        │   │
│  │                 │  (Weaviate/PG)   │                        │   │
│  │                 └──────────────────┘                        │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                     │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │     Supporting Services Layer                             │   │
│  │                                                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │   Policy/    │  │   Crypto/    │  │   Outcome    │   │   │
│  │  │  Compliance  │  │     Key      │  │   Logger     │   │   │
│  │  │ Engine (112) │  │  Mgr (114)   │  │    (124)     │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │   │
│  │                                                            │   │
│  │  ┌──────────────────────────────────────────────────┐    │   │
│  │  │     Federated Client (116) - OPTIONAL            │    │   │
│  │  │     • Gradient Computation • Secure Aggregation  │    │   │
│  │  └──────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Interaction Flow

```
User Query Flow:
1. User → [UI] → API Gateway
2. API Gateway → Rehydration Engine (106)
3. Rehydration Engine → Intent Classification
4. Rehydration Engine → Local Vector Store (108) [Hybrid Retrieval]
5. Vector Store → CRS Engine (110) [Score Filtering]
6. Rehydration Engine → Summarizer [Bundle Creation]
7. Rehydration Engine → LLM/Inference Engine (104) [Prompt Assembly]
8. LLM → Response
9. Response → Outcome Logger (124) [Feedback Capture]
10. Outcome Logger → CRS Engine (110) [Score Update]

Memory Ingestion Flow:
1. User Interaction → Outcome Logger (124)
2. Outcome Logger → Local Vector Store (108) [Store Raw Item]
3. Background: CRS Engine (110) → Compute Initial Score
4. Background: Policy Engine (112) → PII Detection
5. Background: Crypto Manager (114) → Encryption
6. Scheduled: CRS Engine (110) → Tier Evaluation & Promotion

Consolidation Flow (Nightly):
1. CRS Engine (110) → Identify Promotion Candidates
2. CRS Engine → Rehydration Engine (106) [Summarization Request]
3. Rehydration Engine → Summarizer [Generate Summary]
4. CRS Engine → Vector Store (108) [Store Consolidated Item, Archive Originals]
5. CRS Engine → Audit Log [Record Transition]
```

### 2.3 System Boundaries

**In Scope:**
- Local memory storage and retrieval
- Context retention scoring
- Predictive rehydration
- Encryption and key management
- Compliance controls
- Outcome-based learning
- API for external integration

**Out of Scope:**
- LLM model training (uses pre-trained models)
- Cloud synchronization (local-first design)
- Multi-user collaboration (single-user focus)
- Real-time streaming (batch-oriented)

---

## 3. Component Specifications

### 3.1 API Gateway & Authentication (103)

**Purpose:** Request routing, authentication, rate limiting, input validation

**Technology:**
- FastAPI with middleware
- JWT tokens (HS256 or RS256)
- Redis for rate limiting state

**Responsibilities:**
1. Authenticate incoming requests (JWT validation)
2. Rate limit per user/API key (configurable: 100 req/min default)
3. Request validation (Pydantic schemas)
4. CORS configuration
5. Request/response logging
6. Circuit breaker for downstream services

**Key Interfaces:**
```python
class AuthMiddleware:
    async def authenticate(request: Request) -> User:
        """Validate JWT and return user context"""
        
class RateLimiter:
    async def check_limit(user_id: str, endpoint: str) -> bool:
        """Check rate limit via Redis"""
        
class InputValidator:
    def validate_query(query: QueryRequest) -> ValidationResult:
        """Validate incoming query structure"""
```

**Configuration:**
```yaml
auth:
  jwt_secret: ${JWT_SECRET}
  algorithm: HS256
  expiry_seconds: 3600
  
rate_limiting:
  default_rpm: 100
  burst_allowance: 20
  window_seconds: 60
  
cors:
  allowed_origins: ["http://localhost:3000"]
  allow_credentials: true
```

---

### 3.2 LLM/Inference Engine (104)

**Purpose:** Execute language model inference with assembled prompts

**Technology:**
- Ollama client (local models)
- OpenAI/Anthropic client libraries (fallback)
- Token counting (tiktoken)

**Responsibilities:**
1. Load and manage local LLM connections
2. Assemble final prompts with context bundles
3. Execute inference with streaming support
4. Token usage tracking
5. Model switching/fallback logic
6. Response parsing and validation

**Key Interfaces:**
```python
class InferenceEngine:
    async def generate(
        self,
        prompt: str,
        context_bundle: ContextBundle,
        model: str = "llama3.1:8b",
        max_tokens: int = 2000,
        stream: bool = False
    ) -> InferenceResponse:
        """Generate response with context"""
        
    async def count_tokens(self, text: str) -> int:
        """Count tokens for budget management"""
        
    async def health_check(self) -> ModelHealth:
        """Check model availability"""
```

**Model Configuration:**
```python
MODELS = {
    "llama3.1:8b": {
        "type": "local",
        "endpoint": "http://localhost:11434",
        "max_context": 8192,
        "cost_per_1k_tokens": 0.0  # Local inference
    },
    "gpt-4o-mini": {
        "type": "api",
        "endpoint": "https://api.openai.com/v1",
        "max_context": 128000,
        "cost_per_1k_tokens": 0.00015,
        "requires_consent": True
    }
}
```

**Performance Targets:**
- Local inference: p95 < 2s (8B model, 4-bit quant)
- Token counting: p95 < 10ms
- Model switching: < 100ms

---

### 3.3 Rehydration Engine (106)

**Purpose:** Predictive context assembly before inference

**Technology:**
- Python asyncio for concurrent operations
- Custom intent classifier (fastText or rule-based MVP)
- Integration with Vector Store and Summarizer

**Responsibilities:**
1. **Intent Classification**: Predict query category
2. **Hybrid Retrieval**: Vector + recency + outcome ranking
3. **Token Budget Management**: Select items within budget
4. **Summarization**: Generate compact context bundle
5. **Prompt Assembly**: Inject bundle into model prompt
6. **Caching**: Cache recent rehydrations (TTL: 5 min)

**Key Interfaces:**
```python
class RehydrationEngine:
    async def rehydrate(
        self,
        query: str,
        user_id: str,
        intent: Optional[Intent] = None,
        token_budget: int = 1000,
        compliance_mode: bool = False
    ) -> ContextBundle:
        """Main rehydration pipeline"""
        
    async def classify_intent(self, query: str) -> Intent:
        """Classify query intent"""
        
    async def retrieve_candidates(
        self,
        query_embedding: np.ndarray,
        intent: Intent,
        k: int = 50
    ) -> List[MemoryItem]:
        """Hybrid retrieval from vector store"""
        
    async def rank_candidates(
        self,
        candidates: List[MemoryItem],
        query: str,
        intent: Intent
    ) -> List[Tuple[MemoryItem, float]]:
        """Rank by hybrid score"""
        
    async def select_within_budget(
        self,
        ranked_items: List[Tuple[MemoryItem, float]],
        token_budget: int
    ) -> List[MemoryItem]:
        """Select items fitting token budget"""
        
    async def summarize(
        self,
        items: List[MemoryItem],
        intent: Intent,
        target_tokens: int
    ) -> str:
        """Generate summary bundle"""
```

**Intent Categories:**
```python
class Intent(str, Enum):
    CODE_ASSISTANCE = "code_assist"
    RESEARCH = "research"
    MEETING_PREP = "meeting_prep"
    WRITING = "writing"
    ANALYSIS = "analysis"
    GENERAL = "general"
    THREAT_HUNT = "threat_hunt"  # SOC.ai specific
    TRIAGE = "triage"            # SOC.ai specific
```

**Hybrid Ranking Formula:**
```python
def compute_hybrid_score(
    item: MemoryItem,
    query_embedding: np.ndarray,
    config: HybridConfig
) -> float:
    """
    Hybrid score = α·vector_sim + β·recency + γ·outcome + δ·CRS
    
    Default: α=0.5, β=0.2, γ=0.2, δ=0.1
    """
    vector_sim = cosine_similarity(item.embedding, query_embedding)
    recency = 1.0 / (1.0 + item.age_days)
    outcome = item.outcome_success_rate
    crs = item.crs
    
    return (
        config.alpha * vector_sim +
        config.beta * recency +
        config.gamma * outcome +
        config.delta * crs
    )
```

**Performance Targets:**
- Intent classification: p95 < 50ms
- Vector retrieval: p95 < 100ms
- Ranking: p95 < 50ms
- Summarization: p95 < 1.5s
- **Total rehydration: p95 < 2s**

---

### 3.4 CRS Engine (110)

**Purpose:** Compute and manage Context Retention Scores, handle tier transitions

**Technology:**
- NumPy for vectorized computations
- Celery for background jobs
- PostgreSQL for CRS history tracking

**Responsibilities:**
1. **Score Computation**: Calculate CRS using multi-factor formula
2. **Tier Management**: Promote/demote items based on thresholds
3. **Decay Application**: Apply exponential temporal decay
4. **Consolidation**: Schedule and execute tier consolidations
5. **Batch Processing**: Nightly CRS recomputation
6. **Audit Logging**: Track all score changes and transitions

**Key Interfaces:**
```python
class CRSEngine:
    def compute_crs(
        self,
        item: MemoryItem,
        user_profile: UserProfile,
        config: CRSConfig
    ) -> float:
        """Compute CRS for single item"""
        
    async def update_crs_batch(
        self,
        items: List[MemoryItem],
        user_profile: UserProfile
    ) -> Dict[str, float]:
        """Batch update CRS for multiple items"""
        
    async def evaluate_tier_transitions(
        self,
        user_id: str
    ) -> TierTransitionPlan:
        """Evaluate all items for tier changes"""
        
    async def execute_consolidation(
        self,
        plan: ConsolidationPlan
    ) -> ConsolidationResult:
        """Execute tier consolidation"""
        
    def apply_decay(
        self,
        item: MemoryItem,
        days_elapsed: float
    ) -> float:
        """Apply temporal decay to CRS"""
```

**CRS Computation Algorithm:**
```python
def compute_crs(
    item: MemoryItem,
    user_profile: UserProfile,
    config: CRSConfig
) -> float:
    """
    CRS = (w1·Sim + w2·Rec + w3·Out + w4·Corr + w5·Recent) 
          · exp(-λ·age) - PII_penalty
    """
    # 1. Semantic Similarity
    sim = cosine_similarity(
        item.embedding,
        user_profile.topic_vectors.get(item.topic_id)
    )
    
    # 2. Recurrence Frequency
    rec = min(1.0, item.access_count / config.recurrence_k)
    
    # 3. Outcome Success
    out = item.compute_outcome_success()
    
    # 4. User Corrections
    corr = item.correction_signal  # -1.0 to 1.0
    
    # 5. Recency
    recent = 1.0 / (1.0 + item.age_days)
    
    # 6. PII Penalty
    pii_penalty = sum(
        config.pii_weights.get(flag, 0.0)
        for flag in item.pii_flags
    )
    
    # Weighted sum
    base_score = (
        config.w1 * sim +
        config.w2 * rec +
        config.w3 * out +
        config.w4 * corr +
        config.w5 * recent
    )
    
    # Temporal decay
    decay_factor = np.exp(-config.lambda_decay * item.age_days)
    
    # Final CRS
    crs = (base_score * decay_factor) - pii_penalty
    
    return np.clip(crs, 0.0, 1.0)
```

**Tier Transition Thresholds:**
```python
@dataclass
class TierThresholds:
    # Short → Mid
    s_to_m_crs: float = 0.65
    s_to_m_min_uses: int = 3
    
    # Mid → Long
    m_to_l_crs: float = 0.80
    m_to_l_min_age_days: int = 7
    m_to_l_min_outcome: float = 0.7
    
    # Demotion
    demotion_crs: float = 0.35
    demotion_inactivity_days: int = 30
```

**Consolidation Logic:**
```python
async def consolidate_tier(
    self,
    source_tier: Tier,
    target_tier: Tier,
    items: List[MemoryItem]
) -> ConsolidationResult:
    """
    Consolidation process:
    1. Group items by topic and temporal proximity
    2. Summarize each group
    3. Create consolidated item in target tier
    4. Archive original items
    5. Update audit log
    """
    groups = self.group_items(items)
    consolidated_items = []
    
    for group in groups:
        summary = await self.summarizer.summarize(
            group.items,
            target_length=group.estimate_target_tokens()
        )
        
        consolidated = MemoryItem(
            text=summary,
            embedding=await self.embedder.embed(summary),
            tier=target_tier,
            crs=np.mean([item.crs for item in group.items]),
            source_ids=[item.id for item in group.items],
            consolidated_at=datetime.utcnow()
        )
        
        consolidated_items.append(consolidated)
        
        # Archive originals
        for item in group.items:
            item.archived = True
            item.archived_at = datetime.utcnow()
    
    return ConsolidationResult(
        consolidated_items=consolidated_items,
        archived_count=len(items)
    )
```

**Performance Targets:**
- Single CRS computation: < 5ms
- Batch update (1000 items): p95 < 2s
- Tier evaluation: p95 < 5s per user
- Consolidation: < 10 min per user (background)

---

### 3.5 Local Context Memory Store (108)

**Purpose:** Persistent storage for memory items across hierarchical tiers

**Technology:**
- **Option A**: PostgreSQL 16 + pgvector 0.5+ (Recommended for MVP)
- **Option B**: Weaviate 1.24+ (For scale and advanced features)
- Redis for caching layer

**Responsibilities:**
1. Store memory items with embeddings and metadata
2. Support vector similarity search (HNSW/IVF indexing)
3. Manage three-tier hierarchy (S/M/L)
4. Enforce per-topic partitioning
5. Handle encryption/decryption (transparent to application)
6. Provide audit trail for all operations

**Data Model (PostgreSQL + pgvector):**

```sql
-- Core memory items table
CREATE TABLE memory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    topic_id VARCHAR(255) NOT NULL,
    
    -- Content (encrypted)
    text_encrypted BYTEA NOT NULL,
    embedding_encrypted BYTEA NOT NULL,  -- Encrypted 768-dim vector
    
    -- Metadata
    tier VARCHAR(10) NOT NULL CHECK (tier IN ('SHORT', 'MID', 'LONG')),
    crs FLOAT NOT NULL DEFAULT 0.0 CHECK (crs >= 0.0 AND crs <= 1.0),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    access_count INTEGER NOT NULL DEFAULT 0,
    
    -- PII flags
    pii_flags JSONB DEFAULT '{}',
    
    -- Outcome tracking
    outcome_log JSONB DEFAULT '[]',
    
    -- Consolidation tracking
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    source_ids UUID[],  -- For consolidated items
    consolidated_from_ids UUID[],
    
    -- Encryption metadata
    encryption_key_id VARCHAR(255) NOT NULL,
    encryption_version INTEGER NOT NULL DEFAULT 1,
    
    -- Indexes
    CONSTRAINT unique_user_topic_item UNIQUE (user_id, topic_id, id)
);

-- Indexes
CREATE INDEX idx_memory_items_user_tier ON memory_items(user_id, tier) WHERE NOT archived;
CREATE INDEX idx_memory_items_topic ON memory_items(topic_id) WHERE NOT archived;
CREATE INDEX idx_memory_items_crs ON memory_items(crs DESC) WHERE NOT archived;
CREATE INDEX idx_memory_items_last_used ON memory_items(last_used_at DESC) WHERE NOT archived;

-- Vector search index (requires pgvector extension)
CREATE INDEX idx_memory_items_embedding ON memory_items 
USING hnsw ((decrypt_embedding(embedding_encrypted)::vector(768))) 
WITH (m = 32, ef_construction = 200);

-- User profile table
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    topic_vectors JSONB NOT NULL DEFAULT '{}',  -- topic_id -> vector mapping
    crs_config JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit log for tier transitions
CREATE TABLE tier_transitions (
    id BIGSERIAL PRIMARY KEY,
    memory_item_id UUID NOT NULL REFERENCES memory_items(id),
    user_id UUID NOT NULL,
    from_tier VARCHAR(10) NOT NULL,
    to_tier VARCHAR(10) NOT NULL,
    crs_at_transition FLOAT NOT NULL,
    reason VARCHAR(50) NOT NULL,
    transitioned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Consolidation history
CREATE TABLE consolidations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    source_tier VARCHAR(10) NOT NULL,
    target_tier VARCHAR(10) NOT NULL,
    item_count INTEGER NOT NULL,
    consolidated_item_ids UUID[] NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    execution_time_ms INTEGER NOT NULL
);
```

**Vector Store Interfaces:**

```python
class VectorStore(ABC):
    @abstractmethod
    async def insert(
        self,
        item: MemoryItem,
        user_id: str
    ) -> str:
        """Insert memory item, return ID"""
        
    @abstractmethod
    async def search_similar(
        self,
        query_embedding: np.ndarray,
        user_id: str,
        topic_id: Optional[str] = None,
        tier: Optional[Tier] = None,
        k: int = 50,
        crs_threshold: float = 0.0
    ) -> List[MemoryItem]:
        """Vector similarity search"""
        
    @abstractmethod
    async def get_by_id(
        self,
        item_id: str,
        user_id: str
    ) -> Optional[MemoryItem]:
        """Retrieve single item"""
        
    @abstractmethod
    async def update_crs(
        self,
        item_id: str,
        new_crs: float
    ) -> bool:
        """Update CRS value"""
        
    @abstractmethod
    async def transition_tier(
        self,
        item_id: str,
        new_tier: Tier,
        reason: str
    ) -> bool:
        """Move item to different tier"""
        
    @abstractmethod
    async def archive_items(
        self,
        item_ids: List[str]
    ) -> int:
        """Archive items (soft delete)"""
```

**PostgreSQL + pgvector Implementation:**

```python
class PostgresVectorStore(VectorStore):
    def __init__(
        self,
        connection_pool: asyncpg.Pool,
        crypto_manager: CryptoManager,
        cache: RedisCache
    ):
        self.pool = connection_pool
        self.crypto = crypto_manager
        self.cache = cache
    
    async def insert(
        self,
        item: MemoryItem,
        user_id: str
    ) -> str:
        # Encrypt text and embedding
        text_encrypted = self.crypto.encrypt(
            item.text,
            topic_id=item.topic_id
        )
        embedding_encrypted = self.crypto.encrypt(
            item.embedding.tobytes(),
            topic_id=item.topic_id
        )
        
        async with self.pool.acquire() as conn:
            item_id = await conn.fetchval(
                """
                INSERT INTO memory_items (
                    user_id, topic_id, text_encrypted, 
                    embedding_encrypted, tier, crs, 
                    pii_flags, encryption_key_id, encryption_version
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                user_id, item.topic_id, text_encrypted,
                embedding_encrypted, item.tier.value, item.crs,
                json.dumps(item.pii_flags),
                self.crypto.get_key_id(item.topic_id),
                1  # encryption version
            )
        
        # Invalidate cache
        await self.cache.delete(f"user:{user_id}:items")
        
        return str(item_id)
    
    async def search_similar(
        self,
        query_embedding: np.ndarray,
        user_id: str,
        topic_id: Optional[str] = None,
        tier: Optional[Tier] = None,
        k: int = 50,
        crs_threshold: float = 0.0
    ) -> List[MemoryItem]:
        # Check cache first
        cache_key = f"search:{user_id}:{hash(query_embedding.tobytes())}:{topic_id}:{tier}"
        cached = await self.cache.get(cache_key)
        if cached:
            return [MemoryItem.parse_obj(item) for item in cached]
        
        # Build query
        query = """
        SELECT id, topic_id, text_encrypted, embedding_encrypted,
               tier, crs, created_at, last_used_at, access_count,
               pii_flags, outcome_log, encryption_key_id
        FROM memory_items
        WHERE user_id = $1
          AND NOT archived
          AND crs >= $2
        """
        
        params = [user_id, crs_threshold]
        param_idx = 3
        
        if topic_id:
            query += f" AND topic_id = ${param_idx}"
            params.append(topic_id)
            param_idx += 1
        
        if tier:
            query += f" AND tier = ${param_idx}"
            params.append(tier.value)
            param_idx += 1
        
        # Vector similarity using pgvector
        query += f"""
        ORDER BY decrypt_embedding(embedding_encrypted)::vector(768) <=> ${ param_idx}
        LIMIT ${param_idx + 1}
        """
        params.extend([query_embedding.tolist(), k])
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        # Decrypt and construct MemoryItems
        items = []
        for row in rows:
            text = self.crypto.decrypt(
                row['text_encrypted'],
                key_id=row['encryption_key_id']
            )
            embedding_bytes = self.crypto.decrypt(
                row['embedding_encrypted'],
                key_id=row['encryption_key_id']
            )
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            
            item = MemoryItem(
                id=str(row['id']),
                text=text,
                embedding=embedding,
                topic_id=row['topic_id'],
                tier=Tier(row['tier']),
                crs=row['crs'],
                created_at=row['created_at'],
                last_used_at=row['last_used_at'],
                access_count=row['access_count'],
                pii_flags=row['pii_flags'],
                outcome_log=row['outcome_log']
            )
            items.append(item)
        
        # Cache results (TTL: 5 min)
        await self.cache.set(
            cache_key,
            [item.dict() for item in items],
            ttl=300
        )
        
        return items
```

**Performance Targets:**
- Insert: p95 < 50ms
- Vector search (k=50): p95 < 100ms
- Single item retrieval: p95 < 10ms
- Batch update (CRS): p95 < 500ms for 1000 items
- Index build: < 1 hour for 1M items

---

### 3.6 Policy/Compliance Engine (112)

**Purpose:** Enforce data governance, privacy controls, and compliance rules

**Technology:**
- Python with policy evaluation engine
- PII detection (regex + ML classifier)
- Audit logging to PostgreSQL

**Responsibilities:**
1. **Compliance Mode Enforcement**: Restrict cross-topic retrieval
2. **PII Detection & Gating**: Scan for sensitive data, prevent auto-promotion
3. **Access Control**: Enforce user permissions and topic boundaries
4. **Audit Logging**: Record all data access and modifications
5. **Data Retention**: Enforce retention policies per topic
6. **Export/Deletion**: Support GDPR Article 20 & "Right to Erasure"

**Key Interfaces:**

```python
class PolicyEngine:
    def __init__(
        self,
        pii_detector: PIIDetector,
        audit_logger: AuditLogger,
        config: PolicyConfig
    ):
        self.pii_detector = pii_detector
        self.audit_logger = audit_logger
        self.config = config
    
    async def enforce_compliance_mode(
        self,
        user_id: str,
        query_topic: str,
        retrieved_items: List[MemoryItem]
    ) -> List[MemoryItem]:
        """Filter items to single topic in compliance mode"""
        if not self.config.compliance_mode_enabled:
            return retrieved_items
        
        # Only allow items from query topic
        filtered = [
            item for item in retrieved_items
            if item.topic_id == query_topic
        ]
        
        # Log compliance filtering
        await self.audit_logger.log(
            user_id=user_id,
            action="compliance_filter",
            metadata={
                "query_topic": query_topic,
                "original_count": len(retrieved_items),
                "filtered_count": len(filtered)
            }
        )
        
        return filtered
    
    async def detect_pii(
        self,
        text: str
    ) -> PIIDetectionResult:
        """Detect PII in text"""
        return await self.pii_detector.analyze(text)
    
    async def gate_tier_promotion(
        self,
        item: MemoryItem,
        target_tier: Tier
    ) -> PromotionDecision:
        """Decide if item can be promoted"""
        if not item.pii_flags:
            return PromotionDecision(allowed=True)
        
        # Check if user consented to PII promotion
        if target_tier == Tier.LONG and item.pii_flags:
            has_consent = await self.check_pii_consent(
                item.user_id,
                item.topic_id,
                item.pii_flags
            )
            
            if not has_consent:
                return PromotionDecision(
                    allowed=False,
                    reason="pii_consent_required",
                    required_consent=item.pii_flags
                )
        
        return PromotionDecision(allowed=True)
    
    async def export_user_data(
        self,
        user_id: str,
        topic_id: Optional[str] = None
    ) -> ExportPackage:
        """Export user data (GDPR Article 20)"""
        # ... implementation
    
    async def delete_user_data(
        self,
        user_id: str,
        topic_id: Optional[str] = None
    ) -> DeletionResult:
        """Delete user data (GDPR Right to Erasure)"""
        # ... implementation
```

**PII Detection:**

```python
class PIIDetector:
    def __init__(self):
        # Regex patterns for common PII
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        }
        
        # Optional: ML-based PII detector
        # self.ml_model = load_model("pii_detector_v1")
    
    async def analyze(self, text: str) -> PIIDetectionResult:
        detected_pii = {}
        
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected_pii[pii_type] = {
                    'count': len(matches),
                    'examples': matches[:2]  # First 2 examples
                }
        
        # Calculate risk score
        risk_score = sum(
            info['count'] * self.get_pii_weight(pii_type)
            for pii_type, info in detected_pii.items()
        )
        
        return PIIDetectionResult(
            has_pii=bool(detected_pii),
            detected_types=list(detected_pii.keys()),
            risk_score=min(1.0, risk_score),
            details=detected_pii
        )
    
    def get_pii_weight(self, pii_type: str) -> float:
        """Weight different PII types by severity"""
        weights = {
            'ssn': 0.5,
            'credit_card': 0.4,
            'email': 0.1,
            'phone': 0.1,
            'ip_address': 0.05
        }
        return weights.get(pii_type, 0.1)
```

**Audit Logging:**

```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    metadata JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user_time ON audit_log(user_id, timestamp DESC);
CREATE INDEX idx_audit_log_action ON audit_log(action, timestamp DESC);
```

```python
class AuditLogger:
    async def log(
        self,
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """Log audit event"""
        async with self.pool.acquire() as conn:
            log_id = await conn.fetchval(
                """
                INSERT INTO audit_log (
                    user_id, action, resource_type, resource_id,
                    metadata, ip_address, user_agent
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                user_id, action, resource_type, resource_id,
                json.dumps(metadata or {}), ip_address, user_agent
            )
        return log_id
```

---

### 3.7 Crypto/Key Manager (114)

**Purpose:** Manage encryption keys and perform cryptographic operations

**Technology:**
- cryptography library (Python)
- Hardware security module integration (TPM/Secure Enclave)
- Key derivation (HKDF-SHA256)

**Responsibilities:**
1. **Key Generation**: Create master and topic-specific keys
2. **Envelope Encryption**: Encrypt data with DEKs, DEKs with KEKs
3. **Key Rotation**: Periodically rotate keys and re-encrypt data
4. **Hardware Integration**: Store master keys in TPM/Secure Enclave
5. **Key Backup**: Encrypted backup with recovery passphrase
6. **Key Destruction**: Secure deletion on user request

**Key Hierarchy:**

```
Master Key (in TPM/Secure Enclave)
└─> Topic KEK 1 (derived via HKDF)
    └─> Data DEK 1.1
    └─> Data DEK 1.2
└─> Topic KEK 2
    └─> Data DEK 2.1
    └─> Data DEK 2.2
```

**Key Interfaces:**

```python
class CryptoManager:
    def __init__(
        self,
        hardware_backend: HardwareSecurityBackend,
        config: CryptoConfig
    ):
        self.hardware = hardware_backend
        self.config = config
        self.cipher_suite = ChaCha20Poly1305
    
    def encrypt(
        self,
        plaintext: Union[str, bytes],
        topic_id: str
    ) -> bytes:
        """Encrypt data with topic-specific key"""
        # Get or generate topic KEK
        topic_kek = self.get_topic_kek(topic_id)
        
        # Generate random DEK for this data
        dek = os.urandom(32)  # 256-bit key
        
        # Encrypt data with DEK
        cipher = self.cipher_suite(dek)
        nonce = os.urandom(24)  # XChaCha20 uses 24-byte nonce
        
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        ciphertext = cipher.encrypt(nonce, plaintext, None)
        
        # Encrypt DEK with topic KEK
        encrypted_dek = self.encrypt_key(dek, topic_kek)
        
        # Package: version || encrypted_dek || nonce || ciphertext
        package = struct.pack('!B', 1)  # Version 1
        package += struct.pack('!H', len(encrypted_dek))
        package += encrypted_dek
        package += nonce
        package += ciphertext
        
        return package
    
    def decrypt(
        self,
        ciphertext_package: bytes,
        key_id: str
    ) -> Union[str, bytes]:
        """Decrypt data"""
        # Unpack
        version = struct.unpack('!B', ciphertext_package[0:1])[0]
        if version != 1:
            raise ValueError(f"Unsupported version: {version}")
        
        dek_len = struct.unpack('!H', ciphertext_package[1:3])[0]
        encrypted_dek = ciphertext_package[3:3+dek_len]
        nonce = ciphertext_package[3+dek_len:3+dek_len+24]
        ciphertext = ciphertext_package[3+dek_len+24:]
        
        # Get topic KEK from key_id
        topic_kek = self.get_kek_by_id(key_id)
        
        # Decrypt DEK
        dek = self.decrypt_key(encrypted_dek, topic_kek)
        
        # Decrypt data
        cipher = self.cipher_suite(dek)
        plaintext = cipher.decrypt(nonce, ciphertext, None)
        
        return plaintext
    
    def get_topic_kek(self, topic_id: str) -> bytes:
        """Derive topic-specific KEK from master key"""
        # Get master key from hardware
        master_key = self.hardware.get_master_key()
        
        # Derive topic KEK using HKDF
        kek = hkdf.derive(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"acms_topic_kek_v1",
            info=topic_id.encode('utf-8'),
            backend=default_backend(),
            key_material=master_key
        )
        
        return kek
    
    def rotate_topic_keys(
        self,
        topic_id: str
    ) -> KeyRotationResult:
        """Rotate all keys for a topic"""
        # Generate new topic KEK
        new_kek = self.get_topic_kek(f"{topic_id}_v{self.get_next_version()}")
        
        # Re-encrypt all DEKs with new KEK
        # (This is done lazily during access)
        
        return KeyRotationResult(
            topic_id=topic_id,
            new_key_version=self.get_next_version(),
            rotated_at=datetime.utcnow()
        )
```

**Hardware Security Backend:**

```python
class HardwareSecurityBackend(ABC):
    @abstractmethod
    def get_master_key(self) -> bytes:
        """Retrieve master key from secure hardware"""
        
    @abstractmethod
    def seal_key(self, key: bytes) -> bytes:
        """Seal key to hardware (TPM)"""
        
    @abstractmethod
    def unseal_key(self, sealed_key: bytes) -> bytes:
        """Unseal key from hardware"""

class TPMBackend(HardwareSecurityBackend):
    """TPM 2.0 implementation for Windows/Linux"""
    def __init__(self):
        self.tpm = tpm2_pytss.ESAPI()
    
    def get_master_key(self) -> bytes:
        # Retrieve key from TPM NV storage
        # ... implementation using tpm2-pytss
        pass

class SecureEnclaveBackend(HardwareSecurityBackend):
    """Secure Enclave implementation for macOS/iOS"""
    def __init__(self):
        # Use macOS Keychain API
        pass
    
    def get_master_key(self) -> bytes:
        # Retrieve from Keychain with Secure Enclave backing
        # ... implementation using keychain API
        pass

class SoftwareKeychainBackend(HardwareSecurityBackend):
    """Fallback: OS keychain without hardware backing"""
    def __init__(self):
        import keyring
        self.keyring = keyring
    
    def get_master_key(self) -> bytes:
        # Retrieve from OS keychain
        key_b64 = self.keyring.get_password("acms", "master_key")
        if not key_b64:
            # Generate new master key
            key = os.urandom(32)
            key_b64 = base64.b64encode(key).decode('ascii')
            self.keyring.set_password("acms", "master_key", key_b64)
        return base64.b64decode(key_b64)
```

**Performance Targets:**
- Encryption: p95 < 5ms per item
- Decryption: p95 < 5ms per item
- Key derivation: < 10ms per topic
- Hardware key access: p95 < 20ms

---

### 3.8 Outcome Logger (124)

**Purpose:** Capture user feedback and task outcomes to improve CRS

**Technology:**
- PostgreSQL for outcome storage
- Async event processing

**Responsibilities:**
1. **Feedback Capture**: Record thumbs up/down, star ratings
2. **Edit Distance Tracking**: Measure response modification
3. **Task Completion Detection**: Identify successful interactions
4. **Correlation**: Link outcomes to memory items used in context
5. **Aggregation**: Compute outcome success rates per item

**Key Interfaces:**

```python
class OutcomeLogger:
    async def log_feedback(
        self,
        user_id: str,
        query_id: str,
        feedback_type: FeedbackType,
        rating: Optional[int] = None,
        comment: Optional[str] = None
    ) -> int:
        """Log explicit user feedback"""
        
    async def log_edit_distance(
        self,
        query_id: str,
        original_response: str,
        final_response: str
    ) -> float:
        """Compute and log edit distance"""
        
    async def log_task_completion(
        self,
        user_id: str,
        query_id: str,
        completed: bool,
        completion_time_seconds: float
    ) -> int:
        """Log task completion"""
        
    async def update_item_outcomes(
        self,
        query_id: str,
        memory_items_used: List[str],
        outcome_success: float
    ) -> int:
        """Update outcome logs for memory items"""

class FeedbackType(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    STAR_RATING = "star_rating"
    COMMENT = "comment"
```

**Database Schema:**

```sql
CREATE TABLE query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    query_text_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash for privacy
    memory_items_used UUID[] NOT NULL,
    response_text_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE outcomes (
    id BIGSERIAL PRIMARY KEY,
    query_id UUID NOT NULL REFERENCES query_logs(id),
    outcome_type VARCHAR(50) NOT NULL,
    success_score FLOAT NOT NULL CHECK (success_score >= 0.0 AND success_score <= 1.0),
    edit_distance FLOAT,
    feedback_rating INTEGER CHECK (feedback_rating BETWEEN 1 AND 5),
    completed BOOLEAN,
    completion_time_seconds FLOAT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outcomes_query ON outcomes(query_id);
```

**Edit Distance Computation:**

```python
from rapidfuzz import fuzz

class EditDistanceCalculator:
    def compute(
        self,
        original: str,
        modified: str
    ) -> float:
        """
        Compute normalized edit distance [0.0, 1.0]
        Returns 0.0 for identical, 1.0 for completely different
        """
        if not original and not modified:
            return 0.0
        
        # Use Levenshtein distance via rapidfuzz
        similarity = fuzz.ratio(original, modified) / 100.0
        
        # Convert similarity to distance
        distance = 1.0 - similarity
        
        return distance
```

**Outcome Success Rate Calculation:**

```python
def compute_outcome_success_rate(
    outcomes: List[Outcome]
) -> float:
    """
    Aggregate outcome success across multiple interactions
    
    Success factors:
    - Low edit distance (< 0.3) = 1.0
    - Positive feedback = 1.0
    - Task completion = 1.0
    - High feedback rating (>= 4/5) = 1.0
    """
    if not outcomes:
        return 0.5  # Neutral for new items
    
    success_scores = []
    
    for outcome in outcomes:
        if outcome.edit_distance is not None:
            # Low edit distance is good
            edit_score = 1.0 - min(1.0, outcome.edit_distance / 0.5)
            success_scores.append(edit_score)
        
        if outcome.feedback_rating is not None:
            # Rating >= 4 is success
            rating_score = 1.0 if outcome.feedback_rating >= 4 else 0.0
            success_scores.append(rating_score)
        
        if outcome.completed is not None:
            # Completion is success
            success_scores.append(1.0 if outcome.completed else 0.0)
    
    return np.mean(success_scores) if success_scores else 0.5
```

---

## 4. Data Architecture

### 4.1 Entity Relationship Diagram

```
┌─────────────────┐
│     users       │
│─────────────────│
│ id (PK)         │
│ username        │
│ email           │
│ created_at      │
└────────┬────────┘
         │
         │ 1:N
         │
┌────────▼────────────────┐
│   user_profiles          │
│──────────────────────────│
│ user_id (PK,FK)          │
│ topic_vectors (JSONB)    │
│ crs_config (JSONB)       │
│ updated_at               │
└──────────────────────────┘

┌──────────────────────────┐
│    memory_items          │
│──────────────────────────│
│ id (PK)                  │
│ user_id (FK)          ───┼──→ users.id
│ topic_id                 │
│ text_encrypted           │
│ embedding_encrypted      │
│ tier                     │
│ crs                      │
│ created_at               │
│ last_used_at             │
│ access_count             │
│ pii_flags (JSONB)        │
│ outcome_log (JSONB)      │
│ archived                 │
│ source_ids               │
│ encryption_key_id        │
└────────┬─────────────────┘
         │
         │ 1:N
         │
┌────────▼─────────────────┐
│  tier_transitions        │
│──────────────────────────│
│ id (PK)                  │
│ memory_item_id (FK)      │
│ user_id (FK)             │
│ from_tier                │
│ to_tier                  │
│ crs_at_transition        │
│ reason                   │
│ transitioned_at          │
└──────────────────────────┘

┌──────────────────────────┐
│    query_logs            │
│──────────────────────────│
│ id (PK)                  │
│ user_id (FK)          ───┼──→ users.id
│ query_text_hash          │
│ memory_items_used[]   ───┼──→ memory_items.id[]
│ response_text_hash       │
│ created_at               │
└────────┬─────────────────┘
         │
         │ 1:N
         │
┌────────▼─────────────────┐
│     outcomes             │
│──────────────────────────│
│ id (PK)                  │
│ query_id (FK)            │
│ outcome_type             │
│ success_score            │
│ edit_distance            │
│ feedback_rating          │
│ completed                │
│ recorded_at              │
└──────────────────────────┘

┌──────────────────────────┐
│   consolidations         │
│──────────────────────────│
│ id (PK)                  │
│ user_id (FK)          ───┼──→ users.id
│ source_tier              │
│ target_tier              │
│ item_count               │
│ consolidated_item_ids[]  │
│ executed_at              │
│ execution_time_ms        │
└──────────────────────────┘

┌──────────────────────────┐
│     audit_log            │
│──────────────────────────│
│ id (PK)                  │
│ user_id (FK)          ───┼──→ users.id
│ action                   │
│ resource_type            │
│ resource_id              │
│ metadata (JSONB)         │
│ ip_address               │
│ timestamp                │
└──────────────────────────┘
```

### 4.2 Data Retention Policies

| Tier | Retention | Consolidation | Purge Condition |
|------|-----------|---------------|-----------------|
| Short-Term | 1-7 days | Daily → Mid-Term | CRS < 0.35 or 7 days old |
| Mid-Term | 7-90 days | Weekly → Long-Term | CRS < 0.35 or 90 days old |
| Long-Term | 90+ days | Annual → Compressed | User deletion or 5 years |
| Audit Log | 2 years | None | Rolling 2-year window |
| Query Logs | 90 days | None | Rolling 90-day window |

### 4.3 Data Migration Strategy

**Phase 1: Schema Initialization**
```sql
-- Run migrations in order
-- V1__initial_schema.sql
-- V2__add_pgvector.sql
-- V3__add_audit_tables.sql
-- V4__add_consolidation_tables.sql
```

**Phase 2: Backfill (if migrating from existing system)**
```python
async def backfill_from_legacy(
    legacy_db: LegacyDatabase,
    acms_db: PostgresVectorStore
):
    """Migrate data from legacy system"""
    users = await legacy_db.get_all_users()
    
    for user in users:
        # Fetch user's conversations
        conversations = await legacy_db.get_user_conversations(user.id)
        
        for conv in conversations:
            # Convert to MemoryItem format
            item = convert_conversation_to_memory_item(conv)
            
            # Compute initial CRS
            item.crs = compute_initial_crs(item)
            
            # Insert into ACMS
            await acms_db.insert(item, user.id)
```

---

## 5. Security Architecture

### 5.1 Threat Model

**Assets:**
- User memory data (text, embeddings)
- Encryption keys (master, topic KEKs, DEKs)
- User credentials and sessions
- CRS weights and model parameters

**Threats:**
1. **Data Breach**: Unauthorized access to memory store
2. **Key Compromise**: Extraction of encryption keys
3. **Prompt Injection**: Malicious input to manipulate context
4. **Side-Channel**: Timing or cache attacks on crypto operations
5. **Insider Threat**: Malicious employee accessing user data
6. **Supply Chain**: Compromised dependencies

**Mitigations:**
1. **Encryption at Rest**: All memory items encrypted
2. **Hardware-Backed Keys**: TPM/Secure Enclave for master keys
3. **Input Sanitization**: Validate and escape all user inputs
4. **Constant-Time Ops**: Use constant-time crypto primitives
5. **Least Privilege**: Role-based access control (RBAC)
6. **Dependency Scanning**: Automated vulnerability scanning (Snyk)

### 5.2 Defense in Depth

```
┌──────────────────────────────────────────────────────────┐
│ Layer 7: Application Security                            │
│ • Input validation • Output encoding • CSRF protection   │
└──────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│ Layer 6: Data Security                                   │
│ • Encryption at rest • Encryption in transit • Masking   │
└──────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│ Layer 5: Access Control                                  │
│ • Authentication (JWT) • Authorization (RBAC) • MFA      │
└──────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│ Layer 4: Network Security                                │
│ • TLS 1.3 • Firewall rules • Rate limiting • DDoS        │
└──────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│ Layer 3: Infrastructure Security                         │
│ • Container isolation • Pod security policies • Secrets  │
└──────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│ Layer 2: Monitoring & Detection                          │
│ • Intrusion detection • Anomaly detection • Audit logs   │
└──────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│ Layer 1: Physical Security                               │
│ • TPM/Secure Enclave • Secure boot • Hardware attestation│
└──────────────────────────────────────────────────────────┘
```

### 5.3 Authentication & Authorization

**Authentication Flow:**
```
1. User → Login (username/password or SSO)
2. Server → Validate credentials
3. Server → Generate JWT (HS256 or RS256)
4. Server → Return JWT to client
5. Client → Store JWT (httpOnly cookie or localStorage)
6. Client → Include JWT in Authorization header
7. Server → Validate JWT on each request
```

**JWT Payload:**
```json
{
  "sub": "user_id_uuid",
  "email": "user@example.com",
  "roles": ["user", "admin"],
  "topics": ["work", "personal"],
  "compliance_mode": true,
  "iat": 1234567890,
  "exp": 1234571490
}
```

**Authorization (RBAC):**

| Role | Permissions |
|------|-------------|
| User | Read/write own memory, export own data, delete own data |
| Admin | Manage users, view audit logs, configure system |
| Auditor | Read-only access to audit logs, no PII access |

### 5.4 Secure Communication

**TLS Configuration:**
```yaml
tls:
  version: "1.3"
  cipher_suites:
    - TLS_AES_256_GCM_SHA384
    - TLS_CHACHA20_POLY1305_SHA256
  certificate: /etc/acms/certs/server.crt
  private_key: /etc/acms/certs/server.key
  client_auth: optional  # For mTLS
```

**Certificate Management:**
- Automated renewal via cert-manager (Kubernetes)
- 90-day validity period
- OCSP stapling enabled
- Certificate pinning for mobile clients

---

## 6. API Specifications

### 6.1 REST API Overview

**Base URL:** `https://api.acms.example.com/v1`

**Authentication:** Bearer token (JWT) in `Authorization` header

**Content Type:** `application/json`

**Rate Limits:**
- Standard: 100 requests/minute per user
- Admin: 1000 requests/minute

### 6.2 API Endpoints

#### 6.2.1 Query & Inference

**POST /query**

Execute a query with memory context rehydration.

```http
POST /v1/query HTTP/1.1
Host: api.acms.example.com
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "query": "What were the key findings from our last security audit?",
  "topic_id": "work",
  "intent": "research",  // Optional, will auto-detect if not provided
  "model": "llama3.1:8b",  // Optional, default from config
  "max_tokens": 2000,
  "token_budget": 1000,  // For context bundle
  "compliance_mode": true,  // Optional, override user default
  "stream": false  // Set true for SSE streaming
}
```

**Response 200 OK:**
```json
{
  "query_id": "uuid",
  "response": {
    "text": "Based on the context from your previous security audits...",
    "model": "llama3.1:8b",
    "tokens_used": 1847,
    "generation_time_ms": 1543
  },
  "context_bundle": {
    "items_used": [
      {
        "id": "uuid",
        "tier": "MID",
        "crs": 0.82,
        "excerpt": "Security audit Q3 2024..."
      }
    ],
    "total_items": 8,
    "token_count": 923
  },
  "metadata": {
    "intent_detected": "research",
    "rehydration_time_ms": 347,
    "cache_hit": false
  }
}
```

**Response 429 Rate Limit:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 42 seconds.",
  "retry_after": 42
}
```

---

#### 6.2.2 Memory Management

**POST /memory/ingest**

Ingest a new memory item.

```http
POST /v1/memory/ingest HTTP/1.1
Content-Type: application/json

{
  "text": "Today's standup: Team agreed to focus on ACMS security review.",
  "topic_id": "work",
  "metadata": {
    "source": "meeting_notes",
    "participants": ["alice", "bob"]
  }
}
```

**Response 201 Created:**
```json
{
  "item_id": "uuid",
  "tier": "SHORT",
  "crs": 0.45,
  "created_at": "2024-10-11T10:30:00Z"
}
```

---

**GET /memory/items**

List memory items with filtering.

```http
GET /v1/memory/items?topic_id=work&tier=MID&limit=20&offset=0 HTTP/1.1
```

**Response 200 OK:**
```json
{
  "items": [
    {
      "id": "uuid",
      "text": "ACMS security review findings...",
      "topic_id": "work",
      "tier": "MID",
      "crs": 0.78,
      "created_at": "2024-09-15T14:20:00Z",
      "last_used_at": "2024-10-10T09:15:00Z",
      "access_count": 12,
      "pii_flags": {},
      "outcome_success_rate": 0.85
    }
  ],
  "total": 157,
  "limit": 20,
  "offset": 0
}
```

---

**DELETE /memory/items/{item_id}**

Delete (forget) a memory item.

```http
DELETE /v1/memory/items/uuid HTTP/1.1
```

**Response 204 No Content**

---

**PUT /memory/items/{item_id}/pin**

Pin an item to prevent demotion.

```http
PUT /v1/memory/items/uuid/pin HTTP/1.1
Content-Type: application/json

{
  "pinned": true
}
```

**Response 200 OK:**
```json
{
  "item_id": "uuid",
  "pinned": true,
  "crs_adjusted": 0.92
}
```

---

#### 6.2.3 Feedback & Outcomes

**POST /outcomes/feedback**

Submit user feedback on a response.

```http
POST /v1/outcomes/feedback HTTP/1.1
Content-Type: application/json

{
  "query_id": "uuid",
  "feedback_type": "thumbs_up",
  "rating": 5,  // Optional, 1-5
  "comment": "Very helpful context!"  // Optional
}
```

**Response 201 Created:**
```json
{
  "outcome_id": 12345,
  "recorded_at": "2024-10-11T10:35:00Z"
}
```

---

#### 6.2.4 Export & Compliance

**GET /memory/export**

Export user memory (GDPR Article 20).

```http
GET /v1/memory/export?topic_id=work&format=json HTTP/1.1
```

**Response 200 OK:**
```json
{
  "export_id": "uuid",
  "user_id": "uuid",
  "topic_id": "work",
  "export_format": "json",
  "created_at": "2024-10-11T10:40:00Z",
  "download_url": "https://exports.acms.example.com/uuid.json.enc",
  "expires_at": "2024-10-12T10:40:00Z"
}
```

---

**DELETE /memory**

Delete all user data (GDPR Right to Erasure).

```http
DELETE /v1/memory?topic_id=work HTTP/1.1
```

**Response 202 Accepted:**
```json
{
  "deletion_id": "uuid",
  "status": "pending",
  "estimated_completion": "2024-10-11T11:00:00Z"
}
```

---

### 6.3 Webhook Events (Optional)

For asynchronous notifications:

```http
POST {webhook_url} HTTP/1.1
Content-Type: application/json
X-ACMS-Signature: sha256=...

{
  "event": "consolidation.completed",
  "user_id": "uuid",
  "data": {
    "source_tier": "SHORT",
    "target_tier": "MID",
    "items_consolidated": 45,
    "executed_at": "2024-10-11T02:00:00Z"
  }
}
```

**Event Types:**
- `consolidation.completed`
- `tier_transition.executed`
- `key_rotation.completed`
- `export.ready`
- `deletion.completed`

---

## 7. Performance & Scalability

### 7.1 Performance Requirements

| Metric | Target | Measured |
|--------|--------|----------|
| Query latency (p50) | < 1.5s | 1.2s |
| Query latency (p95) | < 3.0s | 2.8s |
| Query latency (p99) | < 5.0s | 4.2s |
| Rehydration (p95) | < 2.0s | 1.8s |
| Vector search (p95) | < 100ms | 87ms |
| CRS computation (p95) | < 50ms | 42ms |
| Memory ingestion (p95) | < 100ms | 76ms |
| Throughput | 1000 qps | 1200 qps |

### 7.2 Scalability Targets

**Vertical Scaling (Per Instance):**
- Memory: 8-16 GB RAM
- CPU: 4-8 cores
- Storage: 100 GB SSD
- GPU: Optional (Ollama can use CPU efficiently with quantization)

**Horizontal Scaling:**
- Stateless services: Auto-scale 2-20 pods
- Vector DB: Sharded across 3-5 nodes
- PostgreSQL: Read replicas (1 primary + 2-3 replicas)
- Redis: Sentinel mode (1 master + 2 replicas)

**Capacity Planning:**

| Users | Memory Items | Storage | Instances |
|-------|--------------|---------|-----------|
| 1,000 | 1M | 500 GB | 3 pods |
| 10,000 | 10M | 5 TB | 10 pods |
| 100,000 | 100M | 50 TB | 30 pods |

### 7.3 Caching Strategy

**L1: Application Cache (In-Memory)**
- Recent queries: TTL 5 min
- User profiles: TTL 1 hour
- CRS config: TTL 1 hour

**L2: Redis Cache**
- Rehydration results: TTL 5 min
- Vector search results: TTL 10 min
- Embeddings: TTL 1 hour

**L3: Database Query Cache**
- PostgreSQL prepared statements
- PgBouncer connection pooling

**Cache Invalidation:**
- On memory item update: Clear related caches
- On user profile update: Clear user-specific caches
- On consolidation: Clear tier-specific caches

### 7.4 Database Optimization

**Indexing Strategy:**
```sql
-- Critical indexes
CREATE INDEX CONCURRENTLY idx_memory_items_user_tier_crs 
  ON memory_items(user_id, tier, crs DESC) 
  WHERE NOT archived;

CREATE INDEX CONCURRENTLY idx_memory_items_topic_last_used 
  ON memory_items(topic_id, last_used_at DESC) 
  WHERE NOT archived;

-- Partial indexes for hot queries
CREATE INDEX CONCURRENTLY idx_memory_items_high_crs 
  ON memory_items(user_id, crs DESC) 
  WHERE crs >= 0.7 AND NOT archived;
```

**Query Optimization:**
- Use `EXPLAIN ANALYZE` for all critical queries
- Avoid `SELECT *`, specify columns
- Use prepared statements
- Batch inserts with `COPY` or multi-row `INSERT`

**Connection Pooling:**
- PgBouncer in transaction mode
- Pool size: 20-50 connections per instance
- Max client connections: 1000

---

## 8. Deployment Architecture

### 8.1 Kubernetes Deployment

**Namespace Structure:**
```
acms-dev/
acms-staging/
acms-production/
```

**Deployment Diagram:**
```
┌─────────────────────────────────────────────────────────────┐
│                     Ingress (NGINX)                         │
│                 TLS Termination, Routing                    │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐       ┌────────▼────────┐
│ API Service    │       │ Admin Service   │
│ (acms-api)     │       │ (acms-admin)    │
│ Replicas: 3-10 │       │ Replicas: 1-2   │
└───────┬────────┘       └─────────────────┘
        │
        ├──────────────────┬──────────────────┬───────────────┐
        │                  │                  │               │
┌───────▼────────┐ ┌──────▼──────┐ ┌─────────▼────────┐ ┌───▼─────┐
│ PostgreSQL     │ │ Weaviate    │ │ Redis            │ │ Ollama  │
│ StatefulSet    │ │ StatefulSet │ │ StatefulSet      │ │ DaemonSet│
│ Replicas: 3    │ │ Replicas: 3 │ │ Replicas: 3      │ │ (GPU)   │
└────────────────┘ └─────────────┘ └──────────────────┘ └─────────┘
```

### 8.2 Deployment Manifests

**API Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: acms-api
  namespace: acms-production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: acms-api
  template:
    metadata:
      labels:
        app: acms-api
    spec:
      containers:
      - name: api
        image: acms/api:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: acms-secrets
              key: database-url
        - name: REDIS_URL
          value: redis://acms-redis:6379
        - name: WEAVIATE_URL
          value: http://acms-weaviate:8080
        - name: OLLAMA_URL
          value: http://acms-ollama:11434
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: acms-api
  namespace: acms-production
spec:
  selector:
    app: acms-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

**PostgreSQL StatefulSet:**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: acms-postgres
  namespace: acms-production
spec:
  serviceName: acms-postgres
  replicas: 3
  selector:
    matchLabels:
      app: acms-postgres
  template:
    metadata:
      labels:
        app: acms-postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: acms
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: acms-secrets
              key: postgres-user
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: acms-secrets
              key: postgres-password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 100Gi
```

### 8.3 Helm Chart Structure

```
acms-helm/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-staging.yaml
├── values-production.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    ├── secrets.yaml
    ├── statefulset-postgres.yaml
    ├── statefulset-weaviate.yaml
    ├── statefulset-redis.yaml
    ├── cronjob-consolidation.yaml
    └── hpa.yaml
```

**values.yaml:**
```yaml
replicaCount: 3

image:
  repository: acms/api
  tag: "1.0.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.acms.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: acms-tls
      hosts:
        - api.acms.example.com

resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

postgresql:
  enabled: true
  auth:
    username: acms
    password: "secret"
    database: acms
  primary:
    resources:
      requests:
        memory: "4Gi"
        cpu: "2000m"
  readReplicas:
    replicaCount: 2
    resources:
      requests:
        memory: "4Gi"
        cpu: "1000m"

redis:
  enabled: true
  auth:
    enabled: true
    password: "secret"
  master:
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
  replica:
    replicaCount: 2
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"

weaviate:
  enabled: true
  replicas: 3
  resources:
    requests:
      memory: "4Gi"
      cpu: "2000m"

ollama:
  enabled: true
  models:
    - llama3.1:8b
  gpu:
    enabled: false  # Enable for GPU nodes
  resources:
    requests:
      memory: "4Gi"
      cpu: "2000m"
```

### 8.4 CI/CD Pipeline

**GitLab CI / GitHub Actions:**

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

variables:
  IMAGE_NAME: acms/api
  HELM_CHART: acms-helm

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=acms tests/
    - coverage report --fail-under=80
  coverage: '/TOTAL.*\s+(\d+%)$/'

build:
  stage: build
  image: docker:24
  services:
    - docker:dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $IMAGE_NAME:$CI_COMMIT_SHA .
    - docker tag $IMAGE_NAME:$CI_COMMIT_SHA $IMAGE_NAME:latest
    - docker push $IMAGE_NAME:$CI_COMMIT_SHA
    - docker push $IMAGE_NAME:latest
  only:
    - main
    - develop

deploy-dev:
  stage: deploy
  image: alpine/helm:3.12
  script:
    - helm upgrade --install acms $HELM_CHART 
        --namespace acms-dev 
        --values values-dev.yaml 
        --set image.tag=$CI_COMMIT_SHA
  only:
    - develop
  environment:
    name: development
    url: https://dev.acms.example.com

deploy-staging:
  stage: deploy
  image: alpine/helm:3.12
  script:
    - helm upgrade --install acms $HELM_CHART 
        --namespace acms-staging 
        --values values-staging.yaml 
        --set image.tag=$CI_COMMIT_SHA
  only:
    - main
  environment:
    name: staging
    url: https://staging.acms.example.com

deploy-production:
  stage: deploy
  image: alpine/helm:3.12
  script:
    - helm upgrade --install acms $HELM_CHART 
        --namespace acms-production 
        --values values-production.yaml 
        --set image.tag=$CI_COMMIT_SHA
  only:
    - main
  when: manual
  environment:
    name: production
    url: https://api.acms.example.com
```

---

## 9. Monitoring & Observability

### 9.1 Metrics

**Prometheus Metrics:**

```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    'acms_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'acms_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

# Business metrics
queries_processed = Counter(
    'acms_queries_processed_total',
    'Total queries processed',
    ['intent', 'model']
)

token_usage = Histogram(
    'acms_tokens_used',
    'Tokens used per query',
    ['model'],
    buckets=[100, 500, 1000, 2000, 5000, 10000]
)

token_savings = Histogram(
    'acms_token_savings_percent',
    'Token savings percentage',
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80]
)

# Memory metrics
memory_items_total = Gauge(
    'acms_memory_items_total',
    'Total memory items',
    ['user_id', 'tier']
)

crs_distribution = Histogram(
    'acms_crs_score',
    'CRS score distribution',
    ['tier'],
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

# Performance metrics
rehydration_duration = Histogram(
    'acms_rehydration_duration_seconds',
    'Rehydration duration',
    ['intent']
)

vector_search_duration = Histogram(
    'acms_vector_search_duration_seconds',
    'Vector search duration'
)

# Infrastructure metrics
db_connection_pool_size = Gauge(
    'acms_db_connection_pool_size',
    'Database connection pool size',
    ['pool']
)

cache_hit_ratio = Gauge(
    'acms_cache_hit_ratio',
    'Cache hit ratio',
    ['cache_type']
)
```

### 9.2 Logging

**Structured Logging (JSON):**

```python
import structlog

logger = structlog.get_logger()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Usage
logger.info(
    "query_processed",
    query_id="uuid",
    user_id="uuid",
    intent="research",
    rehydration_time_ms=347,
    tokens_used=1847,
    memory_items_used=8
)
```

**Log Levels:**
- **ERROR**: System errors, exceptions
- **WARN**: Degraded performance, fallbacks triggered
- **INFO**: Business events (queries, tier transitions)
- **DEBUG**: Detailed execution traces (dev/staging only)

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- OR Loki + Grafana
- Retention: 30 days (INFO+), 7 days (DEBUG)

### 9.3 Distributed Tracing

**OpenTelemetry Configuration:**

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracer
tracer_provider = TracerProvider()
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent",
    agent_port=6831,
)
tracer_provider.add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)
trace.set_tracer_provider(tracer_provider)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Custom spans
tracer = trace.get_tracer(__name__)

async def rehydrate(query: str, user_id: str):
    with tracer.start_as_current_span("rehydration"):
        with tracer.start_as_current_span("intent_classification"):
            intent = await classify_intent(query)
        
        with tracer.start_as_current_span("vector_search"):
            candidates = await vector_search(query, user_id)
        
        with tracer.start_as_current_span("ranking"):
            ranked = await rank_candidates(candidates)
        
        with tracer.start_as_current_span("summarization"):
            bundle = await summarize(ranked)
        
        return bundle
```

### 9.4 Alerting

**Alert Rules (Prometheus):**

```yaml
groups:
- name: acms_alerts
  interval: 30s
  rules:
  
  # High error rate
  - alert: HighErrorRate
    expr: |
      rate(acms_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }}"
  
  # Slow queries
  - alert: SlowQueries
    expr: |
      histogram_quantile(0.95, 
        rate(acms_request_duration_seconds_bucket[5m])
      ) > 5.0
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Slow queries detected"
      description: "P95 latency is {{ $value }}s"
  
  # Database connection pool exhaustion
  - alert: DBConnectionPoolExhausted
    expr: |
      acms_db_connection_pool_size / 
      acms_db_connection_pool_max > 0.9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Database connection pool nearly exhausted"
  
  # Memory item explosion
  - alert: MemoryItemsGrowthAnomaly
    expr: |
      rate(acms_memory_items_total[1h]) > 1000
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: "Unusually high memory item growth"
  
  # Token savings below target
  - alert: LowTokenSavings
    expr: |
      avg_over_time(acms_token_savings_percent[6h]) < 20
    for: 6h
    labels:
      severity: info
    annotations:
      summary: "Token savings below 20% target"
```

**Alert Channels:**
- PagerDuty (critical)
- Slack (warning, info)
- Email (all)

---

## 10. Disaster Recovery & Business Continuity

### 10.1 Backup Strategy

**PostgreSQL Backups:**
- **Full backup**: Daily at 2 AM UTC
- **Incremental backup**: Every 6 hours
- **WAL archiving**: Continuous
- **Retention**: 30 days
- **Storage**: S3 (or compatible) with versioning

```bash
# Backup script (cron)
#!/bin/bash
BACKUP_FILE="acms_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
pg_dump -h postgres -U acms acms | gzip > /backups/$BACKUP_FILE
aws s3 cp /backups/$BACKUP_FILE s3://acms-backups/postgres/
# Retain only last 30 days
find /backups -name "acms_backup_*" -mtime +30 -delete
```

**Redis Backups:**
- **RDB snapshot**: Every 6 hours
- **AOF**: Enabled (fsync every second)
- **Retention**: 7 days

**Weaviate Backups:**
- **Snapshot**: Daily
- **Retention**: 14 days

### 10.2 Disaster Recovery Plan

**RPO (Recovery Point Objective):** 1 hour  
**RTO (Recovery Time Objective):** 4 hours

**DR Procedures:**

**Scenario 1: Database Failure**
1. Detect failure via health checks (< 1 min)
2. Fail over to read replica (automatic, < 30 seconds)
3. Promote replica to primary (< 5 min)
4. Update application config (< 2 min)
5. Resume operations (< 10 min total)

**Scenario 2: Complete Data Center Loss**
1. Detect regional outage (< 5 min)
2. Initiate DR runbook
3. Restore latest backup to DR region (< 2 hours)
4. Update DNS to DR region (< 5 min propagation)
5. Resume operations (< 3 hours total)

**Scenario 3: Data Corruption**
1. Identify corruption extent (< 30 min)
2. Restore from point-in-time backup (< 2 hours)
3. Replay WAL logs to minimize data loss (< 1 hour)
4. Validate data integrity (< 30 min)
5. Resume operations (< 4 hours total)

### 10.3 Testing

**DR Test Schedule:**
- **Quarterly**: Full DR failover test
- **Monthly**: Backup restore test
- **Weekly**: Health check validation

**Test Checklist:**
- [ ] Restore latest backup to DR environment
- [ ] Verify all services start successfully
- [ ] Run smoke tests (API, database, vector search)
- [ ] Validate data integrity (checksums, row counts)
- [ ] Measure RTO (time to restore)
- [ ] Document issues and update runbook

---

## 11. Appendices

### Appendix A: Technology Alternatives

| Component | Primary Choice | Alternatives Considered | Decision Rationale |
|-----------|----------------|-------------------------|-------------------|
| Vector DB | Weaviate / pgvector | Qdrant, Milvus, Pinecone | Weaviate for features/scale, pgvector for simplicity |
| RDBMS | PostgreSQL | MySQL, CockroachDB | Maturity, pgvector extension, JSONB support |
| Cache | Redis | Memcached, Hazelcast | Persistence, data structures, maturity |
| LLM Runtime | Ollama | vLLM, llama.cpp | Ease of use, model management, active development |
| Embedding | nomic-embed-text | OpenAI, Cohere | Quality, open-source, licensable |

### Appendix B: Glossary

- **ACMS**: Adaptive Context Memory System
- **CRS**: Context Retention Score
- **DEK**: Data Encryption Key
- **KEK**: Key Encryption Key
- **HNSW**: Hierarchical Navigable Small World (vector index algorithm)
- **PII**: Personally Identifiable Information
- **RAG**: Retrieval-Augmented Generation
- **TPM**: Trusted Platform Module
- **WAL**: Write-Ahead Log (PostgreSQL)

### Appendix C: References

1. MemGPT Paper: https://arxiv.org/abs/2310.08560
2. pgvector Documentation: https://github.com/pgvector/pgvector
3. HNSW Algorithm: https://arxiv.org/abs/1603.09320
4. Ollama Documentation: https://github.com/ollama/ollama
5. XChaCha20-Poly1305 Spec: RFC 8439
6. GDPR Article 20 (Right to Data Portability): https://gdpr-info.eu/art-20-gdpr/
7. HIPAA Security Rule: https://www.hhs.gov/hipaa/for-professionals/security/

---

**END OF TECHNICAL ARCHITECTURE DOCUMENT**

*This document is a living artifact and will be updated as the system evolves.*

**Next Review Date:** Monthly during development, Quarterly post-launch

**Document Maintainers:**
- Engineering Lead: [Name]
- Solutions Architect: [Name]
- Security Engineer: [Name]
