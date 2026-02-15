# ACMS Bug Tracker

All bugs discovered during development must be documented here.

## Bug Tracking Workflow

1. **Discover issue** (user report, QA finding, self-discovery)
2. **Create bug file**: `bugs/BUG-XXX-short-title.md`
3. **Update this README** with new entry in table below
4. **Investigate and fix**
5. **Document solution** in bug file
6. **QA verifies fix**
7. **Update status to FIXED**

## Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| CRITICAL | System unusable, data loss | Immediate |
| HIGH | Major feature broken | 24 hours |
| MEDIUM | Minor feature issue | 1 week |
| LOW | Cosmetic issue | Backlog |

## Active Bugs

| ID | Title | Severity | Status | Owner | Created |
|----|-------|----------|--------|-------|---------|
| - | - | - | - | - | - |

## Fixed Bugs

| ID | Title | Severity | Fixed Date |
|----|-------|----------|------------|
| BUG-001 | Query Router uses keyword matching instead of semantic understanding | HIGH | 2026-02-02 |

---

## Bug File Template

Use this template when creating new bug files:

```markdown
# BUG-XXX: [Descriptive Title]

## Summary
[One sentence describing the bug]

## Severity
CRITICAL / HIGH / MEDIUM / LOW

## Status
OPEN / IN_PROGRESS / FIXED / WONT_FIX

## Environment
- ACMS Version: [commit hash]
- Component: [affected component]

## Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Expected vs Actual]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Root Cause
[Technical explanation once identified]

## Fix
[Description of the fix once implemented]

## Verification
- [ ] Unit test added
- [ ] Integration test passes
- [ ] Manual verification done
```
