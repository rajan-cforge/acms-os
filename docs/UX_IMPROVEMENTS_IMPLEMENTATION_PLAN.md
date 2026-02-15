# ACMS UX Improvements - TDD Implementation Plan

> **Created:** February 6, 2026
> **Methodology:** Agent-Based TDD Workflow
> **Duration:** 12 weeks (6 sprints × 2 weeks)

---

## SDLC Agent Workflow

Every feature follows this rigorous loop:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AGENT-BASED TDD WORKFLOW                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PHASE 1: PM ↔ Dev Architect Loop                                       │
│  ─────────────────────────────────────────────────────────────────────  │
│  • PM defines requirements, acceptance criteria, UX scenarios           │
│  • Dev Architect proposes technical design                              │
│  • Loop until PM approves all requirements are addressable              │
│  • Output: Approved technical spec with PM sign-off                     │
│                                                                         │
│  PHASE 2: Dev Architect ↔ Developer Loop                                │
│  ─────────────────────────────────────────────────────────────────────  │
│  • Dev Architect breaks down into implementation tasks                  │
│  • Developer writes tests FIRST (TDD), then implementation              │
│  • Loop until Architect approves code meets design                      │
│  • Output: Implemented code with passing unit tests                     │
│                                                                         │
│  PHASE 3: Developer ↔ QA Loop                                           │
│  ─────────────────────────────────────────────────────────────────────  │
│  • QA defines test scenarios (API + UI/UX)                              │
│  • Developer implements integration tests                               │
│  • QA runs comprehensive test suite                                     │
│  • Loop until QA approves all scenarios pass                            │
│  • Output: Full test coverage, QA sign-off                              │
│                                                                         │
│  PHASE 4: PM Final Review                                               │
│  ─────────────────────────────────────────────────────────────────────  │
│  • PM reviews implemented feature against original requirements         │
│  • PM validates UX scenarios work as specified                          │
│  • PM provides final sign-off or requests changes                       │
│  • Output: Feature approved for merge                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Test Directory Structure

```
tests/
├── unit/
│   ├── views/                    # NEW: Frontend view logic tests
│   │   ├── test_memory_clustering.py
│   │   ├── test_knowledge_consolidation.py
│   │   ├── test_confidence_scoring.py
│   │   └── test_domain_taxonomy.py
│   ├── cache/
│   ├── feedback/
│   ├── intelligence/
│   │   ├── test_cluster_discovery.py      # NEW
│   │   ├── test_knowledge_consolidator.py # NEW
│   │   └── test_confidence_decay.py       # NEW
│   └── api/
│       ├── test_clusters_endpoints.py     # NEW
│       ├── test_knowledge_v2_endpoints.py # NEW
│       └── test_financial_constitution.py # NEW
├── integration/
│   ├── test_memory_clustering_flow.py     # NEW
│   ├── test_knowledge_provenance.py       # NEW
│   └── test_financial_rules_engine.py     # NEW
├── e2e/
│   ├── test_memories_view.py              # NEW
│   ├── test_knowledge_view.py             # NEW
│   ├── test_financial_view.py             # NEW
│   └── test_reports_view.py               # NEW
└── fixtures/
    ├── memory_clusters.json               # NEW
    ├── consolidated_knowledge.json        # NEW
    └── financial_rules.json               # NEW
```

---

## Sprint Overview

| Sprint | Weeks | Focus | Backend | Frontend |
|--------|-------|-------|---------|----------|
| **1** | 1-2 | Foundation + Design System | CSS variables, component library | Expandable cards |
| **2** | 3-4 | Memory Clustering | cluster tables, discovery job | Timeline view, click-to-expand |
| **3** | 5-6 | Knowledge Consolidation | consolidated_knowledge, provenance | Domain tree, confidence UI |
| **4** | 7-8 | Financial Constitution | rules engine, violations | Rule builder, alerts |
| **5** | 9-10 | Reports & Insights | trend snapshots, SCAR insights | Charts, visualizations |
| **6** | 11-12 | Polish & Integration | Performance, edge cases | Animations, accessibility |

---

# SPRINT 1: Foundation + Design System (Weeks 1-2)

## PM Requirements

### Feature: F1.1 - CSS Design System
**User Story:** As a developer, I want a consistent design system so that all views have unified styling.

**Acceptance Criteria:**
- [ ] Typography scale defined (hero, h1, h2, h3, body, small, micro)
- [ ] Spacing scale defined (8px base grid)
- [ ] Color palette defined (backgrounds, accents, semantic colors)
- [ ] Border and shadow tokens defined
- [ ] All existing views use new CSS variables

### Feature: F1.2 - Expandable Card Component
**User Story:** As a user, I want to click on any card to see more details without navigating away.

**Acceptance Criteria:**
- [ ] Card shows collapsed state with preview content
- [ ] Click expands with smooth animation (300ms)
- [ ] Expanded state shows full content
- [ ] Click again or outside collapses
- [ ] Keyboard accessible (Enter to expand, Escape to collapse)

### Feature: F1.3 - Skeleton Loading States
**User Story:** As a user, I want to see loading indicators that match the content shape so I know data is loading.

**Acceptance Criteria:**
- [ ] Skeleton components for text, cards, stats
- [ ] Shimmer animation effect
- [ ] Replace all "Loading..." text with skeletons

---

## Architect Design

### F1.1 - CSS Design System

**Files to Create:**
```
desktop-app/src/renderer/styles/
├── design-tokens.css      # All CSS variables
├── typography.css         # Font styles
├── components.css         # Reusable component classes
└── animations.css         # Transition definitions
```

