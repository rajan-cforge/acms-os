# ACMS: Universal Context API - Complete Build Plan for Claude Code

**Version**: 2.0 (Context Bridge Focus)  
**Build Time**: 68 hours (7 phases × ~10 hours)  
**Approach**: Test-Driven Development (TDD)  
**Goal**: Self-published API-first product for enterprises  

---

## 🎯 **VISION STATEMENT**

**ACMS is the universal memory API that connects all AI tools in an enterprise.**

```
     ChatGPT  ←→  ┌─────────────┐  ←→  Claude
                  │             │
     Cursor   ←→  │    ACMS     │  ←→  Claude Code
                  │  Universal  │
     Glean    ←→  │  Context    │  ←→  Copilot
                  │     API     │
     Custom   ←→  └─────────────┘  ←→  Any AI Tool
```

**Value Proposition:**  
> "One memory layer for all your AI tools. Every tool sees the same context, learns from every interaction, never asks you to repeat yourself."

**Not:**
- ❌ Another AI assistant
- ❌ Another RAG system  
- ❌ Another chatbot

**Instead:**
- ✅ The context fabric beneath all AI tools
- ✅ The memory API every AI tool connects to
- ✅ The universal translator for AI context

---

## 📊 **ARCHITECTURE OVERVIEW**

### **System Layers**

```
┌────────────────────────────────────────────────────────┐
│  AI Tool Layer (Connectors)                            │
│  ChatGPT │ Claude │ Cursor │ Glean │ Copilot │ Custom │
└────────────────────────────────────────────────────────┘
                         ↕ REST API
┌────────────────────────────────────────────────────────┐
│  Universal Context API (Phase 4)                       │
│  • POST /context/store                                 │
│  • POST /context/retrieve                              │
│  • GET  /context/history                               │
│  • POST /context/feedback (outcome learning)           │
└────────────────────────────────────────────────────────┘
                         ↕
┌────────────────────────────────────────────────────────┐
│  Core Memory Engine (Phase 3)                          │
│  • Context Retrieval System (CRS)                      │
│  • Memory Ingestion Pipeline                           │
│  • Tier Management (Hot/Warm/Cold/Archived)           │
└────────────────────────────────────────────────────────┘
                         ↕
┌────────────────────────────────────────────────────────┐
│  Storage Layer (Phase 2)                               │
│  • PostgreSQL (structured data + pgvector)             │
│  • Weaviate (vector search)                            │
│  • Redis (caching)                                     │
│  • Encryption (XChaCha20-Poly1305)                     │
└────────────────────────────────────────────────────────┘
                         ↕
┌────────────────────────────────────────────────────────┐
│  Infrastructure (Phase 1) ✅ DONE                      │
│  • Docker Compose (PostgreSQL, Redis, Ollama)          │
│  • Weaviate (existing instance, port 8080)             │
│  • Health checks                                       │
└────────────────────────────────────────────────────────┘
```

---

## 🗓️ **PHASE-BY-PHASE PLAN**

### **Phase 0: Bootstrap Memory System** ✅ COMPLETE
- **Duration**: 2 hours (Hour 0-2)
- **Status**: DONE
- **Deliverables**: ACMS-Lite (SQLite CLI), 48 memories stored, checkpoint 0 passed

---

### **Phase 1: Infrastructure Setup** ✅ COMPLETE
- **Duration**: 6 hours (Hour 2-8)
- **Status**: DONE
- **Deliverables**: 
  - Docker Compose (PostgreSQL 40432, Redis 40379, Ollama 40434)
  - Weaviate (existing, port 8080)
  - Ollama models (all-minilm:22m, llama3.2:1b)
  - Health checks passing

---

### **Phase 2: Storage Layer** 🎯 NEXT
- **Duration**: 10 hours (Hour 8-18)
- **Objective**: Database schemas, encryption, Weaviate integration

#### **Deliverables:**

**1. PostgreSQL Schema (schema/01_base_schema.sql)**
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Topics (memory partitions per user)
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Memory items
CREATE TABLE memory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) UNIQUE, -- SHA256 for deduplication
    encrypted_content BYTEA, -- XChaCha20-Poly1305 encrypted
    source VARCHAR(50) NOT NULL, -- 'chatgpt', 'claude', 'cursor', etc.
    tier VARCHAR(20) DEFAULT 'hot', -- hot, warm, cold, archived
    embedding_id VARCHAR(100), -- Weaviate UUID
    metadata JSONB, -- Flexible metadata
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INT DEFAULT 0,
    
    -- CRS components
    similarity_score FLOAT DEFAULT 0.0,
    recurrence_score FLOAT DEFAULT 0.0,
    outcome_score FLOAT DEFAULT 0.0,
    correction_score FLOAT DEFAULT 0.0,
    recency_score FLOAT DEFAULT 0.0,
    hybrid_score FLOAT DEFAULT 0.0,
    
    INDEX idx_user_topic (user_id, topic_id),
    INDEX idx_tier (tier),
    INDEX idx_hybrid_score (hybrid_score DESC),
    INDEX idx_source (source)
);

-- Context retrieval logs
CREATE TABLE context_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    source VARCHAR(50) NOT NULL, -- Which AI tool requested context
    memories_returned INT,
    token_count INT,
    retrieval_latency_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Outcome feedback
CREATE TABLE outcome_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID REFERENCES memory_items(id) ON DELETE CASCADE,
    context_log_id UUID REFERENCES context_logs(id) ON DELETE CASCADE,
    feedback_type VARCHAR(20), -- 'helpful', 'not_helpful', 'irrelevant'
    created_at TIMESTAMP DEFAULT NOW()
);
```

**2. Alembic Migrations Setup**
```bash
# Install Alembic
pip install alembic psycopg2-binary

# Initialize Alembic
alembic init migrations

# Create first migration
alembic revision -m "initial_schema"

# Apply migrations
alembic upgrade head
```

**3. Weaviate Collection Setup (weaviate/setup_collection.py)**
```python
import weaviate
from weaviate.classes.config import Configure, Property, DataType

def setup_acms_collection():
    """
    Create ACMS_Memories collection in Weaviate
    - 384 dimensions (all-minilm:22m)
    - HNSW index for fast similarity search
    """
    client = weaviate.connect_to_local(
        host="localhost",
        port=8080,
        grpc_port=50051
    )
    
    # Check if collection exists
    if client.collections.exists("ACMS_Memories"):
        print("Collection ACMS_Memories already exists")
        return
    
    # Create collection
    client.collections.create(
        name="ACMS_Memories",
        description="Universal context memory for all AI tools",
        vectorizer_config=Configure.Vectorizer.none(),  # We provide embeddings
        properties=[
            Property(
                name="memory_id",
                data_type=DataType.TEXT,
                description="PostgreSQL memory_item UUID"
            ),
            Property(
                name="user_id",
                data_type=DataType.TEXT,
                description="User UUID"
            ),
            Property(
                name="topic_id",
                data_type=DataType.TEXT,
                description="Topic UUID"
            ),
            Property(
                name="content",
                data_type=DataType.TEXT,
                description="Memory content"
            ),
            Property(
                name="source",
                data_type=DataType.TEXT,
                description="AI tool source (chatgpt, claude, etc.)"
            ),
            Property(
                name="tier",
                data_type=DataType.TEXT,
                description="Memory tier (hot, warm, cold, archived)"
            ),
            Property(
                name="created_at",
                data_type=DataType.DATE,
                description="Creation timestamp"
            )
        ],
        vector_index_config=Configure.VectorIndex.hnsw(
            distance_metric="cosine",
            ef_construction=128,
            ef=64,
            max_connections=32
        )
    )
    
    print("✅ Collection ACMS_Memories created")
    client.close()

