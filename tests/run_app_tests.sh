#!/bin/bash
# Run app tests with services started automatically

set -e

echo "🚀 Starting services for testing..."

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve > /tmp/ollama.log 2>&1 &
    OLLAMA_PID=$!
    sleep 3
else
    echo "✓ Ollama already running"
    OLLAMA_PID=""
fi

# Check if API is running
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "Starting API server..."
    source venv/bin/activate
    python main.py > /tmp/api.log 2>&1 &
    API_PID=$!
    
    # Wait for API to be ready
    echo -n "Waiting for API to start"
    for i in {1..30}; do
        if curl -s http://localhost:8080/health > /dev/null 2>&1; then
            echo " ✓"
            break
        fi
        echo -n "."
        sleep 1
    done
else
    echo "✓ API already running"
    API_PID=""
fi

# Run the tests
echo ""
echo "🧪 Running tests..."
# Run all tests without skipping any
./venv/bin/python tests/run_tests.py --suite all --exitfirst $@

TEST_EXIT_CODE=$?

# Cleanup
echo ""
echo "🧹 Cleaning up..."

if [ ! -z "$API_PID" ]; then
    echo "Stopping API server..."
    kill $API_PID 2>/dev/null || true
    wait $API_PID 2>/dev/null || true
fi

if [ ! -z "$OLLAMA_PID" ]; then
    echo "Stopping Ollama..."
    kill $OLLAMA_PID 2>/dev/null || true
    wait $OLLAMA_PID 2>/dev/null || true
fi

exit $TEST_EXIT_CODE