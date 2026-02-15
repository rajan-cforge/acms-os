# ACMS Background Jobs Guide

**Last Updated**: December 14, 2025

This guide explains how background jobs work in ACMS, how to run them, and how to see their results in the UI.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND JOBS ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      API SERVER (acms_api container)                 │   │
│  │                                                                     │   │
│  │  FastAPI App ─────────────────────────────────────────────────────  │   │
│  │       │                                                             │   │
│  │       ├── API Endpoints (sync/async handlers)                       │   │
│  │       │                                                             │   │
│  │       └── APScheduler (Background Jobs) ← NOT INTEGRATED YET       │   │
│  │              │                                                      │   │
│  │              ├── decay_job (daily 3 AM)                            │   │
│  │              ├── dedup_job (weekly Sunday 4 AM)                    │   │
│  │              ├── cleanup_job (weekly Sunday 5 AM)                  │   │
│  │              │                                                      │   │
│  │              ├── topic_extraction_job (hourly) ← TODO              │   │
│  │              ├── insight_generation_job (daily 2 AM) ← TODO        │   │
│  │              └── weekly_report_job (Monday 6 AM) ← TODO            │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Alternative: Standalone Scheduler Process                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  python -m src.jobs.scheduler                                        │   │
│  │  (Runs as separate process, connects to same database)              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Current State

### What EXISTS

| Component | File | Status |
|-----------|------|--------|
| Scheduler setup | `src/jobs/scheduler.py` | ✅ Exists, uses APScheduler |
| Maintenance jobs | `src/jobs/maintenance.py` | ✅ Exists (decay, dedup, cleanup) |
| Weekly report generator | `src/reporting/weekly_report.py` | ✅ Exists (on-demand) |
| Topic extractor | `src/intelligence/topic_extractor.py` | ✅ Exists (on-demand) |
| Insights engine | `src/intelligence/insights_engine.py` | ✅ Exists (on-demand) |

### What's MISSING

| Component | Status | Impact |
|-----------|--------|--------|
| Scheduler NOT integrated into API server | ❌ | Jobs don't run automatically |
| Topic extraction job | ❌ | New Q&A doesn't get topics extracted |
| Insight generation job | ❌ | No automatic pattern detection |
| Weekly report scheduled job | ❌ | Reports only on-demand |
| Job status API endpoint | ❌ | Can't see job status in UI |
| UI for viewing insights/reports | ❌ | No way to see derived intelligence |

---

## How to Run Jobs (Current Methods)

### Method 1: Manual CLI (Ad-hoc)

```bash
# Run all maintenance jobs
PYTHONPATH=/path/to/acms python -m src.jobs.maintenance --job all

# Run specific maintenance job
PYTHONPATH=/path/to/acms python -m src.jobs.maintenance --job decay
PYTHONPATH=/path/to/acms python -m src.jobs.maintenance --job dedup
PYTHONPATH=/path/to/acms python -m src.jobs.maintenance --job cleanup
```

### Method 2: Standalone Scheduler (Background Process)

```bash
# Start scheduler as separate process
cd /path/to/acms
PYTHONPATH=. python -m src.jobs.scheduler

# Output:
# Starting ACMS Job Scheduler...
# [Scheduler] Started with 3 jobs: decay (daily 3AM), dedup (Sun 4AM), cleanup (Sun 5AM)
```

### Method 3: Generate Report On-Demand

```bash
# Generate weekly report
PYTHONPATH=/path/to/acms python -c "
import asyncio
from src.reporting.weekly_report import generate_weekly_report
from src.storage.database import get_db_pool

async def main():
    pool = await get_db_pool()
    report = await generate_weekly_report(pool)
    print(report.executive_summary)

asyncio.run(main())
"
```

### Method 4: Via API Endpoints (On-Demand)

```bash
# Generate insights summary
curl -s "http://localhost:40080/api/v2/insights/summary?period_days=7" | jq

# Generate report
curl -X POST "http://localhost:40080/api/v2/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{"report_type": "weekly", "scope": "user"}' | jq

# List previous reports
curl -s "http://localhost:40080/api/v2/reports" | jq
```

---

## Job Descriptions

### Maintenance Jobs (Existing)

#### 1. Decay Job
- **Schedule**: Daily at 3 AM
- **Purpose**: Reduce importance scores of old, unused memories
- **Logic**: Memories not accessed in 7+ days get 5% decay per day
- **File**: `src/jobs/maintenance.py:decay_job()`