if __name__ == "__main__":
    setup_acms_collection()
```

**4. Encryption Manager (crypto/encryption.py)**
```python
import os
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import base64

class EncryptionManager:
    """
    XChaCha20-Poly1305 AEAD encryption for memory content
    Key derivation: HKDF-SHA256
    """
    def __init__(self, master_key: bytes = None):
        if master_key is None:
            # Generate random 32-byte key
            master_key = os.urandom(32)
        
        self.master_key = master_key
    
    def derive_key(self, context: str = "memory_content") -> bytes:
        """Derive encryption key from master key + context"""
        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=context.encode()
        )
        return kdf.derive(self.master_key)
    
    def encrypt(self, plaintext: str, context: str = "memory_content") -> bytes:
        """Encrypt plaintext using ChaCha20-Poly1305"""
        key = self.derive_key(context)
        cipher = ChaCha20Poly1305(key)
        nonce = os.urandom(24)  # XChaCha20 uses 24-byte nonce
        ciphertext = cipher.encrypt(nonce, plaintext.encode(), None)
        return nonce + ciphertext  # Prepend nonce
    
    def decrypt(self, ciphertext: bytes, context: str = "memory_content") -> str:
        """Decrypt ciphertext using ChaCha20-Poly1305"""
        key = self.derive_key(context)
        cipher = ChaCha20Poly1305(key)
        nonce = ciphertext[:24]
        encrypted_data = ciphertext[24:]
        plaintext = cipher.decrypt(nonce, encrypted_data, None)
        return plaintext.decode()
    
    @staticmethod
    def generate_master_key() -> bytes:
        """Generate new master key"""
        return os.urandom(32)
    
    @staticmethod
    def save_key(key: bytes, filepath: str = ".acms_master.key"):
        """Save master key to file (SECURE THIS!)"""
        with open(filepath, 'wb') as f:
            f.write(key)
        os.chmod(filepath, 0o600)  # Read/write for owner only
    
    @staticmethod
    def load_key(filepath: str = ".acms_master.key") -> bytes:
        """Load master key from file"""
        with open(filepath, 'rb') as f:
            return f.read()
```

**5. Memory Storage Module (storage/memory_store.py)**
```python
import hashlib
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from crypto.encryption import EncryptionManager

