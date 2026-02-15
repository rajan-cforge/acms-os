# ACMS Cognitive Architecture Improvements
## Engineering Specification — Derived from "The Architecture of Cognition" Series
### February 2026

---

## Overview

This document translates the cognitive science principles from the Architecture of Cognition reading series into specific, implementable improvements for ACMS. Each improvement is grounded in both neuroscience research and the actual ACMS codebase (as documented in the Claude Code architecture analysis). Improvements are ordered by implementation priority, estimated effort, and expected impact.

---

## TIER 1: IMMEDIATE IMPROVEMENTS (1-3 Days Each)

---

### 1.1 Consolidation Triage — Selective Knowledge Extraction

**Cognitive Principle:** The hippocampus selectively replays experiences during sleep consolidation, prioritizing novel, emotionally significant, and goal-relevant memories. Not everything gets consolidated. (Chapter 2: Sleep Consolidation Engine)

**Current ACMS Behavior:** The intelligence pipeline (`src/jobs/intelligence_jobs.py`) processes ALL unprocessed `query_history` records through the full knowledge extraction pipeline, including Claude Sonnet calls at $0.10/hour budget cap.

**Problem:** Transient queries ("what time is it in Tokyo?", "convert 5kg to pounds") consume the same LLM extraction budget as high-value interactions ("here's how I solved the RBAC issue in our staging cluster"). This is the equivalent of the hippocampus consolidating your memory of glancing at a clock with the same intensity as your memory of a car accident.

**Implementation:**

File: `src/jobs/intelligence_jobs.py` — Add triage step before Stage 1 Topic Extraction

```python
class ConsolidationPriority(Enum):
    FULL_EXTRACTION = "full"        # Full knowledge extraction with Claude
    LIGHTWEIGHT_TAGGING = "light"   # Keyword-only topic tagging, no LLM
    TRANSIENT = "transient"         # Mark for TTL expiration, skip extraction

class ConsolidationTriager:
    """
    Hippocampal replay selector: determines which query_history
    entries warrant full consolidation vs. lightweight encoding
    vs. natural decay.
    """

    # Signals that indicate high consolidation priority
    HIGH_VALUE_SIGNALS = {
        "follow_up_detected": 0.15,    # User asked follow-ups
        "long_response": 0.10,          # Response > 500 words
        "code_in_response": 0.10,       # Contains code blocks
        "explicit_positive_feedback": 0.20,  # Thumbs up
        "session_duration_gt_5min": 0.10,    # Extended engagement
        "novel_topic": 0.15,            # Topic not in existing clusters
    }

    # Signals that indicate transient/disposable queries
    TRANSIENT_PATTERNS = [
        r"\b(what time|convert|calculate|translate)\b",
        r"\b(hello|hi|thanks|thank you|goodbye)\b",
        r"^.{0,20}$",  # Very short queries (< 20 chars)
    ]

    def triage(self, query_record: QueryHistory) -> ConsolidationPriority:
        # Check transient patterns first (fast path)
        if self._is_transient(query_record.question):
            return ConsolidationPriority.TRANSIENT

        # Calculate consolidation score
        score = 0.5  # Base score
        for signal, weight in self.HIGH_VALUE_SIGNALS.items():
            if self._check_signal(query_record, signal):
                score += weight

        if score >= 0.7:
            return ConsolidationPriority.FULL_EXTRACTION
        elif score >= 0.4:
            return ConsolidationPriority.LIGHTWEIGHT_TAGGING
        else:
            return ConsolidationPriority.TRANSIENT
```

**Integration point:** Modify `run_topic_extraction()` in `intelligence_jobs.py`:

```python
async def run_topic_extraction():
    unprocessed = await get_unprocessed_queries()
    triager = ConsolidationTriager()

    for query in unprocessed:
        priority = triager.triage(query)

        if priority == ConsolidationPriority.FULL_EXTRACTION:
            await full_knowledge_extraction(query)  # Existing pipeline
        elif priority == ConsolidationPriority.LIGHTWEIGHT_TAGGING:
            await keyword_only_extraction(query)     # Free, no LLM
        else:
            await mark_as_transient(query)            # Skip, TTL decay
```

**Expected Impact:**
- 40-60% reduction in LLM extraction costs (based on typical query distribution)
- Higher quality knowledge base (less noise from throwaway queries)
- Faster consolidation cycles (processing fewer records per hour)

---

### 1.2 Adaptive Similarity Thresholds — Pattern Separation vs. Completion

**Cognitive Principle:** The hippocampus dynamically switches between pattern separation (dentate gyrus, high precision) and pattern completion (CA3, high recall) based on the nature of the retrieval cue. (Chapter 2: Pattern Separation and Pattern Completion)