**CSS Variables:**
```css
:root {
  /* Typography */
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --text-hero: 32px;
  --text-h1: 24px;
  --text-h2: 18px;
  --text-h3: 16px;
  --text-body: 15px;
  --text-small: 13px;
  --text-micro: 11px;

  /* Spacing (8px grid) */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;

  /* Colors */
  --bg-app: #0D0D0D;
  --bg-surface: #141414;
  --bg-elevated: #1A1A1A;
  --bg-overlay: #242424;

  --text-primary: #F5F5F5;
  --text-secondary: #A0A0A0;
  --text-tertiary: #666666;

  --accent-green: #4CAF50;
  --accent-blue: #2196F3;
  --accent-purple: #9333EA;
  --accent-orange: #FF9800;
  --accent-red: #EF4444;

  /* Borders */
  --border-subtle: rgba(255,255,255,0.06);
  --border-default: rgba(255,255,255,0.10);
  --border-emphasis: rgba(255,255,255,0.16);

  /* Shadows */
  --shadow-sm: 0 2px 4px rgba(0,0,0,0.1);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.15);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.2);
  --shadow-glow: 0 0 20px rgba(76,175,80,0.15);

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  /* Transitions */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 350ms;
}
```

### F1.2 - Expandable Card Component

**File:** `desktop-app/src/renderer/components/expandable-card.js`

**API:**
```javascript
class ExpandableCard {
  constructor(options) {
    this.id = options.id;
    this.collapsedContent = options.collapsedContent;  // HTML string
    this.expandedContent = options.expandedContent;    // HTML string or async function
    this.onExpand = options.onExpand;                  // callback
    this.onCollapse = options.onCollapse;              // callback
  }

  render() → HTMLElement
  expand() → void
  collapse() → void
  toggle() → void
  isExpanded() → boolean
}
```

---

## TDD Test Specifications

### Unit Tests: Design System

**File:** `tests/unit/frontend/test_design_system.py`

```python
# Test that all CSS variables are defined
def test_typography_variables_exist():
    """All typography CSS variables must be defined."""
    required = ['--text-hero', '--text-h1', '--text-h2', '--text-h3',
                '--text-body', '--text-small', '--text-micro']
    # Parse CSS file and verify

def test_spacing_scale_is_8px_based():
    """Spacing scale must follow 8px grid."""
    # --space-2 should be 8px, --space-4 should be 16px, etc.

def test_color_contrast_accessibility():
    """Text colors must have sufficient contrast against backgrounds."""
    # WCAG AA: 4.5:1 for normal text, 3:1 for large text
```

### Unit Tests: Expandable Card

**File:** `desktop-app/tests/components/expandable-card.test.js`

```javascript
describe('ExpandableCard', () => {
  describe('initialization', () => {
    test('renders in collapsed state by default', () => {
      const card = new ExpandableCard({
        id: 'test-1',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full content</p>'
      });
      const el = card.render();
      expect(el.classList.contains('expanded')).toBe(false);
    });

    test('shows collapsed content initially', () => {
      // ...
    });
  });

  describe('expand/collapse', () => {
    test('click expands the card', () => {
      // ...
    });

    test('expand animation takes 300ms', () => {
      // ...
    });

    test('escape key collapses expanded card', () => {
      // ...
    });

    test('clicking outside collapses expanded card', () => {
      // ...
    });
  });

  describe('accessibility', () => {
    test('card is focusable', () => {
      // tabindex="0"
    });

    test('enter key expands card', () => {
      // ...
    });

    test('has aria-expanded attribute', () => {
      // ...
    });
  });

  describe('callbacks', () => {
    test('onExpand is called when expanding', () => {
      // ...
    });

    test('onCollapse is called when collapsing', () => {
      // ...
    });
  });
});
```

### Integration Tests

**File:** `tests/integration/test_design_system_integration.py`

```python
def test_all_views_use_design_tokens():
    """All view CSS should use design tokens, not hardcoded values."""
    # Scan CSS files for hardcoded colors like #fff, #000
    # Should find none - all should use var(--xxx)

def test_expandable_card_in_memories_view():
    """Memory cards should be expandable."""
    # Load memories view, verify cards have expandable behavior
```

### E2E Tests

**File:** `desktop-app/tests/e2e/design-system.spec.js`

```javascript
const { test, expect } = require('@playwright/test');

test.describe('Design System', () => {
  test('typography renders correctly', async ({ page }) => {
    await page.goto('/');
    // Check that text sizes match design tokens
  });

  test('expandable card animates smoothly', async ({ page }) => {
    await page.goto('/#memories');
    const card = page.locator('.expandable-card').first();
    await card.click();
    // Verify animation completes
    await expect(card).toHaveClass(/expanded/);
  });

  test('skeleton loading appears before content', async ({ page }) => {
    // Throttle network
    await page.route('**/memories*', route =>
      route.fulfill({ status: 200, body: '[]', delay: 1000 })
    );
    await page.goto('/#memories');
    await expect(page.locator('.skeleton')).toBeVisible();
  });
});
```

---

## QA Test Scenarios

| ID | Scenario | Steps | Expected | Priority |
|----|----------|-------|----------|----------|
| S1.1 | Design tokens applied | Load any view | No hardcoded colors visible | P0 |
| S1.2 | Card expand click | Click collapsed card | Expands with animation | P0 |
| S1.3 | Card collapse click | Click expanded card | Collapses with animation | P0 |
| S1.4 | Keyboard expand | Focus card, press Enter | Card expands | P1 |
| S1.5 | Keyboard collapse | Focus expanded, press Esc | Card collapses | P1 |
| S1.6 | Skeleton loading | Slow network | Skeletons visible during load | P1 |
| S1.7 | Click outside collapse | Click outside expanded card | Card collapses | P2 |