class MemoryStore:
    """PostgreSQL memory storage with encryption"""
    
    def __init__(self, db_config: dict, encryption_manager: EncryptionManager):
        self.db_config = db_config
        self.encryption = encryption_manager
        self.conn = None
    
    def connect(self):
        """Connect to PostgreSQL"""
        self.conn = psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            cursor_factory=RealDictCursor
        )
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def store_memory(
        self, 
        user_id: UUID, 
        topic_id: UUID, 
        content: str,
        source: str,
        metadata: dict = None
    ) -> UUID:
        """
        Store memory item with encryption
        Returns: memory_id
        """
        # Check for duplicates via content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        cursor = self.conn.cursor()
        
        # Check if already exists
        cursor.execute(
            "SELECT id FROM memory_items WHERE content_hash = %s",
            (content_hash,)
        )
        existing = cursor.fetchone()
        if existing:
            print(f"⚠️  Memory already exists: {existing['id']}")
            return existing['id']
        
        # Encrypt content
        encrypted_content = self.encryption.encrypt(content)
        
        # Insert memory
        memory_id = uuid4()
        cursor.execute("""
            INSERT INTO memory_items 
            (id, user_id, topic_id, content, content_hash, encrypted_content, 
             source, tier, metadata, created_at, last_accessed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            memory_id, user_id, topic_id, content, content_hash, 
            encrypted_content, source, 'hot', metadata, 
            datetime.now(), datetime.now()
        ))
        
        self.conn.commit()
        print(f"✅ Memory stored: {memory_id}")
        return memory_id
    
    def get_memory(self, memory_id: UUID, decrypt: bool = True) -> dict:
        """Retrieve memory by ID"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM memory_items WHERE id = %s",
            (memory_id,)
        )
        memory = cursor.fetchone()
        
        if memory and decrypt and memory['encrypted_content']:
            memory['content'] = self.encryption.decrypt(memory['encrypted_content'])
        
        return dict(memory) if memory else None
    
    def update_access(self, memory_id: UUID):
        """Update last_accessed and increment access_count"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE memory_items 
            SET last_accessed = %s, access_count = access_count + 1
            WHERE id = %s
        """, (datetime.now(), memory_id))
        self.conn.commit()
    
    def list_memories(
        self, 
        user_id: UUID, 
        topic_id: Optional[UUID] = None,
        tier: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """List memories with filters"""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM memory_items WHERE user_id = %s"
        params = [user_id]
        
        if topic_id:
            query += " AND topic_id = %s"
            params.append(topic_id)
        
        if tier:
            query += " AND tier = %s"
            params.append(tier)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
```

#### **Testing Strategy (Phase 2):**

**Unit Tests:**
```python
# tests/unit/test_encryption.py
def test_encrypt_decrypt():
    em = EncryptionManager()
    plaintext = "This is a secret memory"
    ciphertext = em.encrypt(plaintext)
    assert em.decrypt(ciphertext) == plaintext

def test_different_contexts_different_keys():
    em = EncryptionManager()
    key1 = em.derive_key("context1")
    key2 = em.derive_key("context2")
    assert key1 != key2

# tests/unit/test_memory_store.py
def test_store_and_retrieve_memory():
    store = MemoryStore(db_config, encryption_manager)
    memory_id = store.store_memory(
        user_id=uuid4(),
        topic_id=uuid4(),
        content="Test memory",
        source="test"
    )
    memory = store.get_memory(memory_id)
    assert memory['content'] == "Test memory"

def test_duplicate_prevention():
    # Storing same content twice should return same ID
    content = "Duplicate test"
    id1 = store.store_memory(user_id, topic_id, content, "test")
    id2 = store.store_memory(user_id, topic_id, content, "test")
    assert id1 == id2
```

**Integration Tests:**
```python
# tests/integration/test_weaviate_integration.py
def test_store_memory_with_embedding():
    # Test full pipeline: PostgreSQL + Weaviate
    memory_id = store.store_memory(...)
    # Generate embedding
    embedding = generate_embedding(content)
    # Store in Weaviate
    weaviate_client.store_vector(memory_id, embedding)
    # Verify retrieval
    results = weaviate_client.search(query_embedding, limit=1)
    assert results[0]['memory_id'] == str(memory_id)
```

**Checkpoint 2 Criteria:**
- ✅ All migrations applied
- ✅ User CRUD operations working
- ✅ Memory storage/retrieval working
- ✅ Encryption functional (encrypt → decrypt returns original)
- ✅ Weaviate collection created
- ✅ Vector search working
- ✅ Test coverage > 85%
- ✅ Performance: < 50ms for memory storage, < 100ms for retrieval

---

### **Phase 3: Core Memory Engine**
- **Duration**: 10 hours (Hour 18-28)
- **Objective**: Context Retrieval System (CRS), memory ingestion, tiering

#### **Deliverables:**

**1. Embedding Generator (embeddings/generator.py)**
```python
import ollama
from typing import List

class EmbeddingGenerator:
    """Generate embeddings using Ollama all-minilm:22m"""
    
    def __init__(self, model: str = "all-minilm:22m", host: str = "http://localhost:40434"):
        self.model = model
        self.host = host
    
    def generate(self, text: str) -> List[float]:
        """Generate 384-dim embedding for text"""
        response = ollama.embed(
            model=self.model,
            input=text,
            options={"host": self.host}
        )
        return response['embeddings'][0]
    
    def batch_generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return [self.generate(text) for text in texts]
```

**2. Context Retrieval System (crs/hybrid_scorer.py)**
```python
import math
from datetime import datetime, timedelta
from typing import List, Dict

class ContextRetrievalSystem:
    """
    Hybrid scoring system for memory retrieval
    Formula: CRS = w1·sim + w2·rec + w3·out + w4·cor + w5·rcy
    """
    
    def __init__(
        self,
        w_similarity: float = 0.35,
        w_recurrence: float = 0.20,
        w_outcome: float = 0.25,
        w_correction: float = 0.10,
        w_recency: float = 0.10,
        decay_rate: float = 0.05  # λ = 0.05 per day
    ):
        self.weights = {
            'similarity': w_similarity,
            'recurrence': w_recurrence,
            'outcome': w_outcome,
            'correction': w_correction,
            'recency': w_recency
        }
        self.decay_rate = decay_rate
        
        # Validate weights sum to 1.0
        total = sum(self.weights.values())
        assert abs(total - 1.0) < 0.01, f"Weights must sum to 1.0, got {total}"
    
    def calculate_similarity(self, cosine_distance: float) -> float:
        """
        Similarity score from cosine distance
        Range: [0, 1], higher = more similar
        """
        return (1.0 + cosine_distance) / 2.0  # Convert from [-1,1] to [0,1]
    
    def calculate_recurrence(self, access_count: int, max_access: int = 100) -> float:
        """
        Recurrence score based on access frequency
        Formula: rec = log(1 + access_count) / log(1 + max_access)
        """
        if max_access == 0:
            return 0.0
        return math.log(1 + access_count) / math.log(1 + max_access)
    
    def calculate_outcome(self, helpful_count: int, total_feedback: int) -> float:
        """
        Outcome score based on feedback
        Formula: out = helpful / (total + smoothing)
        """
        smoothing = 2  # Laplace smoothing
        return (helpful_count + 1) / (total_feedback + smoothing)
    
    def calculate_correction(self, correction_count: int, max_corrections: int = 10) -> float:
        """
        Correction score (number of times user corrected based on this memory)
        Higher = more valuable as reference
        """
        return min(correction_count / max_corrections, 1.0)
    
    def calculate_recency(self, created_at: datetime, last_accessed: datetime) -> float:
        """
        Recency score with exponential decay
        Formula: rcy = exp(-λ * days_since_last_access)
        """
        days_since_access = (datetime.now() - last_accessed).days
        return math.exp(-self.decay_rate * days_since_access)
    
    def calculate_hybrid_score(self, memory: Dict) -> float:
        """
        Calculate CRS hybrid score
        Returns: float in [0, 1]
        """
        scores = {
            'similarity': self.calculate_similarity(memory.get('cosine_distance', 0.0)),
            'recurrence': self.calculate_recurrence(memory.get('access_count', 0)),
            'outcome': self.calculate_outcome(
                memory.get('helpful_count', 0),
                memory.get('total_feedback', 0)
            ),
            'correction': self.calculate_correction(memory.get('correction_count', 0)),
            'recency': self.calculate_recency(
                memory['created_at'],
                memory.get('last_accessed', memory['created_at'])
            )
        }
        
        # Weighted sum
        hybrid_score = sum(
            self.weights[component] * scores[component]
            for component in scores
        )
        
        return hybrid_score
    
    def rank_memories(self, memories: List[Dict]) -> List[Dict]:
        """
        Rank memories by CRS hybrid score
        Returns: Sorted list (highest score first)
        """
        for memory in memories:
            memory['hybrid_score'] = self.calculate_hybrid_score(memory)
        
        return sorted(memories, key=lambda m: m['hybrid_score'], reverse=True)
```

**3. Memory Ingestion Pipeline (ingestion/pipeline.py)**
```python
from embeddings.generator import EmbeddingGenerator
from storage.memory_store import MemoryStore
from storage.weaviate_client import WeaviateClient
from uuid import UUID
from typing import Dict

class IngestionPipeline:
    """
    Memory ingestion: text → embedding → PostgreSQL + Weaviate
    """
    
    def __init__(
        self, 
        memory_store: MemoryStore,
        weaviate_client: WeaviateClient,
        embedding_generator: EmbeddingGenerator
    ):
        self.memory_store = memory_store
        self.weaviate = weaviate_client
        self.embedder = embedding_generator
    
    def ingest(
        self,
        user_id: UUID,
        topic_id: UUID,
        content: str,
        source: str,  # 'chatgpt', 'claude', 'cursor', etc.
        metadata: Dict = None
    ) -> UUID:
        """
        Ingest new memory:
        1. Store in PostgreSQL (encrypted)
        2. Generate embedding
        3. Store embedding in Weaviate
        4. Return memory_id
        """
        # Step 1: Store in PostgreSQL
        memory_id = self.memory_store.store_memory(
            user_id=user_id,
            topic_id=topic_id,
            content=content,
            source=source,
            metadata=metadata
        )
        
        # Step 2: Generate embedding
        embedding = self.embedder.generate(content)
        
        # Step 3: Store in Weaviate
        weaviate_id = self.weaviate.store_vector(
            memory_id=memory_id,
            user_id=user_id,
            topic_id=topic_id,
            content=content,
            source=source,
            embedding=embedding
        )
        
        # Update PostgreSQL with weaviate_id
        self.memory_store.update_embedding_id(memory_id, weaviate_id)
        
        print(f"✅ Ingested memory {memory_id} with embedding {weaviate_id}")
        return memory_id
    
    def batch_ingest(self, memories: List[Dict]) -> List[UUID]:
        """Ingest multiple memories efficiently"""
        memory_ids = []
        for mem in memories:
            memory_id = self.ingest(
                user_id=mem['user_id'],
                topic_id=mem['topic_id'],
                content=mem['content'],
                source=mem['source'],
                metadata=mem.get('metadata')
            )
            memory_ids.append(memory_id)
        return memory_ids
```

**4. Memory Tier Manager (tiers/manager.py)**
```python
from datetime import datetime, timedelta
from typing import List
from storage.memory_store import MemoryStore

class TierManager:
    """
    Manage memory tiers: hot → warm → cold → archived
    Based on access patterns and CRS scores
    """
    
    TIER_THRESHOLDS = {
        'hot': {'min_access': 5, 'min_score': 0.7, 'days': 7},
        'warm': {'min_access': 2, 'min_score': 0.5, 'days': 30},
        'cold': {'min_access': 0, 'min_score': 0.3, 'days': 90},
        'archived': {'days': 180}  # Everything older
    }
    
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
    
    def promote_to_hot(self, memory_id: UUID):
        """Promote memory to hot tier (frequently accessed)"""
        self.memory_store.update_tier(memory_id, 'hot')
    
    def demote_to_warm(self, memory_id: UUID):
        """Demote memory to warm tier (occasionally accessed)"""
        self.memory_store.update_tier(memory_id, 'warm')
    
    def archive_memory(self, memory_id: UUID):
        """Archive old, low-value memory"""
        self.memory_store.update_tier(memory_id, 'archived')
    
    def rebalance_tiers(self, user_id: UUID):
        """
        Rebalance all memories based on access patterns
        Run daily as background job
        """
        memories = self.memory_store.list_all_memories(user_id)
        
        for memory in memories:
            days_old = (datetime.now() - memory['created_at']).days
            access_count = memory['access_count']
            hybrid_score = memory['hybrid_score']
            
            # Determine new tier
            if (access_count >= self.TIER_THRESHOLDS['hot']['min_access'] and
                hybrid_score >= self.TIER_THRESHOLDS['hot']['min_score']):
                new_tier = 'hot'
            elif (access_count >= self.TIER_THRESHOLDS['warm']['min_access'] and
                  hybrid_score >= self.TIER_THRESHOLDS['warm']['min_score'] and
                  days_old <= self.TIER_THRESHOLDS['warm']['days']):
                new_tier = 'warm'
            elif days_old <= self.TIER_THRESHOLDS['cold']['days']:
                new_tier = 'cold'
            else:
                new_tier = 'archived'
            
            # Update if changed
            if memory['tier'] != new_tier:
                self.memory_store.update_tier(memory['id'], new_tier)
                print(f"🔄 Memory {memory['id']}: {memory['tier']} → {new_tier}")
```

#### **Testing Strategy (Phase 3):**

**Unit Tests:**
```python
# tests/unit/test_crs.py
def test_similarity_score_range():
    crs = ContextRetrievalSystem()
    assert 0.0 <= crs.calculate_similarity(-1.0) <= 1.0
    assert 0.0 <= crs.calculate_similarity(0.0) <= 1.0
    assert 0.0 <= crs.calculate_similarity(1.0) <= 1.0

def test_hybrid_score_calculation():
    memory = {
        'cosine_distance': 0.8,
        'access_count': 10,
        'helpful_count': 5,
        'total_feedback': 6,
        'correction_count': 2,
        'created_at': datetime.now() - timedelta(days=5),
        'last_accessed': datetime.now() - timedelta(days=1)
    }
    score = crs.calculate_hybrid_score(memory)
    assert 0.0 <= score <= 1.0

# tests/unit/test_embeddings.py
def test_embedding_generation():
    gen = EmbeddingGenerator()
    embedding = gen.generate("Test memory content")
    assert len(embedding) == 384  # all-minilm:22m dimension
    assert all(isinstance(x, float) for x in embedding)
```

**Checkpoint 3 Criteria:**
- ✅ CRS formula implemented and tested
- ✅ Embedding generation working (384 dims)
- ✅ Memory ingestion pipeline functional
- ✅ Tier management working (promote/demote)
- ✅ Test coverage > 85%
- ✅ Performance: < 200ms for full ingestion pipeline

---

### **Phase 4: Universal Context API** 🆕 UPDATED
- **Duration**: 12 hours (Hour 28-40)
- **Objective**: RESTful API for any AI tool to store/retrieve context

#### **Key Change from Original Plan:**
**OLD**: LLM integration + rehydration for single assistant  
**NEW**: Universal API that ANY tool can connect to

#### **Deliverables:**

**1. API Server (api/server.py)**
```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, UUID4
from typing import List, Optional
from uuid import UUID
import uvicorn

from storage.memory_store import MemoryStore
from storage.weaviate_client import WeaviateClient
from crs.hybrid_scorer import ContextRetrievalSystem
from ingestion.pipeline import IngestionPipeline
from embeddings.generator import EmbeddingGenerator

app = FastAPI(
    title="ACMS Universal Context API",
    description="Memory API for all AI tools",
    version="1.0.0"
)

# CORS for browser extensions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Request/Response Models
class ContextStoreRequest(BaseModel):
    user_id: UUID4
    topic_id: UUID4
    content: str
    source: str  # 'chatgpt', 'claude', 'cursor', etc.
    metadata: Optional[dict] = None

class ContextRetrieveRequest(BaseModel):
    user_id: UUID4
    query: str
    topic_id: Optional[UUID4] = None
    source: str  # Which tool is requesting context
    max_tokens: int = 2000
    min_score: float = 0.5

class ContextRetrieveResponse(BaseModel):
    context: str  # Formatted context for the tool
    memories_used: List[UUID4]
    token_count: int
    retrieval_latency_ms: int

class FeedbackRequest(BaseModel):
    memory_id: UUID4
    context_log_id: UUID4
    feedback_type: str  # 'helpful', 'not_helpful', 'irrelevant'

# API Endpoints
@app.post("/api/v1/context/store", status_code=201)
async def store_context(request: ContextStoreRequest):
    """
    Store new memory item
    Called by AI tools after user interaction
    """
    try:
        memory_id = ingestion_pipeline.ingest(
            user_id=request.user_id,
            topic_id=request.topic_id,
            content=request.content,
            source=request.source,
            metadata=request.metadata
        )
        return {
            "memory_id": memory_id,
            "status": "stored"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/context/retrieve", response_model=ContextRetrieveResponse)
async def retrieve_context(request: ContextRetrieveRequest):
    """
    Retrieve relevant context for a query
    Called by AI tools before generating response
    """
    import time
    start_time = time.time()
    
    try:
        # 1. Generate query embedding
        query_embedding = embedding_generator.generate(request.query)
        
        # 2. Vector search in Weaviate
        vector_results = weaviate_client.search(
            query_embedding=query_embedding,
            user_id=request.user_id,
            topic_id=request.topic_id,
            limit=50  # Get top 50 candidates
        )
        
        # 3. Hybrid scoring with CRS
        ranked_memories = crs.rank_memories(vector_results)
        
        # 4. Select memories within token budget
        selected_memories = []
        total_tokens = 0
        
        for memory in ranked_memories:
            if memory['hybrid_score'] < request.min_score:
                continue
            
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            memory_tokens = len(memory['content']) // 4
            
            if total_tokens + memory_tokens > request.max_tokens:
                break
            
            selected_memories.append(memory)
            total_tokens += memory_tokens
        
        # 5. Format context for specific tool
        formatted_context = format_context_for_tool(
            memories=selected_memories,
            source=request.source
        )
        
        # 6. Log retrieval
        context_log_id = log_context_retrieval(
            user_id=request.user_id,
            query=request.query,
            source=request.source,
            memories_returned=len(selected_memories),
            token_count=total_tokens
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return ContextRetrieveResponse(
            context=formatted_context,
            memories_used=[m['id'] for m in selected_memories],
            token_count=total_tokens,
            retrieval_latency_ms=latency_ms
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/context/feedback")
async def record_feedback(request: FeedbackRequest):
    """
    Record outcome feedback for outcome learning
    Called by AI tools when user gives feedback
    """
    try:
        outcome_store.record_feedback(
            memory_id=request.memory_id,
            context_log_id=request.context_log_id,
            feedback_type=request.feedback_type
        )
        return {"status": "recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "postgres": check_postgres_health(),
            "weaviate": check_weaviate_health(),
            "redis": check_redis_health(),
            "ollama": check_ollama_health()
        }
    }

# Helper Functions
def format_context_for_tool(memories: List[dict], source: str) -> str:
    """
    Format context for specific AI tool
    Different tools may have different preferences
    """
    if source == "chatgpt":
        # ChatGPT format: clear sections
        context = "# Relevant Context\n\n"
        for i, mem in enumerate(memories, 1):
            context += f"## Memory {i}\n{mem['content']}\n\n"
        return context
    
    elif source == "claude":
        # Claude format: XML-style
        context = "<context>\n"
        for mem in memories:
            context += f"<memory>{mem['content']}</memory>\n"
        context += "</context>\n"
        return context
    
    elif source == "cursor":
        # Cursor format: code comments
        context = "// Context from ACMS:\n"
        for mem in memories:
            context += f"// {mem['content']}\n"
        return context
    
    else:
        # Generic format
        return "\n\n".join(mem['content'] for mem in memories)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=40080)
```

**2. API Client Library (sdk/python/acms_client.py)**
```python
import requests
from typing import List, Optional, Dict
from uuid import UUID

class ACMSClient:
    """
    Python client for ACMS Universal Context API
    Use this in AI tool integrations
    """
    
    def __init__(self, base_url: str = "http://localhost:40080"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def store_context(
        self,
        user_id: UUID,
        topic_id: UUID,
        content: str,
        source: str,
        metadata: Optional[Dict] = None
    ) -> UUID:
        """Store new memory"""
        response = self.session.post(
            f"{self.base_url}/api/v1/context/store",
            json={
                "user_id": str(user_id),
                "topic_id": str(topic_id),
                "content": content,
                "source": source,
                "metadata": metadata
            }
        )
        response.raise_for_status()
        return UUID(response.json()["memory_id"])
    
    def retrieve_context(
        self,
        user_id: UUID,
        query: str,
        source: str,
        topic_id: Optional[UUID] = None,
        max_tokens: int = 2000,
        min_score: float = 0.5
    ) -> Dict:
        """Retrieve relevant context"""
        response = self.session.post(
            f"{self.base_url}/api/v1/context/retrieve",
            json={
                "user_id": str(user_id),
                "query": query,
                "source": source,
                "topic_id": str(topic_id) if topic_id else None,
                "max_tokens": max_tokens,
                "min_score": min_score
            }
        )
        response.raise_for_status()
        return response.json()
    
    def record_feedback(
        self,
        memory_id: UUID,
        context_log_id: UUID,
        feedback_type: str
    ):
        """Record outcome feedback"""
        response = self.session.post(
            f"{self.base_url}/api/v1/context/feedback",
            json={
                "memory_id": str(memory_id),
                "context_log_id": str(context_log_id),
                "feedback_type": feedback_type
            }
        )
        response.raise_for_status()
    
    def health_check(self) -> Dict:
        """Check API health"""
        response = self.session.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()
```

**3. API Documentation (api/openapi.yaml)**
```yaml
openapi: 3.0.0
info:
  title: ACMS Universal Context API
  description: Memory API for all AI tools
  version: 1.0.0

servers:
  - url: http://localhost:40080
    description: Local development

paths:
  /api/v1/context/store:
    post:
      summary: Store new memory
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [user_id, topic_id, content, source]
              properties:
                user_id:
                  type: string
                  format: uuid
                topic_id:
                  type: string
                  format: uuid
                content:
                  type: string
                source:
                  type: string
                  enum: [chatgpt, claude, claude_code, cursor, glean, copilot, custom]
                metadata:
                  type: object
      responses:
        '201':
          description: Memory stored
          content:
            application/json:
              schema:
                type: object
                properties:
                  memory_id:
                    type: string
                    format: uuid
                  status:
                    type: string

  /api/v1/context/retrieve:
    post:
      summary: Retrieve relevant context
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [user_id, query, source]
              properties:
                user_id:
                  type: string
                  format: uuid
                query:
                  type: string
                source:
                  type: string
                topic_id:
                  type: string
                  format: uuid
                max_tokens:
                  type: integer
                  default: 2000
                min_score:
                  type: number
                  default: 0.5
      responses:
        '200':
          description: Context retrieved
          content:
            application/json:
              schema:
                type: object
                properties:
                  context:
                    type: string
                  memories_used:
                    type: array
                    items:
                      type: string
                      format: uuid
                  token_count:
                    type: integer
                  retrieval_latency_ms:
                    type: integer

  /api/v1/context/feedback:
    post:
      summary: Record outcome feedback
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [memory_id, context_log_id, feedback_type]
              properties:
                memory_id:
                  type: string
                  format: uuid
                context_log_id:
                  type: string
                  format: uuid
                feedback_type:
                  type: string
                  enum: [helpful, not_helpful, irrelevant]
      responses:
        '200':
          description: Feedback recorded
```

#### **Testing Strategy (Phase 4):**

**API Tests:**
```python
# tests/api/test_context_api.py
def test_store_context():
    response = client.post("/api/v1/context/store", json={
        "user_id": str(user_id),
        "topic_id": str(topic_id),
        "content": "Test memory",
        "source": "chatgpt"
    })
    assert response.status_code == 201
    assert "memory_id" in response.json()

def test_retrieve_context():
    # Store some memories first
    store_test_memories()
    
    # Retrieve
    response = client.post("/api/v1/context/retrieve", json={
        "user_id": str(user_id),
        "query": "What is our AWS setup?",
        "source": "claude",
        "max_tokens": 1000
    })
    assert response.status_code == 200
    data = response.json()
    assert "context" in data
    assert data["token_count"] <= 1000

def test_context_formatting_per_tool():
    # Test that different tools get different formats
    memories = [{"content": "Test memory 1"}]
    
    chatgpt_format = format_context_for_tool(memories, "chatgpt")
    assert "# Relevant Context" in chatgpt_format
    
    claude_format = format_context_for_tool(memories, "claude")
    assert "<context>" in claude_format
    
    cursor_format = format_context_for_tool(memories, "cursor")
    assert "//" in cursor_format
```

**Checkpoint 4 Criteria:**
- ✅ API server running on port 40080
- ✅ All endpoints functional (store, retrieve, feedback)
- ✅ Context formatting working for each tool type
- ✅ API client library working
- ✅ OpenAPI documentation complete
- ✅ Test coverage > 85%
- ✅ Performance: < 100ms API response time (excluding embedding generation)

---

### **Phase 5: Connector Framework** 🆕 UPDATED
- **Duration**: 14 hours (Hour 40-54)
- **Objective**: Build connectors for ChatGPT, Claude, Cursor, Glean, Copilot

#### **Key Change from Original Plan:**
**OLD**: Outcome learning system  
**NEW**: Connector SDK + 5 pre-built connectors

#### **Deliverables:**

**1. Connector SDK (connectors/sdk/connector_base.py)**
```python
from abc import ABC, abstractmethod
from typing import Dict, Optional
from uuid import UUID
from sdk.python.acms_client import ACMSClient

class ACMSConnector(ABC):
    """
    Base class for ACMS connectors
    Implement this to connect any AI tool to ACMS
    """
    
    def __init__(self, acms_client: ACMSClient, user_id: UUID, topic_id: UUID):
        self.acms = acms_client
        self.user_id = user_id
        self.topic_id = topic_id
        self.tool_name = self.get_tool_name()
    
    @abstractmethod
    def get_tool_name(self) -> str:
        """Return tool identifier (e.g., 'chatgpt', 'claude')"""
        pass
    
    @abstractmethod
    def intercept_query(self, query: str) -> str:
        """
        Intercept user query before sending to AI tool
        Retrieve relevant context and inject it
        """
        pass
    
    @abstractmethod
    def capture_response(self, query: str, response: str):
        """
        Capture AI tool response after generation
        Store as memory in ACMS
        """
        pass
    
    def inject_context(self, query: str, max_tokens: int = 2000) -> str:
        """
        Helper: Retrieve context from ACMS and format for tool
        """
        context_data = self.acms.retrieve_context(
            user_id=self.user_id,
            query=query,
            source=self.tool_name,
            topic_id=self.topic_id,
            max_tokens=max_tokens
        )
        return context_data['context']
    
    def store_interaction(self, content: str, metadata: Optional[Dict] = None):
        """
        Helper: Store interaction in ACMS
        """
        self.acms.store_context(
            user_id=self.user_id,
            topic_id=self.topic_id,
            content=content,
            source=self.tool_name,
            metadata=metadata
        )
```

**2. ChatGPT Connector (connectors/chatgpt/connector.py)**
```python
from connectors.sdk.connector_base import ACMSConnector

class ChatGPTConnector(ACMSConnector):
    """
    Connector for ChatGPT
    Works via browser extension (intercepts DOM)
    """
    
    def get_tool_name(self) -> str:
        return "chatgpt"
    
    def intercept_query(self, query: str) -> str:
        """
        Before user submits query:
        1. Retrieve relevant context from ACMS
        2. Prepend context to query
        """
        context = self.inject_context(query, max_tokens=1500)
        
        # Format for ChatGPT
        enhanced_query = f"""{context}

---

User query: {query}

Please answer the query using the context above when relevant.
"""
        return enhanced_query
    
    def capture_response(self, query: str, response: str):
        """
        After ChatGPT responds:
        Store Q&A pair as memory
        """
        content = f"Q: {query}\nA: {response}"
        self.store_interaction(
            content=content,
            metadata={"type": "qa_pair"}
        )
```

**3. Claude/Claude Code Connector (connectors/claude/connector.py)**
```python
from connectors.sdk.connector_base import ACMSConnector

class ClaudeConnector(ACMSConnector):
    """
    Connector for Claude (web) and Claude Code (CLI)
    """
    
    def get_tool_name(self) -> str:
        return "claude"
    
    def intercept_query(self, query: str) -> str:
        """Inject context in Claude's XML format"""
        context = self.inject_context(query, max_tokens=2000)
        
        # Context is already formatted as XML by API
        enhanced_query = f"""{context}

{query}"""
        return enhanced_query
    
    def capture_response(self, query: str, response: str):
        """Store Claude interaction"""
        content = f"Query: {query}\n\nClaude's response: {response}"
        self.store_interaction(content=content)

class ClaudeCodeConnector(ClaudeConnector):
    """
    Connector for Claude Code
    Intercepts via MCP (Model Context Protocol)
    """
    
    def get_tool_name(self) -> str:
        return "claude_code"
    
    def capture_code_context(self, file_path: str, code: str):
        """Store code file context"""
        content = f"File: {file_path}\n\n```\n{code}\n```"
        self.store_interaction(
            content=content,
            metadata={"type": "code", "file": file_path}
        )
```

**4. Cursor Connector (connectors/cursor/connector.py)**
```python
from connectors.sdk.connector_base import ACMSConnector

class CursorConnector(ACMSConnector):
    """
    Connector for Cursor IDE
    Integrates as VS Code extension
    """
    
    def get_tool_name(self) -> str:
        return "cursor"
    
    def intercept_query(self, query: str) -> str:
        """
        Inject project context for Cursor
        Format as code comments
        """
        context = self.inject_context(query, max_tokens=1500)
        
        # Cursor format: code comments
        enhanced_query = f"""{context}

{query}"""
        return enhanced_query
    
    def capture_code_generation(self, prompt: str, generated_code: str):
        """Store code generation for future reference"""
        content = f"Prompt: {prompt}\n\nGenerated code:\n```\n{generated_code}\n```"
        self.store_interaction(
            content=content,
            metadata={"type": "code_generation"}
        )
```

**5. GitHub Copilot Connector (connectors/copilot/connector.py)**
```python
from connectors.sdk.connector_base import ACMSConnector

class CopilotConnector(ACMSConnector):
    """
    Connector for GitHub Copilot
    Integrates as VS Code extension
    """
    
    def get_tool_name(self) -> str:
        return "copilot"
    
    def get_project_context(self, file_path: str) -> str:
        """
        Retrieve project-specific context
        Based on current file location
        """
        query = f"Context for file: {file_path}"
        context = self.inject_context(query, max_tokens=1000)
        return context
    
    def intercept_query(self, query: str) -> str:
        """Inject project context into Copilot prompt"""
        context = self.inject_context(query, max_tokens=1000)
        return f"{context}\n\n{query}"
    
    def capture_response(self, query: str, response: str):
        """Store Copilot interaction"""
        self.store_interaction(f"Q: {query}\nA: {response}")
```

**6. Glean Connector (connectors/glean/connector.py)**
```python
from connectors.sdk.connector_base import ACMSConnector

class GleanConnector(ACMSConnector):
    """
    Connector for Glean enterprise search
    Enhances Glean with personal context
    """
    
    def get_tool_name(self) -> str:
        return "glean"
    
    def intercept_query(self, query: str) -> str:
        """
        Before Glean search:
        Add personal/team context from ACMS
        """
        context = self.inject_context(query, max_tokens=1000)
        
        enhanced_query = f"""Personal context: {context}

Search query: {query}"""
        return enhanced_query
    
    def capture_search_result(self, query: str, results: list):
        """Store useful search results as memories"""
        for result in results[:3]:  # Top 3 results
            content = f"Glean result for '{query}': {result['title']}\n{result['snippet']}"
            self.store_interaction(
                content=content,
                metadata={"type": "search_result", "url": result.get('url')}
            )
```

**7. Browser Extension (extensions/chrome/)**
```javascript
// extensions/chrome/content.js
// Inject ACMS context into ChatGPT, Claude, Perplexity, etc.

const ACMS_API = 'http://localhost:40080';
const USER_ID = localStorage.getItem('acms_user_id');
const TOPIC_ID = localStorage.getItem('acms_topic_id');

// Detect which AI tool we're on
const detectTool = () => {
  if (window.location.hostname.includes('chat.openai.com')) return 'chatgpt';
  if (window.location.hostname.includes('claude.ai')) return 'claude';
  if (window.location.hostname.includes('perplexity.ai')) return 'perplexity';
  return null;
};

// Intercept query submission
const interceptQuery = async (originalQuery) => {
  const tool = detectTool();
  if (!tool) return originalQuery;
  
  // Retrieve context from ACMS
  const response = await fetch(`${ACMS_API}/api/v1/context/retrieve`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user_id: USER_ID,
      query: originalQuery,
      source: tool,
      max_tokens: 1500
    })
  });
  
  const data = await response.json();
  
  // Inject context
  const enhancedQuery = `${data.context}\n\n---\n\n${originalQuery}`;
  
  // Show badge: "Context from ACMS"
  showACMSBadge(data.memories_used.length, data.token_count);
  
  return enhancedQuery;
};