**Current ACMS Behavior:**
- QualityCache: Fixed 0.95 threshold (`src/cache/quality_cache.py`)
- Raw retrieval: Fixed 0.85 threshold (`src/retrieval/engine.py`)
- Knowledge retrieval: Fixed 0.60 threshold (`src/retrieval/engine.py`)

**Problem:** A factual recall query ("What was the exact kubectl command I used for RBAC?") and a conceptual exploration query ("What do I know about Kubernetes security?") hit the same similarity thresholds. The first needs pattern separation (exact match, high threshold). The second needs pattern completion (broad match, lower threshold).

**Implementation:**

File: `src/retrieval/engine.py` — Add threshold resolver

```python
class RetrievalMode(Enum):
    EXACT_RECALL = "exact"          # "What was the command..."
    CONCEPTUAL_EXPLORE = "explore"  # "What do I know about..."
    TROUBLESHOOT = "troubleshoot"   # "Why is X failing..."
    COMPARE = "compare"             # "Difference between X and Y"
    DEFAULT = "default"

THRESHOLD_MAP = {
    RetrievalMode.EXACT_RECALL: {
        "cache": 0.96,       # Very strict - near-identical queries only
        "raw": 0.90,         # High precision
        "knowledge": 0.80,   # Still tight for exact recall
    },
    RetrievalMode.CONCEPTUAL_EXPLORE: {
        "cache": 0.92,       # Slightly relaxed
        "raw": 0.75,         # Cast wider net
        "knowledge": 0.55,   # Broad conceptual matching
    },
    RetrievalMode.TROUBLESHOOT: {
        "cache": 0.90,       # Similar problems may have similar solutions
        "raw": 0.80,
        "knowledge": 0.60,
    },
    RetrievalMode.COMPARE: {
        "cache": 0.94,
        "raw": 0.82,
        "knowledge": 0.55,   # Need to find both items being compared
    },
    RetrievalMode.DEFAULT: {
        "cache": 0.95,       # Current defaults
        "raw": 0.85,
        "knowledge": 0.60,
    },
}

def resolve_retrieval_mode(intent: str, query: str) -> RetrievalMode:
    """
    Map intent classification (already in orchestrator.py Step 1)
    to retrieval mode.
    """
    EXACT_SIGNALS = ["what was", "show me the exact", "the command I used",
                     "that specific", "the code from"]
    EXPLORE_SIGNALS = ["what do I know", "everything about", "overview of",
                       "tell me about", "what have I learned"]
    TROUBLE_SIGNALS = ["why is", "failing", "error", "not working",
                       "broken", "debug", "fix"]
    COMPARE_SIGNALS = ["difference between", "compare", "vs", "versus",
                       "which is better"]

    query_lower = query.lower()
    for signal in EXACT_SIGNALS:
        if signal in query_lower:
            return RetrievalMode.EXACT_RECALL
    for signal in EXPLORE_SIGNALS:
        if signal in query_lower:
            return RetrievalMode.CONCEPTUAL_EXPLORE
    for signal in TROUBLE_SIGNALS:
        if signal in query_lower:
            return RetrievalMode.TROUBLESHOOT
    for signal in COMPARE_SIGNALS:
        if signal in query_lower:
            return RetrievalMode.COMPARE

    return RetrievalMode.DEFAULT
```

**Integration point:** Modify the dual memory search in `src/retrieval/engine.py` to pass thresholds dynamically rather than using hardcoded values.

**Expected Impact:**
- Better recall on exploratory queries (currently missing relevant knowledge due to overly strict thresholds)
- Better precision on exact recall queries (fewer false positives)
- No additional latency (threshold selection is a regex check, <1ms)

---

### 1.3 Propagated Forgetting — Cascading Invalidation

**Cognitive Principle:** Active forgetting (dopamine-mediated hippocampal trace deletion) serves a critical function: preventing outdated information from interfering with current processing. (Chapter 2: Forgetting as Garbage Collection)

**Current ACMS Behavior:** When `negative_feedback_count > 2` on a cache entry, it's deleted from `QualityCache` (`src/cache/quality_cache.py`). But related entries in ACMS_Knowledge_v2 and other cache entries about the same topic are unaffected.

**Problem:** If "OAuth requires session cookies" is downvoted and deleted, but "Session cookies are the OAuth authentication mechanism" exists as a separate knowledge entry extracted from a different session, the incorrect information persists. The brain's active forgetting cascades to related traces — ACMS's doesn't.

**Implementation:**

File: `src/cache/quality_cache.py` — Add propagation on deletion