---

## Sign-off Checklist: Sprint 1

- [ ] **PM Sign-off**: Design system meets requirements
- [ ] **Architect Sign-off**: CSS structure is maintainable
- [ ] **Dev Sign-off**: All unit tests passing (target: 15+ tests)
- [ ] **QA Sign-off**: All 7 scenarios pass

---

# SPRINT 2: Memory Clustering (Weeks 3-4)

## PM Requirements

### Feature: F2.1 - Memory Clusters Backend
**User Story:** As a system, I need to automatically group related memories so users see coherent topics.

**Acceptance Criteria:**
- [ ] Memories are grouped by semantic similarity
- [ ] Each cluster has a canonical topic name
- [ ] Clusters track member count and date range
- [ ] New memories are assigned to existing clusters or create new ones
- [ ] Clusters can be browsed via API

### Feature: F2.2 - Timeline View
**User Story:** As a user, I want to see my conversations organized by time with topic groupings.

**Acceptance Criteria:**
- [ ] Memories displayed in reverse chronological order
- [ ] Date headers separate time periods
- [ ] Related memories show cluster badge
- [ ] Quick filter by topic cluster
- [ ] Search filters timeline in real-time

### Feature: F2.3 - Click-to-Expand Memory
**User Story:** As a user, I want to click a memory to see the full conversation and what knowledge was extracted.

**Acceptance Criteria:**
- [ ] Click shows full Q&A content
- [ ] Shows "Knowledge extracted: X items" with links
- [ ] Shows related memories in same cluster
- [ ] Can edit tags
- [ ] Can delete memory (with confirmation)

---

## Architect Design

### Database Schema

**File:** `migrations/018_memory_clusters.sql`

```sql
-- Memory Clusters: Groups of related memories by topic
CREATE TABLE memory_clusters (
    cluster_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',

    -- Identity
    canonical_topic TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,

    -- Aggregates
    member_count INT DEFAULT 0,
    first_memory_at TIMESTAMPTZ,
    last_memory_at TIMESTAMPTZ,
    avg_quality_score FLOAT DEFAULT 0.5,

    -- Weaviate
    centroid_vector_id TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mc_user ON memory_clusters(user_id);
CREATE INDEX idx_mc_topic ON memory_clusters(canonical_topic);

-- Cluster Membership
CREATE TABLE memory_cluster_members (
    cluster_id UUID REFERENCES memory_clusters(cluster_id) ON DELETE CASCADE,
    memory_id UUID NOT NULL,
    similarity_score FLOAT,
    is_canonical BOOLEAN DEFAULT FALSE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (cluster_id, memory_id)
);

CREATE INDEX idx_mcm_memory ON memory_cluster_members(memory_id);
```

### Background Job

**File:** `src/jobs/cluster_discovery.py`

```python
class ClusterDiscoveryJob:
    """
    Weekly job to discover and update memory clusters.

    Algorithm:
    1. Fetch all unassigned memories
    2. Get embeddings from Weaviate
    3. Run DBSCAN clustering (eps=0.15, min_samples=3)
    4. For each cluster:
       - Generate display name via LLM
       - Compute centroid
       - Create/update memory_clusters record
    5. Assign memories to clusters
    """

    async def run(self):
        pass

    async def _fetch_unassigned_memories(self) -> List[str]:
        pass

    async def _cluster_embeddings(self, embeddings: np.ndarray) -> List[List[int]]:
        pass

    async def _generate_cluster_name(self, sample_contents: List[str]) -> str:
        pass

    async def _assign_to_cluster(self, memory_id: str, cluster_id: str, similarity: float):
        pass
```

### API Endpoints

**File:** `src/api/clusters_endpoints.py`

```python
router = APIRouter(prefix="/api/v2/clusters", tags=["clusters"])

@router.get("")
async def list_clusters(
    user_id: str = "default",
    limit: int = 50,
    offset: int = 0,
) -> ClustersResponse:
    """List memory clusters with member counts."""
    pass

@router.get("/{cluster_id}")
async def get_cluster(cluster_id: str) -> ClusterDetail:
    """Get cluster with member memories."""
    pass

@router.get("/{cluster_id}/members")
async def get_cluster_members(
    cluster_id: str,
    limit: int = 20,
    offset: int = 0,
) -> ClusterMembersResponse:
    """Get memories in a cluster."""
    pass
```

---

## TDD Test Specifications

### Unit Tests: Cluster Discovery

