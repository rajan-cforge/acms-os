# ACMS Storage Cleanup Scripts

## Overview

These scripts clean and maintain ACMS storage across all tiers: PostgreSQL, Weaviate, Redis, and in-memory caches.

---

## Quick Start

### ⚠️ EMERGENCY: Clear Everything

```bash
# Delete ALL data (use for fresh starts only!)
./scripts/cleanup_all_storage.sh --nuclear
```

### 🧹 Safe Cleanup Options

```bash
# Clear only caches (safe, no data loss)
./scripts/cleanup_all_storage.sh --cache-only

# Clear only conversations
./scripts/cleanup_all_storage.sh --conversations-only

# Clear old data before specific date
./scripts/cleanup_all_storage.sh --before-date "2025-10-20"
```

### 🔍 AI-Powered Pollution Detection

```bash
# Dry run: See what would be deleted
python scripts/cleanup_polluted_memories.py --auto-detect --dry-run

# Remove memories with specific keyword
python scripts/cleanup_polluted_memories.py --keyword "association for computing machinery"

# Auto-detect and remove all polluted memories
python scripts/cleanup_polluted_memories.py --auto-detect
```

---

## Storage Tiers

### Redis (Semantic Cache)
- **What**: Query-response cache
- **Cleared by**: `--cache-only`, `--nuclear`
- **Impact**: Cache will rebuild naturally
- **Downtime**: None

### Weaviate (Vector DB)
- **What**: ConversationMemory_v1, ConversationThread_v1, ConversationTurn_v1, QueryCache_v1
- **Cleared by**: `--cache-only`, `--nuclear`
- **Impact**: Vector search will need re-indexing
- **Downtime**: Minimal (async rebuild)

### PostgreSQL (Main DB)
- **What**: memories, conversations, conversation_messages, query_analytics, user_feedback
- **Cleared by**: `--nuclear`, `--before-date`, `--conversations-only`
- **Impact**: Permanent data deletion
- **Downtime**: None (queries continue)

---

## Script Reference

### 1. `cleanup_all_storage.sh`

**Purpose**: Fast, brute-force cleanup across all storage tiers

**Options**:
```bash
--nuclear              Delete EVERYTHING (requires 'DELETE ALL' confirmation)
--cache-only           Clear Redis + Weaviate only (safe)
--conversations-only   Clear conversations only
--before-date DATE     Delete data before YYYY-MM-DD
```

**Examples**:
```bash
# Clear cache after test pollution
./scripts/cleanup_all_storage.sh --cache-only

# Remove old test data from development
./scripts/cleanup_all_storage.sh --before-date "2025-10-26"

# Nuclear reset for clean slate
./scripts/cleanup_all_storage.sh --nuclear
```

**Safety**:
- Requires explicit confirmation for `--nuclear`
- Shows what will be deleted before execution

---

### 2. `cleanup_polluted_memories.py`

**Purpose**: AI-powered detection and removal of low-quality/polluted memories

**Options**:
```bash
--auto-detect    Use AI to find polluted memories
--keyword TEXT   Find memories containing specific text
--before-date    Find memories before YYYY-MM-DD
--dry-run        Show what would be deleted without deleting
```

**Examples**:
```bash
# See what pollution exists (safe)
python scripts/cleanup_polluted_memories.py --auto-detect --dry-run

# Remove generic "association for computing machinery" pollution
python scripts/cleanup_polluted_memories.py --keyword "association for computing machinery"

# Remove all AI-detected pollution
python scripts/cleanup_polluted_memories.py --auto-detect

# Remove old memories from before production launch
python scripts/cleanup_polluted_memories.py --before-date "2025-10-20"
```

**Pollution Detection**:
- Generic patterns: "I don't have access", "multiple meanings", etc.
- Uncertainty language: "might", "could", "possibly" (high frequency)
- Short responses: <100 chars often indicate low quality
- Question-only content: Question without substantial answer

**Safety**:
- Requires typing 'DELETE' to confirm (unless `--dry-run`)
- Shows detailed report before deletion
- Includes pollution score and reasons for each memory

---

## Common Workflows