```python
async def propagated_forget(deleted_entry: CacheEntry):
    """
    When an entry is actively forgotten (downvoted out),
    flag semantically similar entries for review.

    This is NOT automatic deletion — it's flagging.
    Only explicit downvotes trigger deletion.
    """
    deleted_embedding = await get_embedding(deleted_entry.query_text)

    # Search both collections for related content
    similar_raw = await weaviate_search(
        collection="ACMS_Raw_v1",
        vector=deleted_embedding,
        threshold=0.85,
        limit=10
    )
    similar_knowledge = await weaviate_search(
        collection="ACMS_Knowledge_v2",
        vector=deleted_embedding,
        threshold=0.80,
        limit=10
    )

    for entry in similar_raw + similar_knowledge:
        await flag_for_review(
            entry_id=entry.id,
            reason=f"Related to actively forgotten entry: {deleted_entry.query_text[:100]}",
            source_deletion_id=deleted_entry.id,
            review_priority="medium"
        )

    # Also check PostgreSQL memory_items
    similar_memories = await memory_crud.search_similar(
        embedding=deleted_embedding,
        threshold=0.85,
        user_id=deleted_entry.user_id
    )
    for memory in similar_memories:
        memory.flagged = True
        memory.metadata["review_reason"] = "related_to_forgotten_entry"
        await memory_crud.update(memory)
```

**Integration point:** Call `propagated_forget()` in the existing feedback handling path after `negative_feedback_count` exceeds 2 and the entry is deleted.

**Expected Impact:**
- Prevents "knowledge zombies" — incorrect information that survives in one collection after being killed in another
- Creates a review queue for potentially stale knowledge
- Maintains data integrity across the dual-collection architecture

---

## TIER 2: MEDIUM-EFFORT IMPROVEMENTS (1-2 Weeks Each)

---

### 2.1 Preflight Knowledge Check — "Feeling of Knowing"

**Cognitive Principle:** Before committing to full retrieval, the brain runs a fast approximate membership test ("feeling of knowing") that determines whether relevant knowledge exists. (Chapter 4: Bloom Filters and the Feeling of Knowing)

**Current ACMS Behavior:** Every query goes through the full retrieval pipeline — embedding generation, parallel Weaviate searches across both collections, PostgreSQL fallback, ranking, deduplication (`src/retrieval/engine.py`). This is expensive for queries about topics ACMS has never seen.

**Implementation:**

New file: `src/retrieval/knowledge_preflight.py`

```python
from collections import defaultdict
import hashlib

class KnowledgePreflight:
    """
    Fast approximate check: does ACMS likely have relevant knowledge
    for this query? Uses topic cluster centroids and entity Bloom filter
    to avoid expensive full retrieval for unknown topics.

    Analogous to the brain's "feeling of knowing" — a fast signal
    that says "I probably know something about this" before committing
    to full memory search.
    """

    def __init__(self):
        self.entity_bloom = BloomFilter(capacity=50000, error_rate=0.01)
        self.cluster_centroids = {}  # topic_slug -> centroid_embedding
        self._initialized = False

    async def initialize(self):
        """Load from existing knowledge base. Run at startup and hourly."""
        # Populate Bloom filter with all known entities
        entities = await knowledge_crud.get_all_entities()
        for entity in entities:
            self.entity_bloom.add(entity.canonical.lower())

        # Compute cluster centroids from topic_extractions
        clusters = await get_topic_clusters()
        for cluster in clusters:
            self.cluster_centroids[cluster.slug] = cluster.centroid_embedding

        self._initialized = True

    async def check(self, query: str, query_embedding: list) -> KnowledgeSignal:
        """
        Returns:
            LIKELY: Full retrieval warranted, high probability of useful results
            UNLIKELY: Skip retrieval, go direct to LLM agent
            UNCERTAIN: Run retrieval but with timeout budget
        """
        if not self._initialized:
            return KnowledgeSignal.UNCERTAIN

        # Fast check 1: Entity mention
        entities = fast_entity_extract(query)  # Regex-based, no LLM
        known_entities = [e for e in entities if e.lower() in self.entity_bloom]

        # Fast check 2: Nearest cluster distance
        min_distance = 1.0
        if self.cluster_centroids:
            for slug, centroid in self.cluster_centroids.items():
                dist = cosine_distance(query_embedding, centroid)
                min_distance = min(min_distance, dist)

        # Decision logic
        if known_entities and min_distance < 0.4:
            return KnowledgeSignal.LIKELY
        elif not known_entities and min_distance > 0.7:
            return KnowledgeSignal.UNLIKELY
        else:
            return KnowledgeSignal.UNCERTAIN
```

**Integration point:** Insert into `src/gateway/orchestrator.py` between Step 2 (Cache Check) and Step 3 (Agent Selection). When `UNLIKELY`, skip context assembly and go direct to agent execution — saving 100-300ms per query on unfamiliar topics.

**Expected Impact:**
- 15-25% latency reduction on queries about unfamiliar topics
- No impact on quality (unfamiliar topics produce no useful retrieval results anyway)
- Bloom filter + centroid check adds <5ms overhead

---

### 2.2 Salience-Weighted Consolidation — The Emotional Priority Queue