**File:** `tests/unit/intelligence/test_cluster_discovery.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.jobs.cluster_discovery import ClusterDiscoveryJob

class TestClusterDiscovery:

    @pytest.fixture
    def job(self):
        return ClusterDiscoveryJob(db_pool=MagicMock())

    def test_cluster_embeddings_groups_similar_items(self, job):
        """Similar embeddings should be in same cluster."""
        # Create embeddings where items 0,1,2 are similar, 3,4,5 are similar
        embeddings = np.array([
            [1.0, 0.0, 0.0],  # Group A
            [0.99, 0.01, 0.0],
            [0.98, 0.02, 0.0],
            [0.0, 1.0, 0.0],  # Group B
            [0.01, 0.99, 0.0],
            [0.02, 0.98, 0.0],
        ])

        clusters = job._cluster_embeddings(embeddings)

        assert len(clusters) == 2
        assert set(clusters[0]) == {0, 1, 2}
        assert set(clusters[1]) == {3, 4, 5}

    def test_noise_points_not_assigned(self, job):
        """Outlier embeddings should not be forced into clusters."""
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.99, 0.01, 0.0],
            [0.98, 0.02, 0.0],
            [0.5, 0.5, 0.0],  # Outlier
        ])

        clusters = job._cluster_embeddings(embeddings)

        # Outlier should not be in any cluster
        all_assigned = set()
        for cluster in clusters:
            all_assigned.update(cluster)
        assert 3 not in all_assigned

    @pytest.mark.asyncio
    async def test_generate_cluster_name_uses_llm(self, job):
        """Cluster names should be generated from sample content."""
        samples = [
            "How do I use async/await in Python?",
            "What's the best way to handle concurrent tasks?",
            "Explain Python asyncio event loop",
        ]

        job.llm_client = AsyncMock()
        job.llm_client.generate.return_value = "Python Async Programming"

        name = await job._generate_cluster_name(samples)

        assert name == "Python Async Programming"
        job.llm_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_to_cluster_creates_membership(self, job):
        """Assigning memory to cluster creates membership record."""
        job.db = AsyncMock()

        await job._assign_to_cluster(
            memory_id="mem-123",
            cluster_id="cluster-456",
            similarity=0.92
        )

        job.db.execute.assert_called()
        # Verify INSERT INTO memory_cluster_members
```

### Unit Tests: Clusters API

**File:** `tests/unit/api/test_clusters_endpoints.py`

```python
import pytest
from fastapi.testclient import TestClient
from src.api_server import app

class TestClustersAPI:

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_list_clusters_returns_array(self, client):
        """GET /api/v2/clusters returns array of clusters."""
        response = client.get("/api/v2/clusters")
        assert response.status_code == 200
        assert "clusters" in response.json()
        assert isinstance(response.json()["clusters"], list)

    def test_list_clusters_includes_member_count(self, client):
        """Each cluster should have member_count field."""
        response = client.get("/api/v2/clusters")
        if response.json()["clusters"]:
            cluster = response.json()["clusters"][0]
            assert "member_count" in cluster

    def test_get_cluster_includes_members(self, client):
        """GET /api/v2/clusters/{id} returns cluster with members."""
        # First create a cluster, then fetch it
        pass

    def test_get_cluster_404_for_nonexistent(self, client):
        """GET /api/v2/clusters/{invalid_id} returns 404."""
        response = client.get("/api/v2/clusters/nonexistent-id")
        assert response.status_code == 404
```

### Integration Tests

**File:** `tests/integration/test_memory_clustering_flow.py`

```python
@pytest.mark.integration
class TestMemoryClusteringFlow:

    @pytest.mark.asyncio
    async def test_full_clustering_pipeline(self):
        """
        End-to-end test:
        1. Insert 10 memories (5 about Python, 5 about Kubernetes)
        2. Run cluster discovery job
        3. Verify 2 clusters created
        4. Verify members assigned correctly
        """
        pass

    @pytest.mark.asyncio
    async def test_new_memory_assigned_to_existing_cluster(self):
        """
        When a new memory is added that's similar to existing cluster,
        it should be assigned to that cluster.
        """
        pass
```

### E2E Tests: Memories View

**File:** `desktop-app/tests/e2e/memories-view.spec.js`

```javascript
const { test, expect } = require('@playwright/test');

test.describe('Memories View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/#memories');
  });

  test('displays timeline with date headers', async ({ page }) => {
    await expect(page.locator('.timeline-header')).toBeVisible();
    await expect(page.locator('.date-divider')).toHaveCount.greaterThan(0);
  });

  test('memory card expands on click', async ({ page }) => {
    const card = page.locator('.memory-card').first();
    await card.click();
    await expect(card).toHaveClass(/expanded/);
    await expect(card.locator('.full-content')).toBeVisible();
  });

  test('expanded memory shows extracted knowledge', async ({ page }) => {
    const card = page.locator('.memory-card').first();
    await card.click();
    await expect(card.locator('.knowledge-extracted')).toBeVisible();
  });

  test('cluster badge links to filtered view', async ({ page }) => {
    const badge = page.locator('.cluster-badge').first();
    const clusterName = await badge.textContent();
    await badge.click();
    await expect(page.locator('.active-filter')).toContainText(clusterName);
  });

  test('search filters memories in real-time', async ({ page }) => {
    await page.fill('.search-input', 'python');
    await page.waitForTimeout(400); // debounce
    const cards = page.locator('.memory-card');
    for (const card of await cards.all()) {
      await expect(card).toContainText(/python/i);
    }
  });
});
```

---

## QA Test Scenarios

| ID | Scenario | Steps | Expected | Priority |
|----|----------|-------|----------|----------|
| S2.1 | Clusters created | Run discovery job on 50+ memories | At least 3 clusters created | P0 |
| S2.2 | Cluster has members | View any cluster | Shows member memories | P0 |
| S2.3 | Timeline display | Open Memories view | Shows date headers | P0 |
| S2.4 | Click expand | Click memory card | Shows full Q&A | P0 |
| S2.5 | Shows knowledge | Expand memory | Shows "X items extracted" | P1 |
| S2.6 | Search filter | Type in search | Filters in <500ms | P1 |
| S2.7 | Cluster filter | Click cluster badge | Shows only that cluster | P1 |
| S2.8 | Delete memory | Click delete, confirm | Memory removed | P2 |
| S2.9 | Empty state | User with 0 memories | Shows helpful message | P2 |

---

## Sign-off Checklist: Sprint 2