### After Integration Testing
```bash
# Tests create cache pollution
./scripts/cleanup_all_storage.sh --cache-only
```

### After Development Session
```bash
# Clean test data from today
./scripts/cleanup_all_storage.sh --before-date "2025-10-27"
```

### Production Pollution Cleanup
```bash
# Step 1: Identify pollution
python scripts/cleanup_polluted_memories.py --auto-detect --dry-run

# Step 2: Review report, then execute
python scripts/cleanup_polluted_memories.py --auto-detect

# Step 3: Verify clean
python scripts/cleanup_polluted_memories.py --auto-detect --dry-run
# Should show: "No polluted memories found!"
```

### Fresh Install Reset
```bash
# Complete wipe
./scripts/cleanup_all_storage.sh --nuclear

# Re-seed foundational data
python scripts/seed_foundational_knowledge.py  # (to be created)
```

---

## Monitoring & Metrics

### Check Pollution Rate
```bash
# Count total memories
psql -h localhost -U acms_user -d acms_db -c "SELECT COUNT(*) FROM memories;"

# Count polluted memories
python scripts/cleanup_polluted_memories.py --auto-detect --dry-run | grep "memories found"

# Calculate rate: polluted / total
```

### Check Cache Size
```bash
# Redis keys
docker exec acms_redis redis-cli DBSIZE

# Weaviate objects
# (check via Weaviate console or API)
```

---

## Safety Best Practices

1. **Always dry-run first**
   ```bash
   python scripts/cleanup_polluted_memories.py --auto-detect --dry-run
   ```

2. **Backup before nuclear option**
   ```bash
   # PostgreSQL backup
   pg_dump -h localhost -U acms_user acms_db > backup_$(date +%Y%m%d).sql

   # Weaviate backup (if needed)
   # Use Weaviate backup tools
   ```

3. **Test in development first**
   ```bash
   # Run on dev database
   export DB_HOST=localhost  # dev
   ./scripts/cleanup_all_storage.sh --cache-only

   # Verify no issues, then run on prod
   export DB_HOST=prod-db-host  # prod
   ```

4. **Review reports carefully**
   - Check "Pollution Report" output
   - Verify deletion candidates are correct
   - Look for false positives

---

## Troubleshooting

### "Permission denied"
```bash
# Make script executable
chmod +x scripts/cleanup_all_storage.sh
```

### "Database connection refused"
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
PGPASSWORD=acms_password psql -h localhost -U acms_user -d acms_db -c "SELECT 1;"
```

### "Weaviate connection failed"
```bash
# Check Weaviate is running
curl http://localhost:40480/v1/.well-known/ready

# Restart if needed
docker restart acms_weaviate
```

### "Redis FLUSHDB failed"
```bash
# Check Redis is running
docker exec acms_redis redis-cli PING
# Should return: PONG

# Restart if needed
docker restart acms_redis
```

---

## Automation

### Daily Cleanup Cron Job
```bash
# Add to crontab (crontab -e)
# Run cleanup at 2 AM daily
0 2 * * * /path/to/acms/scripts/cleanup_all_storage.sh --cache-only >> /var/log/acms_cleanup.log 2>&1
```

### Weekly Pollution Audit
```bash
# Add to crontab
# Sunday at 3 AM: Check for pollution
0 3 * * 0 cd /path/to/acms && python scripts/cleanup_polluted_memories.py --auto-detect --dry-run | mail -s "ACMS Pollution Report" admin@example.com
```

---

## Related Documentation

- **Pollution Research**: `docs/MEMORY_POLLUTION_PREVENTION_RESEARCH.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Testing**: `tests/README_SCENARIOS.md`
- **Deployment**: `docs/DEPLOYMENT.md`

---

## Support

For questions or issues:
1. Check `docs/MEMORY_POLLUTION_PREVENTION_RESEARCH.md` for deep dive
2. Review test results: `tests/phase0_test_results_summary.md`
3. Check logs: `/tmp/acms_api_*.log`

---

## Version History

- **v1.0** (2025-10-27): Initial cleanup scripts created
  - Bash script for multi-tier cleanup
  - Python script for AI-powered pollution detection
  - Full documentation