**Cognitive Principle:** The amygdala modulates hippocampal encoding strength based on emotional significance, creating a priority queue where important experiences get deeper encoding and preferential consolidation. (Chapter 2: The Emotional Priority Queue)

**Current ACMS Behavior:** All queries are consolidated with equal priority. The feedback system (thumbs up/down) is reactive — it adjusts quality after storage, not encoding depth during storage.

**Implementation:**

New file: `src/intelligence/salience_scorer.py`

```python
class SalienceScorer:
    """
    Emotional priority queue for ACMS. Estimates the importance
    of a query based on engagement signals, interaction patterns,
    and content characteristics.

    Used by ConsolidationTriager and by TTL extension logic.
    """

    async def score(self, query_id: str) -> SalienceScore:
        query = await get_query_history(query_id)
        session = await get_session_context(query.session_id)

        score = 0.5  # Base

        # Engagement signals (analogous to amygdala activation)
        follow_ups = await count_follow_up_queries(
            session_id=query.session_id,
            after=query.created_at,
            window_minutes=30
        )
        if follow_ups >= 3:
            score += 0.15  # Deep engagement = high salience

        if session.duration_seconds > 600:
            score += 0.10  # Extended session

        return_visits = await count_topic_returns(
            user_id=query.user_id,
            topic=query.primary_topic,
            days=14
        )
        if return_visits >= 3:
            score += 0.10  # Recurring interest

        # Content signals
        if len(query.answer) > 2000:
            score += 0.05  # Substantial response = complex topic
        if "```" in query.answer:
            score += 0.05  # Code content = implementation knowledge

        # Explicit feedback
        if query.feedback == "positive":
            score += 0.15
        elif query.feedback == "negative":
            score -= 0.20  # Strong negative = deprioritize

        # Emotional markers in query text
        frustration_markers = ["not working", "failing", "error", "broken",
                               "frustrated", "stuck", "help"]
        excitement_markers = ["perfect", "exactly", "brilliant", "love this",
                              "breakthrough"]
        query_lower = query.question.lower()

        if any(m in query_lower for m in frustration_markers):
            score += 0.05  # Pain point = valuable to remember solution
        if any(m in query_lower for m in excitement_markers):
            score += 0.10  # Breakthrough moment

        # Context window enhancement: boost surrounding queries
        # (analogous to flashbulb memory effect)
        context_window = await get_queries_in_window(
            session_id=query.session_id,
            center=query.created_at,
            window_minutes=10
        )

        return SalienceScore(
            value=min(max(score, 0.0), 1.0),
            signals=signals_used,
            context_window_ids=[q.id for q in context_window]
        )
```

**Integration points:**
1. `ConsolidationTriager` (Tier 1.1) uses salience scores for prioritization
2. `QualityCache` TTL can be extended for high-salience entries
3. Weekly reports can highlight high-salience interactions
4. Context window IDs enable "flashbulb" enhancement — when a query scores high, surrounding queries in the same session also get elevated priority

**Expected Impact:**
- Knowledge base weighted toward genuinely important interactions
- Better weekly reports (surfacing what actually mattered, not just what was frequent)
- Dynamic TTL prevents premature expiration of valuable cached responses

---

### 2.3 Co-Retrieval Graph — Hebbian Association Network

**Cognitive Principle:** "Neurons that fire together wire together." The brain tracks co-activation patterns and strengthens connections between frequently co-active representations. (Chapter 4: Hebbian Learning and the Access-Frequency Index)

**Current ACMS Behavior:** `MemoryItem` tracks individual `access_count` and `last_accessed`, but there's no tracking of *which items are retrieved together*. Each item exists in isolation.

**Implementation:**

New table in PostgreSQL + new file: `src/retrieval/coretrieval_graph.py`

```python
# New SQLAlchemy model
class CoRetrievalEdge(Base):
    __tablename__ = "coretrieval_edges"

    id = Column(UUID, primary_key=True, default=uuid4)
    item_a_id = Column(UUID, ForeignKey("memory_items.memory_id"))
    item_b_id = Column(UUID, ForeignKey("memory_items.memory_id"))
    co_retrieval_count = Column(Integer, default=1)
    avg_temporal_distance = Column(Float)  # seconds between retrievals
    last_co_retrieval = Column(DateTime)
    strength = Column(Float)  # Computed: log(count+1) * recency_factor
    context_topics = Column(JSONB)  # Topic clusters where co-retrieval occurred

    __table_args__ = (
        UniqueConstraint("item_a_id", "item_b_id"),
    )

