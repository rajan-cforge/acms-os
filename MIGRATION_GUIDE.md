# ACMS Migration Guide - New Mac Setup

## Pre-Migration Status (Dec 29, 2025)

All containers have been **gracefully shut down** with data saved:
- PostgreSQL: All tables, memories, Plaid data saved
- Weaviate: All vectors and embeddings saved
- Redis: Cache data saved (can be regenerated if lost)

### Data Volumes on External Docker Drive
```
acms_postgres_data   - 249K lines of SQL data
acms_weaviate_data   - Vector embeddings (~93K memories)
acms_redis_data      - Query cache
acms_ollama_data     - Local LLM models
```

### Backup Created
```
migration_backup/acms_database_backup.sql  - Full PostgreSQL dump (safety backup)
```

---

## Migration Steps

### 1. On OLD Mac (Already Done)
- [x] Containers stopped gracefully with `docker-compose down`
- [x] Database backup created in `migration_backup/`
- [x] External Docker drive safely ejected

### 2. Transfer to NEW Mac

**Using Migration Assistant:**
1. Connect both Macs (Thunderbolt, WiFi, or Time Machine backup)
2. Run Migration Assistant on new Mac
3. Select old Mac as source
4. Transfer: Applications, Documents, User folders
5. Wait for completion

**Manual Transfer (if needed):**
1. Copy `/path/to/acms` folder to new Mac
2. Connect external Docker drive to new Mac

### 3. On NEW Mac - First Boot

#### Step 1: Install/Configure Docker Desktop
```bash
# If Docker Desktop didn't transfer, download from:
# https://www.docker.com/products/docker-desktop/

# Open Docker Desktop
# Go to Settings > Resources > Advanced
# Set the disk location to your external Docker drive
```

#### Step 2: Verify Docker Volumes Exist
```bash
docker volume ls | grep acms
# Should show:
# acms_postgres_data
# acms_weaviate_data
# acms_redis_data
# acms_ollama_data
```

#### Step 3: Start ACMS Containers
```bash
cd /path/to/acms
docker-compose up -d
```

#### Step 4: Wait for Services to Initialize
```bash
# Wait 30 seconds for all services to start
sleep 30

# Check all containers are running
docker-compose ps
```

Expected output:
```
NAME            STATUS
acms_api        Up (healthy)
acms_postgres   Up (healthy)
acms_weaviate   Up
acms_redis      Up (healthy)
acms_ollama     Up
```

#### Step 5: Verify Data Integrity
```bash
# Check API health
curl http://localhost:40080/health

# Check memory count
curl http://localhost:40080/stats | python3 -m json.tool

# Check Plaid connection
curl http://localhost:40080/api/plaid/status | python3 -m json.tool
```

#### Step 6: Start Desktop App
```bash
cd /path/to/acms/desktop-app
npm install  # Only if node_modules missing
npm start
```

---

## Troubleshooting

### If Docker Volumes Are Missing

Restore from SQL backup:
```bash
# Start fresh containers
docker-compose up -d

# Wait for postgres to be ready
sleep 10

# Restore database
docker exec -i acms_postgres psql -U acms -d acms < migration_backup/acms_database_backup.sql

# Restart to apply
docker-compose restart
```

### If Weaviate Data Is Missing

Re-sync vectors from PostgreSQL:
```bash
# Vectors can be regenerated from memory_items table
# Run the vectorization script
source venv/bin/activate
python scripts/migrate_to_unified_vectors.py
```

### If Plaid Shows No Connection

1. The Plaid tokens are encrypted in PostgreSQL
2. If encryption key (PLAID_ENCRYPTION_KEY) matches, data will work
3. If not, you'll need to reconnect accounts via Plaid Link

### If API Won't Start

Check logs:
```bash
docker-compose logs api --tail 50
```

Common fixes:
```bash
# Rebuild API container
docker-compose build api
docker-compose up -d api
```

---

## Environment Variables

These are stored in `.env` file and should transfer with the ACMS folder:

| Variable | Purpose |
|----------|---------|
| OPENAI_API_KEY | Embeddings generation |
| ANTHROPIC_API_KEY | Claude responses |
| PLAID_CLIENT_ID | Plaid integration |
| PLAID_SECRET | Plaid authentication |
| PLAID_ENCRYPTION_KEY | Encrypts Plaid tokens |
| ACMS_ENCRYPTION_KEY | General encryption |

**Important:** If `.env` doesn't transfer, you'll need to recreate it with your API keys.

---

## Quick Verification Checklist

After migration, verify these work:

- [ ] `docker-compose ps` shows 5 healthy containers
- [ ] `curl http://localhost:40080/health` returns OK
- [ ] Desktop app launches with `npm start`
- [ ] Chat view shows previous conversations
- [ ] Financial tab shows E*TRADE connection
- [ ] Email tab shows Gmail data (if connected)

---

## Support

If issues persist:
1. Check `docker-compose logs` for errors
2. Verify `.env` file exists with all keys
3. Ensure external Docker drive is mounted
4. Try `docker-compose down && docker-compose up -d`

Last updated: December 29, 2025
