#!/bin/bash
# ACMS Debugging Setup Script
# Quickly enables debugging for full-stack flow tracing

set -e

echo "🔧 ACMS Debugging Setup"
echo "======================"
echo ""

# Check if we're in the right directory
if [ ! -f "src/api_server.py" ]; then
    echo "❌ Error: Must run from ACMS root directory"
    exit 1
fi

# Set environment variables for debugging
export LOG_LEVEL=DEBUG
export LOG_FORMAT=text
export PYTHONPATH=$(pwd)

echo "✅ Environment variables set:"
echo "   LOG_LEVEL=$LOG_LEVEL"
echo "   LOG_FORMAT=$LOG_FORMAT"
echo "   PYTHONPATH=$PYTHONPATH"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if Docker services are running
echo "🐳 Checking Docker services..."
if ! docker-compose ps | grep -q "Up"; then
    echo "⚠️  Docker services not running. Starting..."
    docker-compose up -d
    echo "   Waiting for services to be ready..."
    sleep 5
fi

echo "✅ Docker services:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}"
echo ""

# Create log directory if it doesn't exist
mkdir -p logs

echo "📝 Debugging setup complete!"
echo ""
echo "To start debugging:"
echo ""
echo "1. Backend API (Terminal 1):"
echo "   source venv/bin/activate"
echo "   export LOG_LEVEL=DEBUG"
echo "   PYTHONPATH=$(pwd) python3 src/api_server.py"
echo ""
echo "2. Desktop App (Terminal 2):"
echo "   cd desktop-app"
echo "   npm start -- --inspect"
echo ""
echo "3. Watch Logs (Terminal 3):"
echo "   tail -f api_server.log | grep -E '\[GATEWAY\]|\[API\]|ERROR'"
echo ""
echo "4. Open DevTools in Electron:"
echo "   View → Developer → Developer Tools"
echo ""
echo "📖 See DEBUGGING_GUIDE.md for complete instructions"
echo ""