#### 2. Dedup Job
- **Schedule**: Weekly on Sunday at 4 AM
- **Purpose**: Find and merge near-duplicate memories
- **Logic**: Merges memories with same content_hash, keeps highest-scored
- **File**: `src/jobs/maintenance.py:dedup_job()`

#### 3. Cleanup Job
- **Schedule**: Weekly on Sunday at 5 AM
- **Purpose**: Delete old SHORT tier memories
- **Logic**: Removes SHORT tier memories > 30 days old with low scores
- **File**: `src/jobs/maintenance.py:cleanup_job()`

### Intelligence Jobs (TODO)

#### 4. Topic Extraction Job
- **Schedule**: Hourly at :00
- **Purpose**: Extract topics from new Q&A in query_history
- **Logic**: Find rows without topic_extractions, run keyword/LLM extraction
- **Output**: `topic_extractions` table
- **File**: TODO - needs to be created

#### 5. Insight Generation Job
- **Schedule**: Daily at 2 AM
- **Purpose**: Detect patterns and generate insights
- **Logic**: Analyze topic_extractions, detect trends, create user_insights
- **Output**: `user_insights`, `org_knowledge` tables
- **File**: TODO - needs to be created

#### 6. Weekly Report Job
- **Schedule**: Every Monday at 6 AM
- **Purpose**: Generate weekly executive reports
- **Logic**: Aggregate insights, calculate trends, generate recommendations
- **Output**: `intelligence_reports` table
- **File**: `src/reporting/weekly_report.py` (exists, needs scheduling)

---

## How to See Results in UI

### Current: API Only

```bash
# Insights
curl http://localhost:40080/api/v2/insights/summary | jq

# Reports
curl http://localhost:40080/api/v2/reports | jq
```

### Future: Desktop App UI

The desktop app needs UI components for:

1. **Insights Tab** - Shows personal insights, emerging topics
2. **Reports Section** - Shows weekly reports, trends
3. **Job Status** - Shows background job status (optional)

These are NOT yet implemented in the desktop app.

---

## How to Integrate Scheduler into API Server

To make jobs run automatically when the API starts:

### Step 1: Modify api_server.py

```python
# Add to imports
from src.jobs.scheduler import start_scheduler, shutdown_scheduler

# Modify lifespan function
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting background job scheduler...")
    start_scheduler()
    yield
    # Shutdown
    logger.info("Stopping background job scheduler...")
    shutdown_scheduler()

# Apply to FastAPI app
app = FastAPI(lifespan=lifespan)
```

### Step 2: Add Job Status Endpoint

```python
@app.get("/api/v2/jobs/status")
async def get_job_status():
    from src.jobs.scheduler import get_job_status
    return get_job_status()
```

### Step 3: Restart API

```bash
docker-compose restart api
```

---

## Viewing Job Logs

```bash
# View API logs (includes scheduler if integrated)
docker logs acms_api --tail 100 -f

# Filter for scheduler/job logs
docker logs acms_api 2>&1 | grep -i "scheduler\|job\|decay\|dedup\|cleanup"
```

---

## Testing Checkpoints

### Checkpoint: Verify Scheduler Status

```bash
# If scheduler integrated into API:
curl http://localhost:40080/api/v2/jobs/status | jq

# Expected output:
{
  "status": "running",
  "jobs": [
    {"id": "decay_job", "name": "Daily importance decay", "next_run": "2025-12-15 03:00:00"},
    {"id": "dedup_job", "name": "Weekly deduplication", "next_run": "2025-12-15 04:00:00"},
    {"id": "cleanup_job", "name": "Weekly cleanup", "next_run": "2025-12-15 05:00:00"}
  ]
}
```

### Checkpoint: Manual Job Execution

```bash
# Run decay job manually
PYTHONPATH=/path/to/acms python -c "
import asyncio
from src.jobs.maintenance import decay_job
result = asyncio.run(decay_job())
print(result)
"

# Expected output:
# {'job': 'decay', 'affected_count': 42, 'execution_time_ms': 150.5, ...}
```

### Checkpoint: Verify Insights API

```bash
# Get insights summary
curl -s "http://localhost:40080/api/v2/insights/summary?period_days=7" | jq '.data.top_topics[:3]'
```

---

## Future Enhancements

1. **Integrate scheduler into API server** - Jobs run automatically
2. **Add intelligence jobs** - topic_extraction, insight_generation
3. **Create UI components** - Insights tab, Reports view
4. **Add job status endpoint** - Monitor job health
5. **Add job triggers** - Manually trigger jobs from UI

---

*Last Updated: December 14, 2025*
