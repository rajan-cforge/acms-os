# ACMS Financial Constitution & Portfolio Governance Integration
## Full Design Specification (WHAT / WHY / HOW)

**Audience:** Claude Code  
**Scope:** Full production design (not MVP)  
**ACMS Status Assumed:** Phase 0, Phase 1, Phase 1.5 complete  

---

## 1. WHAT — What We Are Building

We are integrating a **Financial Constitution & Portfolio Governance Engine** into the **ACMS Unified Intelligence Layer**.

This system enables ACMS to:

1. Define an **Investment Constitution**
   - Articles → Rules → Signals → Exceptions
   - Versioned, auditable, immutable by default
   - Explicit amendment and override workflows

2. Ingest **Financial Reality**
   - Plaid (transactions, balances, investments)
   - Fidelity (via Plaid + CSV fallback)
   - Local-only, encrypted at rest

3. Perform **Deterministic Portfolio Evaluation**
   - Concentration risk
   - Drawdowns and volatility
   - Turnover discipline
   - Tax-awareness signals
   - AI-infrastructure thesis exposure
   - Behavioral drift (FOMO, panic selling)

4. Produce **Unified Intelligence Insights**
   - Portfolio compliance
   - Rule violations
   - Drift detection
   - Exception expiry
   - Behavioral risk alerts

5. Answer cross-source questions such as:
   - “Are my investments aligned with my philosophy?”
   - “Where am I drifting?”
   - “Which rules am I violating and why?”

6. Feed **ACMS Pulse**
   - Daily / weekly governance summary
   - Actionable, privacy-safe, audit-backed

This is **not** a robo-advisor or stock picker.  
It is a **decision-governance system**.

---

## 2. WHY — Why This Belongs Inside ACMS

### 2.1 Strategic Rationale

ACMS is becoming a **Unified Intelligence Operating System**, not a chat tool.

Finance without governance:
- Optimizes outcomes, not decision quality
- Ignores behavioral drift
- Cannot enforce stated beliefs

This system introduces:
- Intellectual honesty
- Long-term consistency
- Explicit accountability

### 2.2 Why a Constitution (Not Just RAG)

Investment philosophy is **normative**, not semantic.

RAG-only systems:
- Rationalize after the fact
- Drift with user behavior
- Cannot enforce constraints

A Constitution:
- Can be violated
- Can require justification
- Can expire exceptions
- Is auditable and enforceable

### 2.3 Why Deterministic First, LLM Second

LLMs are used only for:
- Explanation
- Summarization
- Narrative synthesis

LLMs are never used for:
- Pass/fail decisions
- Metric computation
- Rule overrides
- Accessing raw financial values

---

## 3. HOW — How This Is Implemented

### 3.1 Architectural Placement

Integrated at **Phase 1.5: Unified Intelligence Layer**.

```
Financial Data (Plaid / Fidelity)
        ↓
Canonical Finance Tables (Postgres, encrypted)
        ↓
Derived Portfolio Snapshots
        ↓
Constitution Rule Engine
        ↓
Compliance & Drift Results
        ↓
Unified Insights (Postgres + Weaviate)
        ↓
Query Router + Pulse + Chat
```

---

## 3.2 Core Components

```
src/intelligence/finance/
├── constitution/
│   ├── constitution_loader.py
│   ├── rule_dsl.py
│   ├── compute_registry.py
│   ├── evaluator.py
│   ├── exception_manager.py
│   ├── scoring.py
│   └── redaction.py
├── finance_insight_extractor.py
└── governance_pulse_generator.py
```

---

## 3.3 Data Model

### 3.3.1 Constitution Tables (PostgreSQL)

- investment_constitutions
- investment_articles
- investment_rules
- investment_exceptions

All changes are versioned and audited.

### 3.3.2 Financial Fact Tables

- financial_accounts
- financial_transactions
- positions_daily
- portfolio_snapshots_daily

Snapshots store **percentages, buckets, and flags only**.

### 3.3.3 Evaluation Tables

- constitution_evaluations
- constitution_rule_results

Each evaluation is immutable and reproducible.

---

## 3.4 Constitution Structure

