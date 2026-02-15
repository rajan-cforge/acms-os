#!/bin/bash
# Start ACMS Desktop App
# Ensures API server is running before launching desktop app

echo "🚀 Starting ACMS Desktop..."

# Check if API server is running
API_HEALTH=$(curl -s http://localhost:40080/health 2>/dev/null)

if [ -z "$API_HEALTH" ]; then
    echo "⚠️  API server not running. Starting it now..."
    cd "$(dirname "$0")"
    source venv/bin/activate
    source .env
    python3 src/api_server.py > api_server.log 2>&1 &
    echo "⏳ Waiting for API server to start..."
    sleep 3
fi

# Check again
API_HEALTH=$(curl -s http://localhost:40080/health 2>/dev/null)
if [ -z "$API_HEALTH" ]; then
    echo "❌ Failed to start API server. Check api_server.log for errors."
    exit 1
fi

echo "✅ API server is running"
echo "📡 API available at: http://localhost:40080"
echo "📚 API docs: http://localhost:40080/docs"
echo ""
echo "🎨 Launching desktop app..."

cd desktop-app
npm start