- [ ] **PM Sign-off**: Timeline view meets requirements
- [ ] **Architect Sign-off**: Clustering algorithm is correct
- [ ] **Dev Sign-off**: All unit tests passing (target: 25+ tests)
- [ ] **QA Sign-off**: All 9 scenarios pass

---

# SPRINT 3: Knowledge Consolidation (Weeks 5-6)

## PM Requirements

### Feature: F3.1 - Consolidated Knowledge Backend
**User Story:** As a system, I need to merge duplicate knowledge items into single authoritative entries.

**Acceptance Criteria:**
- [ ] Similar facts consolidated (similarity > 0.9)
- [ ] Each consolidated item tracks all source conversations
- [ ] Confidence increases with more sources
- [ ] User verification boosts confidence by 0.25

### Feature: F3.2 - Knowledge Provenance
**User Story:** As a user, I want to see where each knowledge item came from.

**Acceptance Criteria:**
- [ ] Click knowledge → see source conversations
- [ ] Shows contribution type (original, confirmation, refinement)
- [ ] Shows extraction confidence at each stage
- [ ] Can navigate to source conversation

### Feature: F3.3 - Domain Tree Navigation
**User Story:** As a user, I want to browse knowledge by domain/topic.

**Acceptance Criteria:**
- [ ] Left panel shows domain tree
- [ ] Domains show knowledge count
- [ ] Click domain filters knowledge list
- [ ] Nested domains (Technology > Python > Async)

### Feature: F3.4 - Confidence Visualization
**User Story:** As a user, I want to see how confident the system is about each fact.

**Acceptance Criteria:**
- [ ] Visual indicator (dots: ●●●○○)
- [ ] Color coding (green=verified, yellow=medium, red=low)
- [ ] Tooltip shows confidence factors
- [ ] Low confidence items show "Needs Review" badge

---

## Architect Design

### Database Schema

**File:** `migrations/019_consolidated_knowledge.sql`

```sql
-- Consolidated Knowledge: Merged authoritative facts
CREATE TABLE consolidated_knowledge (
    knowledge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',

    -- Content
    canonical_content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    knowledge_type TEXT, -- fact, preference, definition, procedure

    -- Domain
    domain_path TEXT, -- 'technology/python/async'

    -- Confidence
    base_confidence FLOAT DEFAULT 0.5,
    source_count INT DEFAULT 1,
    source_boost FLOAT DEFAULT 0.0,
    verification_boost FLOAT DEFAULT 0.0,
    effective_confidence FLOAT GENERATED ALWAYS AS (
        LEAST(1.0, base_confidence + source_boost + verification_boost)
    ) STORED,

    -- Verification
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,

    -- Timestamps
    first_derived_at TIMESTAMPTZ DEFAULT NOW(),
    last_confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ck_confidence ON consolidated_knowledge(effective_confidence DESC);
CREATE INDEX idx_ck_domain ON consolidated_knowledge(domain_path);
CREATE INDEX idx_ck_verified ON consolidated_knowledge(is_verified);

-- Knowledge Provenance: Source attribution
CREATE TABLE knowledge_provenance (
    provenance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_id UUID REFERENCES consolidated_knowledge(knowledge_id) ON DELETE CASCADE,

    source_type TEXT NOT NULL, -- 'query_history', 'memory_item', 'email'
    source_id UUID NOT NULL,
    source_timestamp TIMESTAMPTZ,
    source_preview TEXT, -- first 200 chars

    contribution_type TEXT, -- 'original', 'confirmation', 'refinement'
    confidence_at_extraction FLOAT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kp_knowledge ON knowledge_provenance(knowledge_id);

-- Knowledge Domains: Hierarchical taxonomy
CREATE TABLE knowledge_domains (
    domain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE, -- 'technology/python'
    display_name TEXT NOT NULL, -- 'Python'
    parent_path TEXT, -- 'technology'
    level INT NOT NULL DEFAULT 0,
    knowledge_count INT DEFAULT 0,
    icon TEXT,
    color TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Background Job

**File:** `src/jobs/knowledge_consolidation.py`

```python
class KnowledgeConsolidationJob:
    """
    Daily job to consolidate similar knowledge items.

    Algorithm:
    1. Fetch new knowledge items (last 24h)
    2. For each item:
       a. Search for similar consolidated_knowledge (similarity > 0.9)
       b. If found: increment source_count, update source_boost
       c. If not: create new consolidated_knowledge
    3. Create provenance records
    4. Update domain counts
    """

    async def run(self):
        pass
```

### API Endpoints

**File:** `src/api/knowledge_v2_endpoints.py`

```python
router = APIRouter(prefix="/api/v2/knowledge", tags=["knowledge-v2"])

@router.get("")
async def list_knowledge(
    domain: Optional[str] = None,
    min_confidence: float = 0.0,
    verified_only: bool = False,
    limit: int = 50,
) -> KnowledgeListResponse:
    """List consolidated knowledge items."""
    pass

@router.get("/{knowledge_id}")
async def get_knowledge(knowledge_id: str) -> KnowledgeDetail:
    """Get knowledge with full provenance chain."""
    pass

@router.post("/{knowledge_id}/verify")
async def verify_knowledge(knowledge_id: str) -> KnowledgeDetail:
    """Mark knowledge as verified, boost confidence."""
    pass

@router.get("/domains")
async def list_domains() -> DomainsResponse:
    """Get domain tree with counts."""
    pass
