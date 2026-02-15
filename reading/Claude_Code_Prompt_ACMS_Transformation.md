# ACMS Cognitive Transformation — Claude Code Prompt

Paste this directly into Claude Code:

---

I have 4,159 queries and 4,805 topic extractions across 57 topics already in my ACMS PostgreSQL database. I've built cognitive architecture components (schema context, co-retrieval tracker, cross-validator, creative recombination) that pass 163 tests but NONE of them are wired into the live pipeline. The user sees zero difference.

**Your job: Make the transformation visible using my existing data. No new features. No new specs. Just wire what exists and seed it from real data.**

## What exists

- API: port 40080, PostgreSQL: port 40432 (user: acms, db: acms), Weaviate: port 40480
- Desktop Electron app running
- `src/gateway/context_assembler.py` — has `ContextAssembler` with `_determine_expertise_level()`, `_get_calibration_instructions()`, `build_schema_context()`
- `src/retrieval/coretrieval_graph.py` — has `CoRetrievalTracker` with `record_co_retrieval()`, `get_associated_items()`
- `src/intelligence/cross_validator.py` — has `CrossValidator`
- `src/jobs/creative_recombination.py` — has `CreativeRecombinator`
- `src/gateway/orchestrator.py` — the main chat pipeline, this is where schema context needs to be injected

## Step 1: Fix expertise calibration (BUG)

`_determine_expertise_level()` uses absolute thresholds that make everything "expert" when you have 4000+ queries. Fix it to use log-scaled depth combined with relative share (depth / total_queries). Target distribution:

- llm (757), python (703) → expert
- claude (331), go (318), finance (217), security (187), kubernetes (172) → advanced  
- weaviate (149), testing (141), docker (114), business (100), writing (86) → intermediate
- monitoring (70), project-mgmt (69), fastapi (66), http (58), aws (56) → beginner

Test by running the fixed function against real topic_extractions data and printing the profile.

## Step 2: Wire schema context into the live chat pipeline

Find where the LLM system prompt is built in `orchestrator.py` and inject expertise context. The flow:

1. Query comes in
2. Detect topic from query text (keyword matching against known topics from topic_extractions)
3. Look up that topic's depth in topic_extractions table
4. Determine expertise level using fixed function from Step 1
5. Get calibration instructions from `_get_calibration_instructions()`
6. Prepend to system prompt: "USER EXPERTISE: {topic} - {level}. {calibration_instructions}"

After this, test with two real queries:
- Expert topic: "How does Python async error handling work?" → response should assume familiarity
- Beginner topic: "How do I use Terraform?" → response should include fundamentals

Verify by checking logs that "USER EXPERTISE" appears in the system prompt.

## Step 3: Seed co-retrieval graph from existing query history

Write and run a script that:
1. Queries query_history joined with topic_extractions, ordered by created_at
2. Groups queries into 30-minute session windows
3. For each session with 2+ different topics, records topic co-occurrences
4. Feeds these into CoRetrievalTracker.record_co_retrieval()

Print the top 20 strongest associations found.

## Step 4: Seed cross-domain discoveries from existing data

Write and run a script that:
1. Maps topics to domains: ai (llm, claude, gemini), programming (python, go, fastapi), infrastructure (kubernetes, docker, aws, monitoring), security (security), business (finance, business, project-mgmt), data (weaviate), quality (testing, code-review)
2. Finds sessions where queries span multiple domains
3. Counts cross-domain bridges
4. Generates insight text for each bridge (e.g., "ai ↔ security" → "Your AI + Security expertise positions you for AI security specialization")

Store these and print all discoveries found.

## Step 5: Seed topic summaries from existing extractions

Write and run a script that for each topic with 5+ queries:
1. Counts total queries
2. Collects all keywords from topic_extractions
3. Gets the 5 most recent sample questions
4. Determines expertise level
5. Stores as a topic summary record

Print the full summary table.

## Step 6: Add API endpoints

Add these 5 endpoints to the API:
- `GET /api/expertise` — returns full expertise profile (topic, depth, level, relative_share)
- `GET /api/topic/{slug}` — returns topic summary with sample questions and keywords
- `GET /api/associations/{topic}` — returns co-retrieval associations
- `GET /api/discoveries` — returns cross-domain insights
- `GET /api/digest/weekly` — returns this week's activity, evolution, discoveries

Test each endpoint with curl.

## Step 7: Wire into desktop app UI

In the Electron desktop app:
1. Add an expertise badge above each chat response (show topic + level + depth)
2. Add a "Knowledge" tab/view that shows:
   - Expertise bars (topic name, fill bar proportional to relative share, level label)
   - Cross-domain discoveries (bridge label + insight text)
   - Knowledge health (total entries, topic count)
3. The badge fetches from /api/expertise, the dashboard fetches from /api/expertise + /api/discoveries

Use the existing cognitive UI component files if they exist in `desktop-app/src/renderer/components/`.

## Validation

After all steps, show me:
1. The expertise profile printed from real data (should NOT be all "expert")
2. A curl to /api/expertise showing calibrated levels
3. A curl to /api/associations/python showing real co-retrieval patterns
4. A curl to /api/discoveries showing real cross-domain insights
5. A screenshot or description of the desktop app showing the expertise badge on a chat response
6. A test chat where the response style clearly differs between an expert topic and a beginner topic

Do NOT create any new spec documents, README files, or documentation. Just implement, seed, wire, and validate.
