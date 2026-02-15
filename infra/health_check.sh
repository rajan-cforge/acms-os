#!/bin/bash
# ACMS Infrastructure Health Check Script
# Checks all services: PostgreSQL, Redis, Weaviate (existing), Ollama

set -e

echo "==================================="
echo "ACMS Infrastructure Health Check"
echo "==================================="

EXIT_CODE=0

# Check PostgreSQL (port 40432)
echo -n "PostgreSQL (40432): "
if nc -z localhost 40432 2>/dev/null; then
    echo "✅ UP"
else
    echo "❌ DOWN"
    EXIT_CODE=1
fi

# Check Redis (port 40379)
echo -n "Redis (40379): "
if nc -z localhost 40379 2>/dev/null; then
    if redis-cli -p 40379 PING 2>/dev/null | grep -q PONG; then
        echo "✅ UP (responds to PING)"
    else
        echo "⚠️  PORT OPEN but not responding"
        EXIT_CODE=1
    fi
else
    echo "❌ DOWN"
    EXIT_CODE=1
fi

# Check Weaviate (existing instance at 8080 or 8081)
echo -n "Weaviate (8080/8081): "
if curl -sf http://localhost:8080/v1/.well-known/ready >/dev/null 2>&1; then
    echo "✅ UP (port 8080)"
elif curl -sf http://localhost:8081/v1/.well-known/ready >/dev/null 2>&1; then
    echo "✅ UP (port 8081)"
else
    echo "❌ DOWN (checked 8080 and 8081)"
    EXIT_CODE=1
fi

# Check Ollama (port 40434)
echo -n "Ollama (40434): "
if curl -sf http://localhost:40434/api/tags >/dev/null 2>&1; then
    MODELS=$(curl -s http://localhost:40434/api/tags | python3 -c "import sys, json; models=json.load(sys.stdin).get('models',[]); print(len(models))" 2>/dev/null || echo "0")
    echo "✅ UP ($MODELS models available)"

    # Check for required models
    HAS_EMBEDDING=$(curl -s http://localhost:40434/api/tags | python3 -c "import sys, json; models=[m['name'] for m in json.load(sys.stdin).get('models',[])]; print('all-minilm' in str(models).lower())" 2>/dev/null || echo "False")
    HAS_LLM=$(curl -s http://localhost:40434/api/tags | python3 -c "import sys, json; models=[m['name'] for m in json.load(sys.stdin).get('models',[])]; print('llama3.2:1b' in str(models).lower())" 2>/dev/null || echo "False")

    if [ "$HAS_EMBEDDING" = "True" ] && [ "$HAS_LLM" = "True" ]; then
        echo "  ✅ Required models: all-minilm:22m ✓ llama3.2:1b ✓"
    else
        echo "  ⚠️  Missing required models"
        [ "$HAS_EMBEDDING" != "True" ] && echo "    ❌ all-minilm:22m not found"
        [ "$HAS_LLM" != "True" ] && echo "    ❌ llama3.2:1b not found"
        EXIT_CODE=1
    fi
else
    echo "❌ DOWN"
    EXIT_CODE=1
fi

echo "==================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All services healthy"
else
    echo "❌ Some services are down"
fi
echo "==================================="

exit $EXIT_CODE