```

---

## TDD Test Specifications

### Unit Tests: Knowledge Consolidation

**File:** `tests/unit/intelligence/test_knowledge_consolidator.py`

```python
class TestKnowledgeConsolidation:

    def test_similar_facts_are_consolidated(self):
        """Facts with >0.9 similarity should merge."""
        fact1 = "FastAPI uses Pydantic for validation"
        fact2 = "Pydantic is used by FastAPI for data validation"

        consolidator = KnowledgeConsolidator()
        result = consolidator.should_consolidate(fact1, fact2)

        assert result == True

    def test_different_facts_not_consolidated(self):
        """Facts with <0.9 similarity should not merge."""
        fact1 = "FastAPI uses Pydantic for validation"
        fact2 = "Kubernetes uses YAML for configuration"

        consolidator = KnowledgeConsolidator()
        result = consolidator.should_consolidate(fact1, fact2)

        assert result == False

    def test_consolidation_increments_source_count(self):
        """When consolidating, source_count increases."""
        pass

    def test_source_boost_calculated_correctly(self):
        """source_boost = min(0.5, source_count * 0.05)"""
        pass

    def test_verification_boosts_confidence(self):
        """Verifying adds 0.25 to confidence."""
        pass
```

### Unit Tests: Confidence Scoring

**File:** `tests/unit/views/test_confidence_scoring.py`

```python
class TestConfidenceScoring:

    def test_effective_confidence_calculation(self):
        """effective = base + source_boost + verification_boost"""
        knowledge = ConsolidatedKnowledge(
            base_confidence=0.5,
            source_boost=0.15,
            verification_boost=0.25
        )

        assert knowledge.effective_confidence == 0.9

    def test_confidence_capped_at_1(self):
        """Confidence cannot exceed 1.0"""
        knowledge = ConsolidatedKnowledge(
            base_confidence=0.8,
            source_boost=0.5,
            verification_boost=0.25
        )

        assert knowledge.effective_confidence == 1.0

    def test_confidence_visual_indicator(self):
        """
        0.8-1.0 = ●●●●○ (green)
        0.6-0.8 = ●●●○○ (blue)
        0.4-0.6 = ●●○○○ (yellow)
        0.2-0.4 = ●○○○○ (orange)
        0.0-0.2 = ○○○○○ (red)
        """
        assert get_confidence_indicator(0.85) == ('●●●●○', 'green')
        assert get_confidence_indicator(0.65) == ('●●●○○', 'blue')
        assert get_confidence_indicator(0.45) == ('●●○○○', 'yellow')
        assert get_confidence_indicator(0.25) == ('●○○○○', 'orange')
        assert get_confidence_indicator(0.10) == ('○○○○○', 'red')
