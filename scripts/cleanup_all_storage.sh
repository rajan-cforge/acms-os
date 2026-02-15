#!/bin/bash
# ACMS Storage Cleanup Script
# Cleans all storage tiers: PostgreSQL, Weaviate, Redis
# Usage: ./scripts/cleanup_all_storage.sh [--nuclear|--cache-only|--conversations-only|--before-date DATE]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
NUCLEAR=false
CACHE_ONLY=false
CONVERSATIONS_ONLY=false
BEFORE_DATE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --nuclear)
            NUCLEAR=true
            shift
            ;;
        --cache-only)
            CACHE_ONLY=true
            shift
            ;;
        --conversations-only)
            CONVERSATIONS_ONLY=true
            shift
            ;;
        --before-date)
            BEFORE_DATE="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo "=================================================="
echo "ACMS Storage Cleanup Script"
echo "=================================================="
echo ""

# Confirmation for nuclear option
if [ "$NUCLEAR" = true ]; then
    echo -e "${RED}⚠️  NUCLEAR MODE: This will DELETE ALL DATA from all storage tiers!${NC}"
    echo -e "${RED}   - All memories${NC}"
    echo -e "${RED}   - All conversations${NC}"
    echo -e "${RED}   - All caches${NC}"
    echo -e "${RED}   - All analytics${NC}"
    echo ""
    read -p "Are you ABSOLUTELY sure? Type 'DELETE ALL' to confirm: " confirm

    if [ "$confirm" != "DELETE ALL" ]; then
        echo "Cleanup cancelled."
        exit 0
    fi
fi

# Function: Clear Redis cache
clear_redis() {
    echo -e "${YELLOW}[Redis] Clearing cache...${NC}"
    docker exec acms_redis redis-cli FLUSHDB
    echo -e "${GREEN}✅ Redis cache cleared${NC}"
}

# Function: Clear Weaviate collections
clear_weaviate() {
    echo -e "${YELLOW}[Weaviate] Clearing vector collections...${NC}"
    python3 << 'EOF'
import sys
sys.path.append('/path/to/acms')
from src.storage.weaviate_client import WeaviateClient

weaviate = WeaviateClient()
collections = ["QueryCache_v1", "ConversationMemory_v1", "ConversationThread_v1", "ConversationTurn_v1"]

for collection_name in collections:
    try:
        if weaviate.collection_exists(collection_name):
            collection = weaviate._client.collections.get(collection_name)
            # Delete all objects
            result = collection.data.delete_many(where={})
            print(f"✅ Cleared {collection_name}")
        else:
            print(f"⚠️  Collection {collection_name} doesn't exist")
    except Exception as e:
        print(f"❌ Error clearing {collection_name}: {e}")

weaviate.close()
EOF
    echo -e "${GREEN}✅ Weaviate collections cleared${NC}"
}

# Function: Clear PostgreSQL data
clear_postgres() {
    echo -e "${YELLOW}[PostgreSQL] Clearing database tables...${NC}"

    if [ -n "$BEFORE_DATE" ]; then
        echo "Deleting records before: $BEFORE_DATE"
        PGPASSWORD=acms_password psql -h localhost -U acms_user -d acms_db << EOF
DELETE FROM memories WHERE created_at < '$BEFORE_DATE';
DELETE FROM conversations WHERE created_at < '$BEFORE_DATE';
DELETE FROM conversation_messages WHERE created_at < '$BEFORE_DATE';
DELETE FROM query_analytics WHERE timestamp < '$BEFORE_DATE';
DELETE FROM user_feedback WHERE created_at < '$BEFORE_DATE';
EOF
    else
        PGPASSWORD=acms_password psql -h localhost -U acms_user -d acms_db << EOF
TRUNCATE TABLE user_feedback CASCADE;
TRUNCATE TABLE query_analytics CASCADE;
TRUNCATE TABLE conversation_messages CASCADE;
TRUNCATE TABLE conversations CASCADE;
TRUNCATE TABLE memories CASCADE;
EOF
    fi

    echo -e "${GREEN}✅ PostgreSQL data cleared${NC}"
}

# Execute based on flags
if [ "$CACHE_ONLY" = true ]; then
    echo "Mode: Cache-only cleanup"
    clear_redis
    clear_weaviate

elif [ "$CONVERSATIONS_ONLY" = true ]; then
    echo "Mode: Conversations-only cleanup"
    PGPASSWORD=acms_password psql -h localhost -U acms_user -d acms_db << EOF
TRUNCATE TABLE conversation_messages CASCADE;
TRUNCATE TABLE conversations CASCADE;
EOF
    echo -e "${GREEN}✅ Conversations cleared${NC}"

    # Also clear conversation vectors from Weaviate
    python3 << 'EOF'
import sys
sys.path.append('/path/to/acms')
from src.storage.weaviate_client import WeaviateClient

weaviate = WeaviateClient()
conv_collections = ["ConversationThread_v1", "ConversationTurn_v1"]

for collection_name in conv_collections:
    try:
        if weaviate.collection_exists(collection_name):
            collection = weaviate._client.collections.get(collection_name)
            result = collection.data.delete_many(where={})
            print(f"✅ Cleared {collection_name}")
    except Exception as e:
        print(f"❌ Error: {e}")

weaviate.close()
EOF

elif [ "$NUCLEAR" = true ]; then
    echo "Mode: NUCLEAR - Clearing ALL data"
    clear_redis
    clear_weaviate
    clear_postgres

else
    echo "Mode: Standard cleanup (cache + old data)"
    clear_redis

    if [ -n "$BEFORE_DATE" ]; then
        clear_postgres
    else
        echo "Use --before-date to clean old PostgreSQL data"
        echo "Use --nuclear to clear ALL PostgreSQL data"
    fi
fi

echo ""
echo "=================================================="
echo -e "${GREEN}Cleanup complete!${NC}"
echo "=================================================="