class CoRetrievalTracker:
    """
    Hebbian learning for ACMS: track which knowledge items are
    retrieved together and build an association network.

    Enables associative pre-loading (when item A is retrieved,
    proactively fetch strongly associated items B and C).
    """

    async def record_co_retrieval(self, session_id: str,
                                   retrieved_ids: List[str],
                                   topic_context: str):
        """Called after each retrieval session with all result IDs."""
        for id_a, id_b in itertools.combinations(retrieved_ids, 2):
            # Ensure consistent ordering
            a, b = sorted([id_a, id_b])

            edge = await get_or_create_edge(a, b)
            edge.co_retrieval_count += 1
            edge.last_co_retrieval = datetime.utcnow()
            edge.strength = self._compute_strength(edge)

            # Track topic context
            if edge.context_topics is None:
                edge.context_topics = {}
            edge.context_topics[topic_context] = \
                edge.context_topics.get(topic_context, 0) + 1

            await upsert_edge(edge)

    def _compute_strength(self, edge: CoRetrievalEdge) -> float:
        """Hebbian strength with recency decay."""
        count_factor = math.log(edge.co_retrieval_count + 1)
        days_since = (datetime.utcnow() - edge.last_co_retrieval).days
        recency_factor = math.exp(-0.05 * days_since)  # Half-life ~14 days
        return count_factor * recency_factor

    async def get_associated_items(self, item_id: str,
                                    min_strength: float = 0.5,
                                    limit: int = 5) -> List[AssociatedItem]:
        """Get items strongly associated with the given item."""
        edges = await get_edges_for_item(item_id, min_strength, limit)
        return [
            AssociatedItem(
                id=edge.other_id(item_id),
                strength=edge.strength,
                co_retrieval_count=edge.co_retrieval_count
            )
            for edge in edges
        ]
```

**Integration point:** In `src/retrieval/engine.py`, after primary retrieval returns results, call `get_associated_items()` for the top results and include strongly associated items in the context assembly — even if they didn't directly match the query embedding. This is associative pre-loading: pulling on one thread brings connected threads with it.

**Expected Impact:**
- Richer context assembly without requiring explicit user queries
- System learns user's knowledge structure over time
- Enables "anticipatory coupling" (Chapter 3) — surfacing related knowledge before it's asked for

---

### 2.4 Cross-Validation — Error Detection Across Collections

**Cognitive Principle:** The brain uses redundant encoding across multiple modalities (visual, auditory, spatial, emotional) for error correction. When modalities disagree, the conflict triggers re-evaluation. (Chapter 4: Error-Correcting Codes and Memory Reconstruction)

**Current ACMS Behavior:** ACMS_Raw_v1 and ACMS_Knowledge_v2 store different representations of the same information. They're searched in parallel and results are merged, but there's no consistency check between them.

**Implementation:**

New file: `src/intelligence/cross_validator.py`

```python
class CrossValidator:
    """
    Error detection via cross-collection consistency checking.

    When raw Q&A and extracted knowledge diverge beyond a threshold,
    flag for reconsolidation. This catches:
    - Stale knowledge (technology changed since extraction)
    - Extraction errors (LLM misinterpreted the Q&A)
    - Superseded information (user corrected themselves in a later session)
    """

    CONSISTENCY_THRESHOLD = 0.70

    async def validate_retrieval(self,
                                  raw_results: List[RawResult],
                                  knowledge_results: List[KnowledgeResult]
                                  ) -> ValidationReport:
        """
        Run during retrieval (or as a batch job on high-access items).
        """
        inconsistencies = []

        for raw in raw_results:
            # Find corresponding knowledge entries (same topic cluster)
            related_knowledge = [
                k for k in knowledge_results
                if self._topics_overlap(raw, k)
            ]

            for knowledge in related_knowledge:
                consistency = await self._compute_consistency(
                    raw.answer,
                    knowledge.answer_summary
                )

                if consistency < self.CONSISTENCY_THRESHOLD:
                    inconsistencies.append(InconsistencyRecord(
                        raw_id=raw.id,
                        knowledge_id=knowledge.id,
                        consistency_score=consistency,
                        raw_date=raw.created_at,
                        knowledge_date=knowledge.created_at,
                        resolution_hint=self._suggest_resolution(raw, knowledge)
                    ))

        return ValidationReport(
            checked_pairs=len(raw_results) * len(knowledge_results),
            inconsistencies=inconsistencies,
            needs_reconsolidation=len(inconsistencies) > 0
        )

    def _suggest_resolution(self, raw, knowledge) -> str:
        """Prefer the more recent representation."""
        if raw.created_at > knowledge.created_at:
            return "raw_is_newer_reconsolidate_knowledge"
        else:
            return "knowledge_is_newer_may_be_corrected"