```

### E2E Tests: Knowledge View

**File:** `desktop-app/tests/e2e/knowledge-view.spec.js`

```javascript
test.describe('Knowledge View', () => {
  test('domain tree shows all domains with counts', async ({ page }) => {
    await page.goto('/#knowledge');
    const tree = page.locator('.domain-tree');
    await expect(tree).toBeVisible();
    await expect(tree.locator('.domain-item')).toHaveCount.greaterThan(0);
  });

  test('clicking domain filters knowledge list', async ({ page }) => {
    await page.goto('/#knowledge');
    const domain = page.locator('.domain-item').filter({ hasText: 'Python' });
    await domain.click();
    // All visible knowledge should be Python-related
  });

  test('confidence dots display correctly', async ({ page }) => {
    await page.goto('/#knowledge');
    const card = page.locator('.knowledge-card').first();
    await expect(card.locator('.confidence-dots')).toBeVisible();
  });

  test('click knowledge shows provenance', async ({ page }) => {
    await page.goto('/#knowledge');
    const card = page.locator('.knowledge-card').first();
    await card.click();
    await expect(page.locator('.provenance-list')).toBeVisible();
  });

  test('verify button boosts confidence', async ({ page }) => {
    await page.goto('/#knowledge');
    const card = page.locator('.knowledge-card').first();
    const initialConfidence = await card.locator('.confidence-value').textContent();
    await card.locator('.verify-btn').click();
    await expect(card.locator('.confidence-value')).not.toHaveText(initialConfidence);
  });
});
```

---

## Sign-off Checklist: Sprint 3

- [ ] **PM Sign-off**: Knowledge consolidation meets requirements
- [ ] **Architect Sign-off**: Provenance chain is complete
- [ ] **Dev Sign-off**: All unit tests passing (target: 35+ tests)
- [ ] **QA Sign-off**: All scenarios pass

---

# SPRINT 4: Financial Constitution (Weeks 7-8)

## PM Requirements

### Feature: F4.1 - Rule Builder
**User Story:** As a user, I want a guided conversation to define my financial rules.

**Acceptance Criteria:**
- [ ] Conversational wizard (not forms)
- [ ] Pre-built templates (Conservative, Balanced, Growth)
- [ ] Each rule explained in plain language
- [ ] Can add custom rules
- [ ] Summary before finalizing

### Feature: F4.2 - Rule Status Display
**User Story:** As a user, I want to see the status of all my financial rules at a glance.

**Acceptance Criteria:**
- [ ] Card per rule showing name, target, current, status
- [ ] Status colors: green (met), yellow (approaching), red (violated)
- [ ] Edit button on each rule
- [ ] Disable rule without deleting

### Feature: F4.3 - Violation Alerts
**User Story:** As a user, I want clear alerts when rules are violated with recommended actions.

**Acceptance Criteria:**
- [ ] Alert severity levels (info, warning, alert)
- [ ] AI-generated explanation of impact
- [ ] Action buttons: Acknowledge, Snooze, Adjust, Plan
- [ ] Snooze options: 1 week, 1 month, custom
- [ ] History of past violations

### Feature: F4.4 - Privacy Mode
**User Story:** As a privacy-conscious user, I want to hide dollar amounts.

**Acceptance Criteria:**
- [ ] Toggle between $ and % views
- [ ] Default can be set in preferences
- [ ] Dollar amounts NEVER sent to AI APIs
- [ ] AI recommendations work fully in % mode

---

## Architect Design

### Database Schema

**File:** `migrations/020_financial_constitution.sql`

```sql
-- Financial Rules: User-defined guardrails
CREATE TABLE financial_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',

    -- Rule definition
    rule_type TEXT NOT NULL, -- allocation, threshold, emergency_fund, concentration
    name TEXT NOT NULL,
    description TEXT,

    -- Parameters (JSONB for flexibility)
    parameters JSONB NOT NULL,
    -- Examples:
    -- allocation: {"asset_class": "stocks", "target_pct": 60, "tolerance_pct": 5}
    -- emergency_fund: {"target_months": 6}
    -- concentration: {"max_single_pct": 15}

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 1,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Rule Evaluations: Current status of each rule
CREATE TABLE rule_evaluations (
    evaluation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES financial_rules(rule_id) ON DELETE CASCADE,

    -- Evaluation result
    status TEXT NOT NULL, -- 'met', 'approaching', 'violated'
    current_value FLOAT,
    target_value FLOAT,
    deviation_pct FLOAT,

    -- AI commentary (no amounts)
    ai_explanation TEXT,
    ai_recommendation TEXT,

    evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Rule Alerts: Violations and user responses
CREATE TABLE rule_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES financial_rules(rule_id) ON DELETE CASCADE,
    evaluation_id UUID REFERENCES rule_evaluations(evaluation_id),

    severity TEXT NOT NULL, -- 'info', 'warning', 'alert'

    -- User response
    acknowledged_at TIMESTAMPTZ,
    snoozed_until TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## TDD Test Specifications

### Unit Tests: Rules Engine

**File:** `tests/unit/api/test_financial_constitution.py`

```python
class TestFinancialRulesEngine:

    def test_allocation_rule_met(self):
        """Rule is met when within tolerance."""
        rule = AllocationRule(target_pct=60, tolerance_pct=5)
        result = rule.evaluate(current_pct=62)

        assert result.status == 'met'

    def test_allocation_rule_approaching(self):
        """Rule is approaching when within 2% of limit."""
        rule = AllocationRule(target_pct=60, tolerance_pct=5)
        result = rule.evaluate(current_pct=64)

        assert result.status == 'approaching'

    def test_allocation_rule_violated(self):
        """Rule is violated when outside tolerance."""
        rule = AllocationRule(target_pct=60, tolerance_pct=5)
        result = rule.evaluate(current_pct=68)

        assert result.status == 'violated'

    def test_emergency_fund_rule(self):
        """Emergency fund evaluates months of expenses."""
        rule = EmergencyFundRule(target_months=6)
        result = rule.evaluate(current_months=4.2)

        assert result.status == 'violated'
        assert result.deviation_pct == pytest.approx(-30)

    def test_concentration_rule(self):
        """Concentration rule checks max single holding."""
        rule = ConcentrationRule(max_single_pct=15)
        holdings = [
            {'ticker': 'AAPL', 'pct': 18},
            {'ticker': 'MSFT', 'pct': 12},
        ]
        result = rule.evaluate(holdings)

        assert result.status == 'violated'
```

### E2E Tests: Financial View

**File:** `desktop-app/tests/e2e/financial-view.spec.js`

```javascript
test.describe('Financial Constitution', () => {
  test('rule builder wizard completes', async ({ page }) => {
    await page.goto('/#financial');
    await page.click('button:has-text("Set Up Constitution")');

    // Step 1: Investment style
    await page.click('button:has-text("Balanced")');
    await page.click('button:has-text("Next")');

    // Step 2: Allocation targets
    await page.click('button:has-text("Use These")');

    // Step 3: Emergency fund
    await page.fill('input[name="emergency_months"]', '6');
    await page.click('button:has-text("Next")');

    // Step 4: Confirm
    await page.click('button:has-text("Confirm")');

    await expect(page.locator('.rule-card')).toHaveCount(3);
  });

  test('rule status colors are correct', async ({ page }) => {
    await page.goto('/#financial');
    // Assuming a violated rule exists
    const violatedRule = page.locator('.rule-card.status-violated');
    await expect(violatedRule.locator('.status-indicator')).toHaveCSS('background-color', 'rgb(239, 68, 68)');
  });

  test('privacy toggle hides amounts', async ({ page }) => {
    await page.goto('/#financial');
    await page.click('button:has-text("Hide Amounts")');
    await expect(page.locator('.dollar-amount')).toHaveCount(0);
    await expect(page.locator('.percentage-value')).toHaveCount.greaterThan(0);
  });

  test('alert snooze works', async ({ page }) => {
    await page.goto('/#financial');
    const alert = page.locator('.rule-alert').first();
    await alert.locator('button:has-text("Snooze")').click();
    await page.click('button:has-text("1 Week")');
    await expect(alert).not.toBeVisible();
  });
});
```

---

## Sign-off Checklist: Sprint 4

- [ ] **PM Sign-off**: Constitution UX is intuitive
- [ ] **Architect Sign-off**: Rules engine is extensible
- [ ] **Dev Sign-off**: All unit tests passing (target: 45+ tests)
- [ ] **QA Sign-off**: All scenarios pass

---

# SPRINT 5: Reports & Insights (Weeks 9-10)

## PM Requirements

### Feature: F5.1 - Weekly Summary Redesign
**User Story:** As a user, I want a weekly summary that highlights what changed.

**Acceptance Criteria:**
- [ ] Constitution compliance score at top
- [ ] "What Changed" section with bullet points
- [ ] One "Thing to Consider" recommendation
- [ ] Links to full details

### Feature: F5.2 - Trend Visualizations
**User Story:** As a user, I want to see trends over time.

**Acceptance Criteria:**
- [ ] Confidence trend chart (line graph)
- [ ] Allocation drift chart (bar comparison)
- [ ] Goal progress rings
- [ ] Time range selector (1m, 3m, 6m, 1y)

### Feature: F5.3 - SCAR Insights
**User Story:** As a user, I want insights that explain Situation, Cause, Action, Result.

**Acceptance Criteria:**
- [ ] Each insight has SCAR structure
- [ ] Maximum 3 active insights
- [ ] Action buttons per insight
- [ ] Can dismiss with feedback

---

## TDD Test Specifications

### Unit Tests: Trend Calculations

**File:** `tests/unit/intelligence/test_trend_calculations.py`

```python
class TestTrendCalculations:

    def test_confidence_trend_calculation(self):
        """Confidence trend shows weekly averages."""
        snapshots = [
            ConfidenceSnapshot(date='2026-01-01', avg=0.72),
            ConfidenceSnapshot(date='2026-01-08', avg=0.75),
            ConfidenceSnapshot(date='2026-01-15', avg=0.78),
        ]

        trend = calculate_confidence_trend(snapshots)

        assert trend.direction == 'improving'
        assert trend.delta == pytest.approx(0.06)

    def test_allocation_drift_calculation(self):
        """Drift is current - target."""
        targets = {'stocks': 60, 'bonds': 30, 'cash': 10}
        current = {'stocks': 65, 'bonds': 25, 'cash': 10}

        drift = calculate_allocation_drift(targets, current)

        assert drift['stocks'] == 5
        assert drift['bonds'] == -5
        assert drift['cash'] == 0
```

### E2E Tests: Reports View

**File:** `desktop-app/tests/e2e/reports-view.spec.js`

```javascript
test.describe('Reports & Insights', () => {
  test('weekly summary shows constitution score', async ({ page }) => {
    await page.goto('/#reports');
    await expect(page.locator('.constitution-score')).toBeVisible();
  });

  test('trend chart renders', async ({ page }) => {
    await page.goto('/#reports');
    await expect(page.locator('.trend-chart canvas')).toBeVisible();
  });

  test('insight card has SCAR structure', async ({ page }) => {
    await page.goto('/#insights');
    const insight = page.locator('.insight-card').first();
    await expect(insight.locator('.situation')).toBeVisible();
    await expect(insight.locator('.cause')).toBeVisible();
    await expect(insight.locator('.action')).toBeVisible();
    await expect(insight.locator('.result')).toBeVisible();
  });

  test('dismiss insight with feedback', async ({ page }) => {
    await page.goto('/#insights');
    const insight = page.locator('.insight-card').first();
    await insight.locator('button:has-text("Dismiss")').click();
    await page.click('button:has-text("Not Helpful")');
    await expect(insight).not.toBeVisible();
  });
});
```

---

## Sign-off Checklist: Sprint 5

- [ ] **PM Sign-off**: Reports are valuable
- [ ] **Architect Sign-off**: Trend calculations are accurate
- [ ] **Dev Sign-off**: All unit tests passing (target: 55+ tests)
- [ ] **QA Sign-off**: All scenarios pass

---

# SPRINT 6: Polish & Integration (Weeks 11-12)

## PM Requirements

### Feature: F6.1 - Animations & Microinteractions
- Smooth card expand/collapse (300ms)
- Skeleton loading everywhere
- Success toasts with icon animations
- Button press states

### Feature: F6.2 - Accessibility
- Keyboard navigation complete
- Screen reader support
- Color contrast WCAG AA
- Reduced motion option

### Feature: F6.3 - Performance
- Views load in <500ms
- Search filters in <200ms
- Smooth scrolling
- Lazy loading for large lists

### Feature: F6.4 - Edge Cases
- Empty states with helpful messages
- Error states with retry options
- Offline indicator
- Session recovery

---

## Final Test Coverage Targets

| Category | Target | Tests |
|----------|--------|-------|
| Unit Tests | >80% coverage | 60+ |
| Integration Tests | Critical paths | 20+ |
| E2E Tests | User flows | 30+ |
| **Total** | | **110+** |

---

## Final Sign-off Checklist

### PM Sign-off
- [ ] All user stories implemented
- [ ] UX matches wireframes
- [ ] Product feels "premium"

### Architect Sign-off
- [ ] Code is maintainable
- [ ] Performance meets targets
- [ ] Security review passed

### Dev Sign-off
- [ ] All tests passing
- [ ] Code coverage >80%
- [ ] No critical bugs

### QA Sign-off
- [ ] All 121 test scenarios pass
- [ ] Accessibility audit passed
- [ ] Cross-browser tested

---

## Appendix: Test Commands

```bash
# Run all backend tests
PYTHONPATH=. pytest tests/ -v --cov=src --cov-report=html

# Run specific sprint tests
PYTHONPATH=. pytest tests/unit/intelligence/test_cluster_discovery.py -v
PYTHONPATH=. pytest tests/unit/views/ -v

# Run frontend tests
cd desktop-app && npm test

# Run E2E tests
cd desktop-app && npx playwright test

# Run E2E with UI
cd desktop-app && npx playwright test --ui

# Generate coverage report
PYTHONPATH=. pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

*This implementation plan follows the ACMS Agent-Based TDD Workflow with rigorous test-first development.*