// Capture response and store
const captureResponse = async (query, response) => {
  const tool = detectTool();
  if (!tool) return;
  
  await fetch(`${ACMS_API}/api/v1/context/store`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user_id: USER_ID,
      topic_id: TOPIC_ID,
      content: `Q: ${query}\nA: ${response}`,
      source: tool,
      metadata: {type: 'qa_pair'}
    })
  });
};

// ChatGPT-specific DOM manipulation
if (detectTool() === 'chatgpt') {
  const textarea = document.querySelector('textarea');
  
  textarea.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const originalQuery = textarea.value;
      const enhancedQuery = await interceptQuery(originalQuery);
      textarea.value = enhancedQuery;
      // Submit
      textarea.form.submit();
    }
  });
}
```

**8. VS Code Extension (extensions/vscode/)**
```typescript
// extensions/vscode/src/extension.ts
import * as vscode from 'vscode';
import axios from 'axios';

const ACMS_API = 'http://localhost:40080';

export function activate(context: vscode.ExtensionContext) {
  
  // Register command: Inject ACMS context
  let disposable = vscode.commands.registerCommand(
    'acms.injectContext',
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      
      const selection = editor.selection;
      const selectedText = editor.document.getText(selection);
      
      // Get file context from ACMS
      const filePath = editor.document.fileName;
      const response = await axios.post(`${ACMS_API}/api/v1/context/retrieve`, {
        user_id: getUserId(),
        query: `Context for file: ${filePath}`,
        source: 'cursor',
        max_tokens: 1000
      });
      
      const context = response.data.context;
      
      // Insert context as comment
      editor.edit(editBuilder => {
        editBuilder.insert(selection.start, `${context}\n\n`);
      });
    }
  );
  
  // Auto-capture code on save
  vscode.workspace.onDidSaveTextDocument(async (document) => {
    const code = document.getText();
    await axios.post(`${ACMS_API}/api/v1/context/store`, {
      user_id: getUserId(),
      topic_id: getTopicId(),
      content: `File: ${document.fileName}\n\`\`\`\n${code}\n\`\`\``,
      source: 'cursor',
      metadata: {type: 'code', file: document.fileName}
    });
  });
  
  context.subscriptions.push(disposable);
}