### Articles
High-level principles (e.g., Capital Preservation, AI Infra Thesis).

### Rules
Executable constraints with:
- Severity (INFO / WARN / FAIL)
- Weight
- Scope (portfolio / account / security)

### Signals
Deterministic computations:
- max_position_pct
- ai_infra_exposure_pct
- drawdown_12m_pct
- turnover_90d_pct
- short_term_gain_risk
- behavioral flags

### Exceptions
Time-boxed overrides with:
- Justification
- Evidence
- Expiry
- Full audit trail

---

## 3.5 Rule Engine

Rules are data, not code.

Example rule definition:
```json
{
  "rule_id": "R1",
  "severity": "FAIL",
  "weight": 0.9,
  "signals": [
    {
      "compute": "max_position_pct",
      "pass_if": "<= 0.15"
    }
  ]
}
```

Only approved compute functions may be used.

---

## 3.6 Exception Handling

- Explicit approval required
- Time-boxed
- Visible in all reports
- Automatic alerts on expiry

---

## 3.7 Unified Insight Emission

Insight types:
- portfolio_compliance
- rule_violation
- portfolio_drift
- exception_expiry
- behavioral_risk

Example:
```json
{
  "insight_type": "rule_violation",
  "severity": "WARN",
  "summary": "AI infrastructure exposure exceeds preferred band",
  "evidence": {
    "current_pct": 0.52,
    "target_max_pct": 0.45
  }
}
```

---

## 3.8 Query Router Integration

Queries containing:
- “aligned”, “constitution”, “rules”, “philosophy”

Route to:
- finance_constitution insights
- evaluation records

All responses include citations to rules and evaluations.

---

## 3.9 ACMS Pulse Integration

New Pulse section:

```
💼 INVESTMENT GOVERNANCE
• Alignment score: 78/100 (↓ 4)
• Violations: 2 WARN
• Exceptions expiring: 1 (14 days)
• Suggested action: Review AI-infra exposure
```

---

## 3.10 Privacy & Audit

### Privacy Rules
- No raw amounts to LLMs
- No account numbers to LLMs
- Only derived metrics exposed

### Audit Coverage
- Ingress: Plaid, CSV
- Transform: evaluations
- Egress: LLM explanations only

---

## 3.11 APIs

### Constitution
- POST /api/finance/constitution
- POST /api/finance/constitution/{id}/activate
- POST /api/finance/constitution/{id}/amend

### Evaluation
- POST /api/finance/constitution/evaluate
- GET /api/finance/constitution/evaluations/latest

### Exceptions
- POST /api/finance/constitution/exceptions
- POST /api/finance/constitution/exceptions/{id}/decision

---

## 3.12 Scoring Model

PASS = 1.0  
WARN = 0.5  
FAIL = 0.0  

Portfolio score:
```
Σ(weight × score) / Σ(weight) × 100
```

Tracked over time for drift.

---

## 3.13 Testing Requirements

### Unit
- Rule DSL
- Compute functions
- Exception logic
- Redaction

### Integration
- Plaid → evaluation → insights
- CSV → evaluation
- Privacy enforcement

### E2E
- Governance UI
- Exception workflow
- Pulse integration

---

## 4. Final Positioning

This system makes ACMS a **governed decision-making OS**, not a reactive assistant.

It is:
- Deterministic
- Auditable
- Privacy-first
- Philosophically grounded

---
Yes. Below is the 25-rule set (organized by Articles) plus the exact signals each rule requires, so you can validate the Phase 2A canonical model and derived tables before finalizing.

A1 — Capital Preservation & Survivability

R1 Max single-name concentration (FAIL)
    •    Rule: max(position_value_pct) <= MAX_SINGLE_NAME_PCT (default 15%)
    •    Signals: positions_daily, portfolio_value → max_position_pct, top_security_ref

R2 Max sector concentration (WARN/FAIL)
    •    Rule: warn >45%, fail >55% in a sector
    •    Signals: positions_daily + securities_master.sector → sector_exposure_pct_by_sector, sector_max_pct

R3 Max speculative sleeve (FAIL)
    •    Rule: speculative_exposure_pct <= 5%
    •    Signals: security_tags (SPECULATIVE) + positions_daily → tag_exposure_pct(SPECULATIVE)