```

**Integration points:**
1. During retrieval: Run lightweight consistency check on results before context assembly. If inconsistency detected, prefer the more recent representation and queue the pair for review.
2. As a weekly batch job: Cross-validate high-access knowledge items to catch drift proactively.

**Expected Impact:**
- Catches knowledge drift before it affects user responses
- Maintains consistency across the dual-collection architecture
- Creates a self-healing knowledge base

---

## TIER 3: LARGER PROJECTS (2-4 Weeks Each)

---

### 3.1 Knowledge Compaction Tiers — LSM Tree-Inspired Consolidation

**Cognitive Principle:** The neocortex extracts abstractions from specific episodes, creating increasingly general knowledge representations. The brain doesn't just store individual memories — it builds schemas. (Chapter 4: LSM Trees and Memory Tier Migration)

**Current ACMS Behavior:** Two storage levels — Raw Q&A (ACMS_Raw_v1) and Individual Knowledge entries (ACMS_Knowledge_v2). No higher-order knowledge synthesis.

**Proposed Architecture:**

```
Level 0: ACMS_Raw_v1 (existing)
    Individual Q&A pairs with embeddings
    Example: "How do I implement OAuth2 refresh tokens?" → [answer]

Level 1: ACMS_Knowledge_v2 (existing)
    Extracted entities, relations, intent
    Example: Entity(OAuth2, protocol), Entity(refresh_token, mechanism),
             Relation(OAuth2, USES, refresh_token)

Level 2: ACMS_Topics_v1 (NEW — Topic Summaries)
    Merged knowledge per topic cluster
    Example: "OAuth2 — User has explored: authorization code flow,
             refresh token implementation, service account auth.
             Primary concern: token lifecycle management.
             Knowledge depth: intermediate (15 interactions).
             Key entities: OAuth2, JWT, refresh_token, PKCE, RBAC.
             Knowledge gaps: PKCE implementation, token revocation."

Level 3: ACMS_Domains_v1 (NEW — Domain Maps)
    Cross-topic relationship maps
    Example: "API Security Domain — User's knowledge topology:
             Strong: OAuth2 (15), JWT (12), HTTPS (8)
             Moderate: CORS (4), Rate Limiting (3)
             Weak: API Key rotation (1), mTLS (0)
             Key relationships: OAuth2→JWT (uses), JWT→HTTPS (requires),
             OAuth2→PKCE (recommended_with)
             Emerging concern: Service account authentication across
             Kubernetes and cloud APIs (cross-domain bridge)."
```

**Implementation:** New compaction job in `src/jobs/knowledge_compaction.py`

```python
class KnowledgeCompactor:
    """
    LSM-tree-inspired compaction for ACMS knowledge.

    Level 1 → Level 2: Merge related knowledge entries into topic summaries
    Level 2 → Level 3: Merge topic summaries into domain maps

    Runs weekly as part of intelligence pipeline.
    Schedule: After insight generation (Stage 2), before weekly reports (Stage 3).
    """

    async def compact_to_topic_summaries(self):
        """Level 1 → Level 2 compaction."""
        clusters = await get_topic_clusters()

        for cluster in clusters:
            entries = await get_knowledge_entries(topic_slug=cluster.slug)

            if len(entries) < 3:
                continue  # Not enough data to summarize

            # Use Claude to synthesize topic summary
            summary = await self._synthesize_topic_summary(
                topic=cluster.slug,
                entries=entries,
                model="claude-sonnet-4-20250514"
            )

            await upsert_topic_summary(
                topic_slug=cluster.slug,
                summary=summary.text,
                entity_map=summary.entities,
                knowledge_depth=len(entries),
                knowledge_gaps=summary.identified_gaps,
                last_compacted=datetime.utcnow()
            )

    async def compact_to_domain_maps(self):
        """Level 2 → Level 3 compaction."""
        topic_summaries = await get_all_topic_summaries()

        # Group topics into domains using embedding clustering
        domains = await cluster_topics_into_domains(
            topics=topic_summaries,
            min_cluster_size=3
        )

        for domain in domains:
            domain_map = await self._synthesize_domain_map(
                domain_name=domain.name,
                topic_summaries=domain.topics,
                model="claude-sonnet-4-20250514"
            )

            await upsert_domain_map(
                domain_name=domain.name,
                topology=domain_map.topology,
                cross_topic_relationships=domain_map.relationships,
                knowledge_strengths=domain_map.strengths,
                knowledge_gaps=domain_map.gaps,
                emerging_themes=domain_map.emerging
            )
```

**Integration with context assembly:** Modify `src/gateway/context_assembler.py` to include topic summaries and domain maps in schema-driven context:

```python
async def assemble_context(query, intent, retrieval_results):
    # Existing: raw results + knowledge results
    context = existing_context_assembly(retrieval_results)

    # NEW: Add schema-level context if available
    topic_summary = await get_topic_summary_for_query(query)
    if topic_summary:
        context.schema_context = (
            f"User's knowledge context: {topic_summary.summary}\n"
            f"Knowledge depth in this area: {topic_summary.knowledge_depth} interactions\n"
            f"Identified gaps: {', '.join(topic_summary.knowledge_gaps)}"
        )

    return context