function getUserId(): string {
  return vscode.workspace.getConfiguration('acms').get('userId') || '';
}

function getTopicId(): string {
  return vscode.workspace.getConfiguration('acms').get('topicId') || '';
}
```

#### **Testing Strategy (Phase 5):**

**Connector Tests:**
```python
# tests/connectors/test_chatgpt_connector.py
def test_chatgpt_context_injection():
    connector = ChatGPTConnector(acms_client, user_id, topic_id)
    enhanced = connector.intercept_query("What is our AWS setup?")
    assert "Relevant Context" in enhanced
    assert "What is our AWS setup?" in enhanced

# tests/connectors/test_claude_connector.py
def test_claude_xml_formatting():
    connector = ClaudeConnector(acms_client, user_id, topic_id)
    enhanced = connector.intercept_query("Explain our database schema")
    assert "<context>" in enhanced
    assert "</context>" in enhanced
```

**Checkpoint 5 Criteria:**
- ✅ Connector SDK functional
- ✅ 5 connectors implemented (ChatGPT, Claude, Cursor, Copilot, Glean)
- ✅ Browser extension working
- ✅ VS Code extension working
- ✅ Context injection verified for each tool
- ✅ Memory capture working
- ✅ Test coverage > 80%

---

### **Phase 6: Production Hardening & Launch**
- **Duration**: 14 hours (Hour 54-68)
- **Objective**: Security, performance, deployment, self-service signup

#### **Deliverables:**

**1. Authentication & Authorization (auth/jwt.py)**
```python
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "your-secret-key-here"  # Move to env var
ALGORITHM = "HS256"