R4 Minimum liquidity buffer (WARN)
    •    Rule: cash_pct >= threshold or cash_months >= 3 (configurable)
    •    Signals: cash_positions, portfolio_value; optional monthly_required_spend (user config) → cash_pct, cash_months

R5 Drawdown guardrail (FAIL)
    •    Rule: trailing 12m drawdown >= -20% else require review/lock risk adds
    •    Signals: portfolio_value_time_series → drawdown_12m_pct, peak_date

A2 — Long-Term Compounding

R6 Turnover limit (WARN)
    •    Rule: turnover_90d_pct <= 20%
    •    Signals: transactions + positions → turnover_pct(window=90)

R7 Holding-period intent match (WARN)
    •    Rule: positions held <30d must be <= 5% unless tagged TACTICAL
    •    Signals: positions_lots (or infer from transactions) → pct_value_positions_held_lt(30d), tag_exposure_pct(TACTICAL)

R8 Core index base (WARN)
    •    Rule: diversified core ETFs/funds >= 25% unless “concentrated mode” declared
    •    Signals: security_tags(INDEX_CORE) + positions_daily → tag_exposure_pct(INDEX_CORE), portfolio_mode

R9 Rebalancing discipline (WARN)
    •    Rule: drift beyond band (e.g., ±5%) triggers rebalance insight
    •    Signals: target allocation config + allocation_pct_by_bucket → band_breaches[]

A3 — Quality + Value Discipline

R10 Thesis required for every single-name (FAIL)
    •    Rule: any non-index single-name must have a thesis artifact
    •    Signals: theses table + positions_daily + tag INDEX_CORE → missing_thesis_security_refs[]

R11 Quality screen for compounder tag (WARN)
    •    Rule: if tagged QUALITY_COMPOUNDER, require quality evidence (FCF+, stability, etc.)
    •    Signals: fundamentals_daily (optional module) or user-provided metrics → quality_pass_flag, data_coverage_confidence

R12 Valuation stretch rule (WARN/FAIL)
    •    Rule: if above multiple threshold, require explicit justification + disconfirm signals
    •    Signals: fundamentals_daily (PE, EV/FCF, FCF yield) + thesis → valuation_stretch_flag, has_valuation_justification

R13 No averaging down without updated thesis (FAIL)
    •    Rule: after -15% move or add-on buys during drawdown require thesis review <14d
    •    Signals: transactions + security_price_series + thesis_reviews → avg_down_event_detected, thesis_review_recency_days

A4 — AI Infrastructure Thesis

R14 AI-infra basket definition (INFO/WARN)
    •    Rule: AI_INFRA_CORE must map to subthemes (compute/network/hyperscaler/etc.)
    •    Signals: security_tags(AI_INFRA_CORE) + theme_mapping → ai_basket_breakdown

R15 AI-infra concentration cap (WARN/FAIL)
    •    Rule: warn >40%, fail >55% unless “high-conviction mode”
    •    Signals: tag_exposure_pct(AI_INFRA_CORE) + portfolio_mode → ai_infra_exposure_pct

R16 Single-point-of-failure check (WARN)
    •    Rule: one name >50% of AI basket triggers warning
    •    Signals: AI basket positions → ai_basket_single_name_max_pct, ai_basket_top_security_ref

R17 Thesis decay monitor (WARN)
    •    Rule: quarterly thesis review required for AI_INFRA_CORE
    •    Signals: thesis_reviews + tags → review_overdue_flag, days_since_last_review

A5 — Tax-Aware Wealth Building

R18 Short-term gains minimization (WARN)
    •    Rule: if ST gains risk is high vs declared long-term intent, warn
    •    Signals: transactions + holding periods (lots) → st_gain_risk_flag, intent_profile

R19 Wash sale risk alert (FAIL)
    •    Rule: loss sale + repurchase (same/substantially identical) within 30d
    •    Signals: transactions + security equivalence map (ticker→equivalent) → wash_sale_events[]

