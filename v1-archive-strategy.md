# ACMS v1.0 Archive Strategy - Phase 0-1 Transition to v2.0

**Purpose**: Document what to keep, archive, and update from ACMS v1.0 (enterprise-first) to v2.0 (desktop-first)  
**Date**: October 13, 2025  
**Status**: Transition Plan  

---

## 📊 **WHAT CHANGED**

### **v1.0 (Original Direction)**
- **Focus**: Enterprise SaaS, design partners, cloud deployment
- **Target**: Regulated industries (healthcare, finance, legal)
- **GTM**: B2B sales, long sales cycles
- **First Customer**: SOC.ai (internal alpha), then 10-20 design partners

### **v2.0 (New Direction)**
- **Focus**: Desktop app, self-testing, multi-tool context bridge
- **Target**: YOU (first user), then individual developers
- **GTM**: Self-published, Product Hunt, prosumer → enterprise
- **First Customer**: YOU testing on YOUR desktop with YOUR tools

---

## ✅ **WHAT TO KEEP FROM PHASE 0-1**

### **Phase 0: ACMS-Lite** ✅ KEEP EVERYTHING
- **File**: `acms_lite.py` (230 lines)
- **Database**: `.acms_lite.db` (48 memories)
- **Why Keep**: This is our meta-memory system. It tracked the entire v1.0 build and will continue tracking v2.0.
- **Action**: NO CHANGES NEEDED

**Rationale**: ACMS-Lite is our "build journal". Even though we're changing direction, we want to remember:
- Why we made certain decisions
- What we learned in Phase 0-1
- Technical specs (ports, databases, CRS formula)
- Checkpoint validation framework

### **Phase 1: Infrastructure** ✅ KEEP EVERYTHING
- **File**: `docker-compose.yml`
- **Services**: PostgreSQL (40432), Redis (40379), Ollama (40434), Weaviate (8080)
- **Why Keep**: v2.0 uses THE SAME infrastructure. Desktop app will connect to these services.
- **Action**: NO CHANGES NEEDED

**Rationale**: The storage layer (PostgreSQL, Weaviate), caching (Redis), and embeddings (Ollama) are identical between v1.0 and v2.0. The only difference is the application layer on top.

---

## 📁 **WHAT TO ARCHIVE**

### **Archive Location:**
```bash
mkdir -p archive/v1.0-enterprise-first

# Move these files:
docs/phase0_summary.md → archive/v1.0/
docs/phase1_summary.md → archive/v1.0/
docs/old_master_plan_v1.0.md → archive/v1.0/
docs/old_prd_v1.0.md → archive/v1.0/
docs/design_partner_strategy.md → archive/v1.0/
```

### **Files to Archive:**

1. **phase0_summary.md**
   - **Why Archive**: Context references "design partners", "enterprise", "SOC.ai"
   - **What Changed**: v2.0 focuses on YOU testing, not enterprise
   - **Keep Reference**: Yes, for historical context

2. **phase1_summary.md**
   - **Why Archive**: Mentions "design partners", "enterprise deployment"
   - **What Changed**: v2.0 is desktop-first, local-only (no enterprise deployment yet)
   - **Keep Reference**: Yes, infrastructure details still relevant

3. **Old Master Plan (from conversation history)**
   - **Why Archive**: Phases 4-6 were enterprise-focused
   - **What Changed**: New master plan is desktop-focused
   - **Keep Reference**: Yes, some technical details reusable

4. **Old PRD (from conversation history)**
   - **Why Archive**: Target users were enterprises, not individual developers
   - **What Changed**: New PRD focuses on desktop use case
   - **Keep Reference**: Yes, some requirements still valid

5. **Design Partner Strategy**
   - **Why Archive**: Focused on recruiting healthcare/finance enterprises
   - **What Changed**: v2.0 starts with YOU testing, enterprises come later
   - **Keep Reference**: Maybe useful post-launch (Phase 7+)

### **Archive README:**
Create `archive/v1.0/README.md`:

```markdown
# ACMS v1.0 Archive - Enterprise-First Direction

This archive contains the original ACMS v1.0 plan, which focused on enterprise SaaS and design partner recruitment.

## Why We Changed Direction

**Original Plan (v1.0)**:
- Build for enterprises first
- Recruit 10-20 design partners (healthcare, finance, legal)
- Cloud deployment, multi-tenant SaaS
- Long sales cycles (6-12 months)

**Problem**: 
- Too abstract (no immediate validation)
- Dependency on external customers
- Slow feedback loop (months)

**New Plan (v2.0)**:
- Build for desktop first
- YOU are the first user (immediate testing)
- Local deployment, single-user
- Fast feedback loop (days)

**When to Revisit**: After v2.0 MVP is proven (Phase 6 complete, you're using it daily), we can revisit v1.0 ideas for enterprise expansion (Phase 7+).

## Files in This Archive

- `phase0_summary.md` - Phase 0 summary (bootstrap)
- `phase1_summary.md` - Phase 1 summary (infrastructure)
- `old_master_plan_v1.0.md` - Original 7-phase plan
- `old_prd_v1.0.md` - Product requirements (enterprise focus)
- `design_partner_strategy.md` - How to recruit enterprises

## What We Kept

- **ACMS-Lite**: Still using for meta-memory (no changes)
- **Infrastructure**: Docker services unchanged (PostgreSQL, Redis, Weaviate, Ollama)
- **Technical Specs**: CRS formula, encryption, embedding model all the same
- **Checkpoint Framework**: Still using checkpoint validation

## What Changed

- **Phases 2-6**: Complete rewrite for desktop app
- **Target User**: Individual developers (YOU) instead of enterprises
- **GTM**: Self-published → prosumer → enterprise (instead of enterprise-first)
- **Architecture**: Desktop app (Electron) instead of cloud API

## Future

If ACMS v2.0 succeeds (you use it daily, friends love it, Product Hunt launch goes well), we'll revisit this archive for enterprise expansion ideas.
```

---

## 🔄 **WHAT TO UPDATE**

### **Update ACMS-Lite Memories:**

**Add new context:**
```bash
# Store v2.0 direction
python3 acms_lite.py store "DIRECTION CHANGE: v2.0 is desktop-first. YOU are first user, testing with YOUR AI tools (ChatGPT, Cursor, Claude). Goal: prove it works before enterprise." --tag direction_change --phase planning

# Store what stayed the same
python3 acms_lite.py store "v1.0 → v2.0 UNCHANGED: Phase 0 (ACMS-Lite), Phase 1 (infrastructure), technical specs (CRS, encryption, databases). Only application layer changed." --tag migration --phase planning

# Store what changed
python3 acms_lite.py store "v1.0 → v2.0 CHANGED: Phases 2-6 rewritten for desktop app. No design partners yet. Focus: YOU testing on YOUR desktop." --tag migration --phase planning

# Archive old memories (don't delete, just tag)
python3 acms_lite.py query "design partner" --limit 10
# For each result, add tag "v1.0_archived"
```

### **Update Checkpoint Validation:**

**No changes needed!** Checkpoint framework is version-agnostic:
```python
# tests/checkpoint_validation.py still works:
# - Checkpoint 0: ACMS-Lite (unchanged)
# - Checkpoint 1: Infrastructure (unchanged)
# - Checkpoints 2-6: Will be updated as v2.0 phases complete
```

### **Update File Structure:**

**Create new docs folder structure:**
```bash
docs/
├── archive/
│   └── v1.0-enterprise-first/
│       ├── README.md
│       ├── phase0_summary.md
│       ├── phase1_summary.md
│       └── old_master_plan_v1.0.md
├── v2.0/
│   ├── master_plan_v2.0.md          # NEW
│   ├── prd_desktop_v2.0.md          # NEW
│   ├── demo_script.md               # NEW
│   ├── integration_instructions.md  # NEW
│   └── phase<N>_summary.md          # Will be created as phases complete
└── README.md                        # Update to point to v2.0
```

---

## 📝 **MIGRATION CHECKLIST**

### **Before Starting Phase 2:**

