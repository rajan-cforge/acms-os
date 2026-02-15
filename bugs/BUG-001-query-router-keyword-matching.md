# BUG-001: Query Router uses keyword matching instead of semantic understanding

## Summary
The Query Router in `src/intelligence/query_router.py` uses naive keyword pattern matching to detect data sources, causing incorrect routing and poor user experience.

## Severity
HIGH

## Status
FIXED (2026-02-02)

## Environment
- ACMS Version: Current (commit 1213363)
- Component: `src/intelligence/query_router.py`

## Steps to Reproduce

1. Send query: "from my emails, find subscriptions"
2. Expected: Routes to email source, searches for subscription-related emails
3. Actual: Searches for keyword "my" instead of understanding the intent

Another example:
1. Send query: "from memories summarize topics"
2. Expected: Routes to knowledge base, summarizes extracted topics
3. Actual: Searches emails for keyword "memories"

## Expected Behavior
The query router should:
- Understand user INTENT semantically (not just keywords)
- Route to appropriate data sources based on meaning
- Handle ambiguous queries with context
- Return relevant results that match what the user is asking for

## Actual Behavior
The query router:
- Uses `SOURCE_HINTS` dictionary with keyword lists
- Matches single words like "from", "my", "email" literally
- Ignores semantic context and user intent
- Returns irrelevant results

## Root Cause

In `src/intelligence/query_router.py` lines 114-119:

```python
SOURCE_HINTS = {
    "email": ["email", "emails", "inbox", "mail", "message", "sent", "received", "from", "to"],
    "financial": ["spending", "budget", "cost", "expense", "transaction", "payment", "invoice", "money", "dollar", "$"],
    "calendar": ["meeting", "calendar", "schedule", "appointment", "event", "agenda"],
    "chat": ["discussed", "talked", "conversation", "chat", "asked", "answered", "said"],
}
```

This approach:
1. Relies on keyword presence, not semantic meaning
2. Has overlapping keywords (e.g., "from" matches email but is common in all queries)
3. Cannot understand complex queries like "summarize my topics"
4. Fails to leverage the LLM for intent understanding

## Proposed Fix
Replace keyword matching with LLM-based semantic understanding:

1. Use Claude/GPT to analyze query intent
2. Return structured response: intent type, data sources, confidence score
3. Fall back to Ollama for privacy-sensitive queries
4. Cache intent analysis for similar queries

## Dependencies
- Requires LLM API access (Claude/GPT/Ollama)
- May need prompt engineering for intent detection
- Should integrate with existing caching system

## Fix

### Phase 1 Fix (2026-02-02)

**Files Modified:**
1. `src/gateway/intent_classifier.py`
   - Removed "from" as generic EMAIL keyword
   - Added specific pattern for "from my emails"
   - Added "memories", "topics", "knowledge" to MEMORY_QUERY

2. `src/gateway/email_handler.py`
   - Added `_extract_search_terms()` for semantic term extraction
   - Added `_search_subscriptions()` for subscription queries
   - Added `_semantic_email_search()` for general content search
   - Fixed "from" parsing to distinguish "from my emails" vs "emails from John"

**Root Cause Addressed:**
- `"from"` was too generic a keyword for EMAIL intent
- Email handler used `r'from\s+(\w+)'` which extracted "my" as sender name

**Result:**
- "from my emails, find subscriptions" → Now finds subscription emails
- "from memories summarize topics" → Now routes to MEMORY_QUERY

## Verification
- [x] Manual API test: subscription query returns subscription emails
- [x] Manual API test: memories query routes to MEMORY_QUERY intent
- [x] No regression in email sender search ("emails from John" still works)
- [ ] Full regression test suite (pending)