R20 Tax-loss harvesting opportunity (INFO/WARN)
    •    Rule: if meaningful unrealized losses exist and no TLH actions in window, suggest
    •    Signals: positions_daily + cost basis (if available) → unrealized_loss_flags[] (no dollars in insights; can store encrypted dollars locally)

R21 RSU/ESPP concentration awareness (WARN)
    •    Rule: employer exposure above threshold (direct + correlated)
    •    Signals: tag EMPLOYER / issuer mapping + positions → employer_exposure_pct, optional correlation_group_exposure_pct

R22 After-tax reporting (INFO)
    •    Rule: monthly report includes after-tax estimates / risk flags
    •    Signals: tax_profile_config + realized_gain_flags → after_tax_report_ready_flag

A6 — Behavioral & Process Integrity

R23 FOMO pattern detector (WARN)
    •    Rule: new position initiated after +X% run-up within Y days without thesis
    •    Signals: transactions + price_series + theses → fomo_entry_events[]

R24 Panic-sell detector (WARN)
    •    Rule: selling after rapid drawdown without thesis update
    •    Signals: transactions + price_series + thesis_reviews → panic_sell_events[]

R25 Narrative-chasing cap (WARN/FAIL)
    •    Rule: new positions per month <= 3 unless research-phase mode
    •    Signals: transactions → new_positions_count_30d, portfolio_mode

⸻

What this implies for Phase 2A data model (signals checklist)

To support these 25 rules cleanly, Phase 2A must reliably produce:
    1.    positions_daily (security_id, quantity, market_value, tags/sector/theme refs)
    2.    transactions normalized (BUY/SELL/DIV/INTEREST/FEE/TRANSFER), with timestamps
    3.    portfolio_value_time_series (or portfolio_snapshots_daily with value buckets + drawdown metrics)
    4.    securities_master with tags, sector, and theme mappings (AI basket)
    5.    theses + thesis_reviews tables (process integrity rules)
    6.    Optional but strongly recommended:
    •    lots / holding periods (inferred if tax lots unavailable)
    •    price series (daily close) for drawdown/FOMO/panic detection
    •    fundamentals_daily (only needed for R11/R12; can be added later with “data coverage” gating)

Answer to the design question (ledger vs insights)

You should keep both (and you already have the right shape):
    •    constitution_evaluations / constitution_rule_results = authoritative evaluation ledger (exact lookup, trend charts, audits, governance reporting)
    •    unified_insights / ACMS_Insights_v1 = searchable “events” layer (semantic retrieval, cross-source questions, Pulse blocks)

This separation is correct and should remain.


) Security Tagging (critical)

Use a 3-layer tagging system so it’s reliable, explainable, and doesn’t block ingestion.

Tag sources (in priority order):
    1.    Manual (authoritative)
    •    UI lets you tag a security (ticker/security_id) with: AI_INFRA_CORE, INDEX_CORE, SPECULATIVE, QUALITY_COMPOUNDER, TACTICAL, EMPLOYER, etc.
    •    This is the ground truth for governance.
    2.    Seeded (default suggestions)
    •    Maintain a local “seed map” table that maps common tickers/ETFs to tags (e.g., VOO/VTI/QQQ → INDEX_CORE).
    •    Also add a “theme mapping” table for AI-infra sub-themes (compute/network/hyperscaler/equipment/etc.).
    3.    Inferred (non-authoritative)
    •    Heuristics (e.g., sector=Semiconductors + known list → candidate AI_INFRA_CORE).
    •    Inference only produces suggested tags with confidence and must be “accepted” to become authoritative.

Data model
    •    security_tags table with:
    •    tag, source = manual|seed|inferred
    •    is_active, confidence, evidence_json
    •    Rule engine uses only:
    •    manual + seed by default
    •    optional include_inferred=true for “draft mode”

This prevents silent misclassification while still scaling.

⸻

2) Theses & Thesis Reviews (R10, R13, R17, R23, R24)

Make this a dedicated thesis artifact with links to evidence, not just free-form notes.

Implementation
    •    A Thesis Editor UI (simple, structured fields + free text):
    •    thesis_text, time_horizon, key_risks, disconfirm_signals, review_cadence_days
    •    A Thesis Review is a separate object:
    •    timestamped check-in + optional updates
    •    can be created manually or triggered by rule violations (e.g., “averaging down requires review”)