- [ ] Archive v1.0 documents (phase0/1 summaries, old PRD)
- [ ] Create archive/v1.0/README.md explaining the change
- [ ] Update main README.md to point to v2.0 plan
- [ ] Store v2.0 direction in ACMS-Lite
- [ ] Tag old memories as "v1.0_archived" (don't delete)
- [ ] Verify Phase 0-1 infrastructure still working
- [ ] Verify checkpoint validation still works

### **During Phase 2-6:**

- [ ] Reference v2.0 master plan (not v1.0)
- [ ] Reference v2.0 PRD (not v1.0)
- [ ] Query ACMS-Lite for technical specs (CRS, encryption) - these didn't change
- [ ] Store new decisions with tag "v2.0"
- [ ] Generate phase summaries under docs/v2.0/

### **After Phase 6 (MVP Complete):**

- [ ] Evaluate: Did v2.0 approach work? (Are you using it daily?)
- [ ] If YES: Continue to Phase 7 (beta testing with friends)
- [ ] If NO: Debug, iterate, maybe revisit v1.0 enterprise ideas
- [ ] Decision point: When to reintroduce enterprise features from v1.0 archive

---

## 🎯 **WHAT THIS MEANS FOR CLAUDE CODE**

### **Instructions for Claude Code:**

**When building Phase 2-6:**
```bash
# CORRECT: Query v2.0 plan
python3 acms_lite.py query "desktop app architecture" --tag v2.0

# CORRECT: Reference new PRD
cat docs/v2.0/prd_desktop_v2.0.md

# CORRECT: Follow new master plan
cat docs/v2.0/master_plan_v2.0.md

# WRONG: Don't reference archived v1.0 docs
# Don't do: cat docs/phase0_summary.md (archived)
# Do instead: cat archive/v1.0/phase0_summary.md (for reference only)
```

**When technical specs needed:**
```bash
# CRS formula, encryption, ports - these didn't change
python3 acms_lite.py query "CRS formula components"
python3 acms_lite.py query "port configuration 40000"
python3 acms_lite.py query "encryption XChaCha20"
# These memories are still valid (not archived)
```

**When in doubt:**
```bash
# Check memory tags
python3 acms_lite.py list --tag v2.0 --limit 10    # v2.0 decisions
python3 acms_lite.py list --tag v1.0_archived --limit 10  # Old decisions (reference only)
python3 acms_lite.py list --tag tech_spec --limit 10      # Technical specs (unchanged)
```

---

## 🔮 **FUTURE: WHEN TO REVISIT v1.0**

### **Trigger: v2.0 MVP Success**

**Success Criteria:**
- ✅ You use ACMS Desktop daily for 1 week
- ✅ Demo impresses 5+ friends/colleagues
- ✅ Product Hunt launch (Top 5 of the day)
- ✅ 100+ users in first month
- ✅ 30%+ conversion to paid ($20/mo)

**Then:**
- Revisit `archive/v1.0/design_partner_strategy.md`
- Adapt for post-launch enterprise outreach
- Add team features (shared workspaces)
- Add enterprise features (SSO, audit logs)
- Start recruiting enterprise design partners

### **Trigger: v2.0 MVP Fails**

**Failure Indicators:**
- ❌ You stop using it after 1 week (not valuable)
- ❌ Demo confuses people (UX problems)
- ❌ Product Hunt launch flops (< 100 upvotes)
- ❌ < 10 users in first month
- ❌ Zero conversion to paid

**Then:**
- Debug: Why didn't v2.0 work?
- Revisit v1.0: Was enterprise-first the right approach after all?
- Pivot: Maybe a hybrid (desktop for developers, cloud for enterprises)
- Learn: Incorporate lessons into v3.0

---

## ✅ **SIGN-OFF**

### **Approval Checklist:**

- [ ] I understand v1.0 is archived (not deleted)
- [ ] I understand v2.0 focuses on desktop testing
- [ ] I understand Phase 0-1 infrastructure unchanged
- [ ] I understand ACMS-Lite continues to track everything
- [ ] I'm ready to start Phase 2 with v2.0 plan

### **Sign-Off:**

**Date**: October 13, 2025  
**Decision**: Proceed with ACMS v2.0 (Desktop-First) direction  
**Rationale**: Faster validation, YOU as first user, immediate feedback loop  
**Next Step**: Start Phase 2 (Storage Layer + Desktop App Foundation)  

---

**Ready to build v2.0!** 🚀

The archive is there if we need it, but let's focus on making v2.0 work first. Enterprise features can come later (Phase 7+) once we prove the core value proposition on desktop.

**PROCEED TO PHASE 2 →**