security = HTTPBearer()

def create_access_token(user_id: str) -> str:
    """Create JWT token for user"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**2. Rate Limiting (middleware/rate_limit.py)**
```python
from fastapi import Request, HTTPException
from redis import Redis
import time

redis_client = Redis(host='localhost', port=40379, decode_responses=True)

async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limit: 100 requests per minute per user
    """
    user_id = request.state.user_id  # From auth middleware
    key = f"rate_limit:{user_id}"
    
    # Increment counter
    count = redis_client.incr(key)
    
    if count == 1:
        redis_client.expire(key, 60)  # Reset after 1 minute
    
    if count > 100:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    response = await call_next(request)
    return response
```

**3. Performance Monitoring (monitoring/prometheus.py)**
```python
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import FastAPI

# Metrics
context_store_requests = Counter('acms_context_store_total', 'Total context store requests')
context_retrieve_requests = Counter('acms_context_retrieve_total', 'Total context retrieve requests')
retrieval_latency = Histogram('acms_retrieval_latency_seconds', 'Context retrieval latency')

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")
```

**4. Self-Service Web App (webapp/)**
```typescript
// webapp/src/App.tsx
// Next.js app for user signup, configuration, dashboard

import { useState } from 'react';

export default function Dashboard() {
  const [apiKey, setApiKey] = useState('');
  const [stats, setStats] = useState(null);
  
  // Fetch user stats
  useEffect(() => {
    fetch('/api/stats', {
      headers: {'Authorization': `Bearer ${apiKey}`}
    })
    .then(res => res.json())
    .then(data => setStats(data));
  }, [apiKey]);
  
  return (
    <div>
      <h1>ACMS Dashboard</h1>
      
      {/* API Key management */}
      <section>
        <h2>API Key</h2>
        <input 
          type="text" 
          value={apiKey} 
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Enter your API key"
        />
      </section>
      
      {/* Usage statistics */}
      <section>
        <h2>Usage Stats</h2>
        {stats && (
          <>
            <p>Memories stored: {stats.total_memories}</p>
            <p>Context retrievals: {stats.total_retrievals}</p>
            <p>Token savings: {stats.token_savings}</p>
            <p>Cost savings: ${stats.cost_savings}</p>
          </>
        )}
      </section>
      
      {/* Connected tools */}
      <section>
        <h2>Connected AI Tools</h2>
        <ul>
          <li>ChatGPT ✅</li>
          <li>Claude ✅</li>
          <li>Cursor ✅</li>
          <li>Copilot ✅</li>
          <li>Glean ✅</li>
        </ul>
      </section>
      
      {/* Memory browser */}
      <section>
        <h2>Recent Memories</h2>
        {/* List of recent memories with delete option */}
      </section>
    </div>
  );
}
```

**5. Deployment (deploy/)**
```yaml
# deploy/docker-compose.prod.yml
version: '3.8'