Cross-source enrichment (optional, not a dependency)
    •    Allow linking to:
    •    emails, memories, uploaded docs (IDs only)
    •    But do not derive thesis automatically from chats/emails as truth. That becomes a suggestion.

Data model
    •    investment_theses(security_id, status, created_at, updated_at, …)
    •    thesis_reviews(thesis_id, review_at, changes_json, notes, …)
    •    thesis_evidence_links(thesis_id, source_type, source_ref, …)

⸻

3) Price Series Source (R5, R13, R23, R24)

Don’t depend on third-party APIs as a hard requirement. Use a local market data provider abstraction with multiple backends.

Strategy
    •    Maintain market_data_daily(security_id, date, close, adj_close, …) locally.
    •    Populate it via pluggable providers:
    1.    Broker/aggregator-derived snapshots (if you can derive daily marks from positions; often incomplete)
    2.    User import (CSV price history) fallback
    3.    External provider (optional plugin), with strict caching and audit

Scope
    •    Only fetch/store prices for securities you hold + benchmarks (SPY/QQQ/VOO) to compute drawdown/relative moves.

Why
    •    Keeps Phase 2A stable even when APIs break.
    •    Makes your behavioral rules reliable.

⸻

4) Tax Lots / Cost Basis (R18–R20)

Assume cost basis is inconsistent across institutions and aggregators. Design for graceful degradation.

Truth model
    •    Store what you have:
    •    If you receive tax lots/cost basis, store it (encrypted).
    •    If not, infer a “shadow-lot ledger” from transactions.

Inference method
    •    Default to FIFO unless user selects LIFO/Specific ID.
    •    Track estimated_cost_basis_confidence to gate tax rules.

Wash sale detection
    •    Requires:
    •    sells at loss + repurchase within 30 days
    •    “substantially identical” mapping
    •    Implement security_equivalence_map:
    •    manual mapping for ETFs / share classes / close substitutes

Data model
    •    position_lots (optional, encrypted fields): qty, open_date, cost_basis
    •    lot_method_config (FIFO/LIFO/Specific ID)
    •    security_equivalence_map(security_id → equivalence_group_id)

Tax rules become:
    •    FAIL only when confidence is high
    •    otherwise WARN with “insufficient basis coverage”

⸻

5) Target Allocation Config (R9)

Use a bucket-based target allocation with bands.

Config table
    •    allocation_targets:
    •    bucket_id (e.g., AI_INFRA, INDEX_CORE, CASH, SPECULATIVE, BONDS)
    •    target_pct
    •    min_pct, max_pct (or band width)
    •    optional rebalance_frequency_days

Bucket composition
    •    Bucket membership is tag-driven:
    •    AI_INFRA = AI_INFRA_CORE
    •    INDEX_CORE = INDEX_CORE
    •    etc.

This keeps rebalancing deterministic and user-controlled.

⸻

6) Fundamentals (R11, R12) — defer/gate

Agree: treat fundamentals as Phase 2D and gate the rules behind coverage.

Mechanism
    •    fundamentals_coverage(security_id, coverage_score 0..1, last_updated_at)
    •    R11/R12 only evaluate if coverage_score >= threshold (e.g., 0.8)
    •    Otherwise:
    •    emit INFO/WARN: “Valuation/quality checks skipped due to missing fundamentals.”

⸻

Design decision summary (so Phase 2A schema is unblocked)

You can finalize Phase 2A with these guaranteed primitives:
    1.    Securities master + tags (manual/seed/inferred)
    2.    Transactions normalized
    3.    Positions_daily
    4.    Portfolio_snapshots_daily (derived metrics: exposure %, drawdown %, turnover %)
    5.    Thesis + thesis_reviews
    6.    Optional but schema-ready:
    •    market_data_daily
    •    position_lots + equivalence_map
    •    allocation_targets

If you want the next step: I can draft the exact Phase 2A PostgreSQL schema (migrations) that supports all 25 rules with the gating/coverage semantics above, including indexes and audit hooks.