```

This is the **consolidation feedback loop** from Chapter 5 — consolidated knowledge about the user's cognitive state influences how new responses are generated.

**Expected Impact:**
- Dramatically richer context assembly for repeat topics
- LLM agents can calibrate response depth to user's actual knowledge level
- Knowledge gaps become visible and actionable
- Domain maps enable the knowledge topology visualization (future UI work)

---

### 3.2 Creative Recombination — Cross-Domain Insight Discovery

**Cognitive Principle:** During REM sleep, the brain recombines stored patterns in novel configurations, discovering connections between seemingly unrelated experiences. (Chapter 2: Sleep Consolidation Engine — REM phase)

**Current ACMS Behavior:** Insights engine (`src/intelligence/insights_engine.py`) detects patterns within topic clusters but doesn't systematically look for connections across distant clusters.

**Implementation:**

New file: `src/jobs/creative_recombination.py`

```python
class CreativeRecombinator:
    """
    'REM sleep' for ACMS: find unexpected connections across
    distant topic clusters.

    Runs weekly during low-activity period.
    Schedule: Sunday 3AM (after insight generation, before weekly reports).
    """

    async def discover_cross_domain_connections(self):
        """
        For each pair of distant topic clusters, look for:
        1. Shared entities (same concept appearing in different domains)
        2. Structural analogies (similar relationship patterns)
        3. Bridging queries (queries that touch both clusters)
        """
        clusters = await get_topic_clusters(min_size=3)

        discoveries = []
        for cluster_a, cluster_b in itertools.combinations(clusters, 2):
            # Skip clusters that are already known to be related
            if self._clusters_are_adjacent(cluster_a, cluster_b):
                continue

            # Check 1: Shared entities
            shared = set(cluster_a.entities) & set(cluster_b.entities)
            if shared:
                discoveries.append(CrossDomainInsight(
                    type="shared_entity",
                    cluster_a=cluster_a.slug,
                    cluster_b=cluster_b.slug,
                    connection=f"Shared concepts: {', '.join(shared)}",
                    strength=len(shared) / min(
                        len(cluster_a.entities),
                        len(cluster_b.entities)
                    )
                ))

            # Check 2: Bridging queries
            bridge_queries = await find_queries_touching_both(
                cluster_a.slug, cluster_b.slug
            )
            if bridge_queries:
                discoveries.append(CrossDomainInsight(
                    type="bridging_queries",
                    cluster_a=cluster_a.slug,
                    cluster_b=cluster_b.slug,
                    connection=f"{len(bridge_queries)} queries bridge these topics",
                    evidence_ids=[q.id for q in bridge_queries]
                ))

        # Filter to non-obvious discoveries and store
        novel_discoveries = [d for d in discoveries if d.strength > 0.2]
        for discovery in novel_discoveries:
            await store_insight(
                insight_type="cross_domain_connection",
                title=f"Connection: {discovery.cluster_a} ↔ {discovery.cluster_b}",
                description=discovery.connection,
                evidence=discovery.evidence_ids,
                trust_level=TrustLevel.MEDIUM
            )

        return novel_discoveries
```

**Expected Impact:**
- Surfaces non-obvious connections in the user's knowledge
- Directly implements the "generative memory" concept from Chapter 5
- Enriches weekly reports with cross-domain insights
- Potential to surprise and delight ("I hadn't connected those topics")

---

### 3.3 Schema-Driven Context Assembly — The Consolidation Feedback Loop

**Cognitive Principle:** Consolidated cortical knowledge influences subsequent hippocampal encoding. What you already know shapes how you process new information. Experts encode differently than novices because their schemas filter and organize incoming data. (Chapter 5: The Consolidation Feedback Loop)

**Current ACMS Behavior:** Context assembly provides raw past interactions to the LLM agent. The agent doesn't receive a model of the user's knowledge state, learning trajectory, or expertise level in the query's domain.

**Implementation:**

Modify `src/gateway/context_assembler.py`:

```python
async def build_schema_context(user_id: str, query: str,
                                 detected_topic: str) -> Optional[str]:
    """
    Build a cognitive state model for the LLM agent.

    This is the consolidation feedback loop: knowledge about
    what the user knows shapes how new knowledge is generated.
    """
    # Get topic summary if available (from compaction tiers)
    topic = await get_topic_summary(user_id, detected_topic)
    if not topic:
        return None

    # Get user's interaction history with this topic
    history_stats = await get_topic_interaction_stats(user_id, detected_topic)

    # Build cognitive state model
    schema = f"""USER KNOWLEDGE CONTEXT (for response calibration):
- Topic: {detected_topic}
- User's depth: {history_stats.total_interactions} past interactions
- Expertise estimate: {_estimate_expertise(history_stats)}
- Known concepts: {', '.join(topic.strong_entities[:10])}
- Identified gaps: {', '.join(topic.knowledge_gaps[:5])}
- Preferred response style: {history_stats.preferred_style}
- Last engagement: {history_stats.last_interaction_date}

Calibration guidance:
- {"Skip foundational explanations — user has strong background" if history_stats.total_interactions > 10 else "Include brief context — user is still building foundation"}
- {"User prefers code examples over conceptual explanations" if history_stats.code_preference > 0.6 else "Balance conceptual and practical content"}
- {"Address knowledge gap: " + topic.knowledge_gaps[0] if topic.knowledge_gaps else "No specific gaps identified"}
"""
    return schema