services:
  acms-api:
    build: .
    ports:
      - "40080:40080"
    environment:
      - DATABASE_URL=postgresql://acms:${DB_PASSWORD}@postgres:5432/acms
      - REDIS_URL=redis://redis:6379
      - WEAVIATE_URL=http://weaviate:8080
      - OLLAMA_URL=http://ollama:40434
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - postgres
      - redis
      - weaviate
      - ollama
    restart: always
  
  postgres:
    image: postgres:16-alpine
    ports:
      - "40432:5432"
    environment:
      - POSTGRES_DB=acms
      - POSTGRES_USER=acms
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
  
  redis:
    image: redis:7-alpine
    ports:
      - "40379:6379"
    volumes:
      - redis_data:/data
    restart: always
  
  weaviate:
    image: semitechnologies/weaviate:1.32.2
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      - CLUSTER_HOSTNAME=weaviate
      - PERSISTENCE_DATA_PATH=/var/lib/weaviate
    volumes:
      - weaviate_data:/var/lib/weaviate
    restart: always
  
  ollama:
    image: ollama/ollama:latest
    ports:
      - "40434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: always

volumes:
  postgres_data:
  redis_data:
  weaviate_data:
  ollama_data:
```

**6. Documentation (docs/)**
- **README.md**: Quick start guide
- **API_REFERENCE.md**: Complete API documentation
- **CONNECTOR_GUIDE.md**: How to build new connectors
- **DEPLOYMENT.md**: Self-hosting instructions
- **FAQ.md**: Common questions

#### **Testing Strategy (Phase 6):**

**Load Tests:**
```python
# tests/load/test_api_load.py
from locust import HttpUser, task, between

class ACMSUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def store_context(self):
        self.client.post("/api/v1/context/store", json={
            "user_id": self.user_id,
            "topic_id": self.topic_id,
            "content": "Load test memory",
            "source": "test"
        })
    
    @task(2)  # 2x more frequent than store
    def retrieve_context(self):
        self.client.post("/api/v1/context/retrieve", json={
            "user_id": self.user_id,
            "query": "Load test query",
            "source": "test"
        })
```

**Security Tests:**
```python
# tests/security/test_auth.py
def test_jwt_expiration():
    token = create_access_token(user_id, exp_minutes=1)
    time.sleep(61)  # Wait for expiration
    with pytest.raises(HTTPException):
        verify_token(token)

def test_rate_limiting():
    # Make 101 requests rapidly
    for i in range(101):
        response = client.post("/api/v1/context/store", ...)
    # 101st request should fail
    assert response.status_code == 429
```

**Checkpoint 6 Criteria:**
- ✅ Authentication working (JWT)
- ✅ Rate limiting functional
- ✅ Monitoring/metrics endpoint working
- ✅ Web app deployed
- ✅ Load tests passing (100+ concurrent users)
- ✅ Security tests passing
- ✅ Documentation complete
- ✅ Ready for public launch

---

## 📊 **SUCCESS METRICS**

### **Technical Metrics:**
- **API Latency**: < 100ms (p95)
- **Context Retrieval**: < 200ms (p95, including embedding)
- **Token Reduction**: 30-50% compared to no memory
- **Relevance Score**: > 0.6 average CRS score for retrieved context
- **Uptime**: 99.9% SLA
- **Test Coverage**: > 85%

### **User Metrics (First 3 Months):**
- **Signups**: 1,000 users
- **Active Users**: 300 DAU (30% activation)
- **Memories Stored**: 100,000+ across all users
- **Context Retrievals**: 10,000+ per day
- **Connected Tools**: 3+ tools per user average
- **NPS**: > 40 (product-market fit)

### **Business Metrics:**
- **MRR**: $10K (500 paying users @ $20/mo)
- **Token Savings**: $50K+ saved for users (aggregate)
- **Enterprise Inquiries**: 10+ qualified leads
- **Churn**: < 10% monthly

---

## 🚢 **GO-TO-MARKET PLAN**

### **Week 1-2: Soft Launch**
- Post on Product Hunt: "Universal Memory API for All AI Tools"
- Post on Hacker News: "Show HN: ACMS - Context bridge for ChatGPT, Claude, Cursor, etc."
- Reddit: r/ChatGPT, r/ClaudeAI, r/LocalLLaMA, r/vscode
- Twitter: Thread with demo videos
- Email 100 friends/colleagues

### **Week 3-4: Community Building**
- Create Discord server for beta users
- Weekly office hours (Q&A, feature requests)
- Case study from top 5 users
- Blog post: "How ACMS Saves Me 2 Hours/Day"

### **Month 2: Growth**
- Add 3 more connectors based on demand
- Launch referral program (refer 3, get 1 month free)
- Conference talk submissions (AI/DevTools conferences)
- Partnership discussions with AI tool vendors

### **Month 3: Enterprise Pivot**
- Publish enterprise version (SSO, admin dashboard, audit logs)
- Outreach to 50 target enterprises
- Case study from first enterprise customer
- Pricing: $15/user/month for teams (10+ users)

---

## 🔧 **TECH STACK SUMMARY**

```
Frontend:
- Web App: Next.js, TypeScript, Tailwind CSS
- Browser Extension: JavaScript, Chrome Extension API
- VS Code Extension: TypeScript, VS Code API

Backend:
- API Server: Python, FastAPI
- Storage: PostgreSQL 16, Redis 7
- Vector DB: Weaviate 1.32.2
- Embeddings: Ollama (all-minilm:22m)
- Authentication: JWT
- Monitoring: Prometheus, Grafana

Infrastructure:
- Containerization: Docker Compose
- Orchestration: Kubernetes (for scale)
- CI/CD: GitHub Actions
- Hosting: Self-hosted or cloud (AWS/GCP/Azure)

Development:
- Language: Python 3.11+
- Testing: pytest, locust
- Code Quality: black, mypy, pylint
- Documentation: Sphinx, OpenAPI
```

---

## 📦 **DELIVERABLES CHECKLIST**

### **Phase 0: Bootstrap** ✅ COMPLETE
- [x] ACMS-Lite (SQLite CLI)
- [x] 48 memories stored
- [x] Checkpoint 0 passed

### **Phase 1: Infrastructure** ✅ COMPLETE
- [x] Docker Compose
- [x] PostgreSQL, Redis, Ollama running
- [x] Weaviate (existing) configured
- [x] Health checks passing

### **Phase 2: Storage Layer**
- [ ] PostgreSQL schemas
- [ ] Alembic migrations
- [ ] Weaviate collection setup
- [ ] Encryption manager
- [ ] Memory storage module
- [ ] Checkpoint 2

### **Phase 3: Core Memory Engine**
- [ ] Embedding generator
- [ ] Context Retrieval System (CRS)
- [ ] Memory ingestion pipeline
- [ ] Tier manager
- [ ] Checkpoint 3

### **Phase 4: Universal Context API**
- [ ] FastAPI server
- [ ] API endpoints (store, retrieve, feedback)
- [ ] Python client library
- [ ] OpenAPI documentation
- [ ] Checkpoint 4

### **Phase 5: Connector Framework**
- [ ] Connector SDK
- [ ] ChatGPT connector
- [ ] Claude/Claude Code connector
- [ ] Cursor connector
- [ ] GitHub Copilot connector
- [ ] Glean connector
- [ ] Browser extension
- [ ] VS Code extension
- [ ] Checkpoint 5

### **Phase 6: Production Hardening**
- [ ] Authentication (JWT)
- [ ] Rate limiting
- [ ] Monitoring (Prometheus)
- [ ] Self-service web app
- [ ] Deployment configuration
- [ ] Documentation
- [ ] Load testing
- [ ] Security testing
- [ ] Checkpoint 6
- [ ] PUBLIC LAUNCH 🚀

---

## 🎯 **INSTRUCTIONS FOR CLAUDE CODE**

### **Starting Point:**
You have completed:
- ✅ Phase 0: ACMS-Lite operational
- ✅ Phase 1: Infrastructure deployed (Docker services running)

### **Next Steps:**

1. **Query ACMS-Lite before every decision:**
   ```bash
   python3 acms_lite.py query "PostgreSQL schema for memory_items"
   python3 acms_lite.py query "CRS formula components"
   python3 acms_lite.py query "port configuration"
   ```

2. **Follow TDD strictly:**
   - Write tests FIRST for each component
   - Run tests to verify they fail
   - Implement component
   - Run tests to verify they pass
   - Refactor if needed

3. **Store every decision:**
   ```bash
   python3 acms_lite.py store "Decision: Using XChaCha20-Poly1305 for encryption because..." --tag decision --phase storage
   python3 acms_lite.py store "Implementation: Memory store module complete, 150 lines" --tag implementation --phase storage
   python3 acms_lite.py store "Error: Weaviate connection timeout, resolved by..." --tag error --phase storage
   ```

4. **Run checkpoints:**
   After each phase, run:
   ```bash
   python3 tests/checkpoint_validation.py <phase_number>
   ```

5. **Generate phase summaries:**
   After each phase:
   ```bash
   python3 acms_lite.py query "phase <N> activities" --limit 50
   # Use results to generate docs/phase<N>_summary.md
   ```

### **Build Priorities:**
1. **Speed**: Use Python for all components (not Go) for MVP speed
2. **Quality**: No workarounds, production-ready code only
3. **Testing**: >85% coverage, TDD always
4. **Documentation**: Inline docstrings + markdown docs

### **Key Rules:**
- ❌ NEVER delete existing Weaviate collections
- ❌ NEVER skip tests
- ❌ NEVER use workarounds
- ✅ ALWAYS query ACMS-Lite first
- ✅ ALWAYS store decisions/implementations
- ✅ ALWAYS run checkpoints

### **Ready to Start Phase 2?**
Begin with:
```bash
# 1. Query existing knowledge
python3 acms_lite.py query "PostgreSQL schema requirements"

# 2. Create tests first
touch tests/unit/test_encryption.py
# Write tests for encryption module

# 3. Implement
touch crypto/encryption.py
# Implement XChaCha20-Poly1305 encryption

# 4. Store progress
python3 acms_lite.py store "Implemented encryption manager" --tag milestone --phase storage
```

---

**END OF BUILD PLAN**

**Good luck building the Universal Context API! 🚀**