def _estimate_expertise(stats) -> str:
    if stats.total_interactions > 20 and stats.avg_depth > 0.7:
        return "advanced"
    elif stats.total_interactions > 8:
        return "intermediate"
    elif stats.total_interactions > 2:
        return "beginner"
    else:
        return "first_encounter"
```

**Integration:** Inject `schema_context` into the system prompt sent to the LLM agent in `src/gateway/orchestrator.py` Step 6 (Agent Execution).

**Expected Impact:**
- Responses calibrated to actual user expertise (no more re-explaining basics to experts)
- Knowledge gaps addressed proactively
- The system develops a genuine model of the user's cognitive state
- This is the mechanism that transforms ACMS from "memory system" to "cognitive partner" (Chapter 5)

---

## IMPLEMENTATION PRIORITY MATRIX

| # | Improvement | Effort | Impact | Cognitive Principle | Files Modified |
|---|---|---|---|---|---|
| 1.1 | Consolidation Triage | 1-2 days | High (cost) | Selective hippocampal replay | intelligence_jobs.py |
| 1.2 | Adaptive Thresholds | 1-2 days | High (quality) | Pattern sep/completion | engine.py |
| 1.3 | Propagated Forgetting | 1 day | Medium (integrity) | Active forgetting cascade | quality_cache.py |
| 2.1 | Preflight Knowledge Check | 1 week | Medium (latency) | Feeling of knowing | NEW: knowledge_preflight.py, orchestrator.py |
| 2.2 | Salience Scoring | 1 week | High (quality) | Amygdala priority queue | NEW: salience_scorer.py, intelligence_jobs.py |
| 2.3 | Co-Retrieval Graph | 1-2 weeks | High (UX) | Hebbian learning | NEW: coretrieval_graph.py, engine.py |
| 2.4 | Cross-Validation | 1 week | Medium (integrity) | Error-correcting codes | NEW: cross_validator.py |
| 3.1 | Knowledge Compaction | 2-3 weeks | Very High (core) | LSM tree consolidation | NEW: knowledge_compaction.py, context_assembler.py |
| 3.2 | Creative Recombination | 1-2 weeks | Medium (insight) | REM sleep recombination | NEW: creative_recombination.py |
| 3.3 | Schema-Driven Context | 2 weeks | Very High (core) | Consolidation feedback loop | context_assembler.py, orchestrator.py |

---

## RECOMMENDED IMPLEMENTATION ORDER

**Sprint 1 (Week 1-2):** Tier 1 items (1.1, 1.2, 1.3)
- Immediate cost savings from consolidation triage
- Better retrieval quality from adaptive thresholds
- Data integrity from propagated forgetting

**Sprint 2 (Week 3-4):** Tier 2 items (2.1, 2.2)
- Latency improvement from preflight check
- Quality improvement from salience scoring
- These feed into Sprint 3 items

**Sprint 3 (Week 5-7):** Co-retrieval graph (2.3) + Cross-validation (2.4)
- Hebbian association network
- Error detection across collections
- These require some data accumulation before they're useful

**Sprint 4 (Week 8-11):** Tier 3 items (3.1, 3.3)
- Knowledge compaction is the highest-impact single improvement
- Schema-driven context is the mechanism that makes compaction useful
- These two should be built together

**Sprint 5 (Week 12-13):** Creative recombination (3.2)
- Requires compaction tiers to exist (needs Level 2 topic summaries)
- The "cherry on top" — the feature that makes ACMS feel genuinely intelligent

---

## ARCHITECTURAL PRINCIPLE

Every improvement in this document follows a single meta-principle derived from the reading series:

**The highest-value memory systems are not databases. They are reconstruction engines.**

ACMS already embodies this at its core — the LLM-based response generation is inherently reconstructive. These improvements extend the principle deeper into the architecture: selective consolidation, adaptive retrieval, associative pre-loading, cross-domain discovery, and schema-driven context assembly are all mechanisms for making reconstruction more intelligent, more personalized, and more valuable.

The memory palace was powerful because it organized meaningfully. ACMS has the storage. These improvements add the meaning.
