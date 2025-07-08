#!/bin/bash
# Run tests with proper environment

echo "🎮 Running Greg AI Playground Tests"
echo "==================================="

# Activate virtual environment
source venv/bin/activate

# Clean up any existing services
echo "🧹 Cleaning up services..."
pkill -f "python main.py" || true
pkill -f "streamlit run" || true
sleep 2

# Run unit tests
echo -e "\n1️⃣ Running Unit Tests..."
python -m pytest tests/unit/test_all_file_types.py tests/unit/test_web_search.py -v --tb=short -q

# Test API
echo -e "\n2️⃣ Testing API..."
python main.py &
API_PID=$!
sleep 5

# Check if API is running
if curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "✅ API started successfully"
    
    # Run a simple functionality test
    echo "Testing basic upload..."
    echo "Test content" > /tmp/test.txt
    curl -s -X POST http://localhost:8080/upload \
        -F "file=@/tmp/test.txt" \
        -F "model=mistral" | grep -q "document_id" && echo "✅ Upload works" || echo "❌ Upload failed"
else
    echo "❌ API failed to start"
fi

# Kill API
kill $API_PID 2>/dev/null
wait $API_PID 2>/dev/null

echo -e "\n✅ Basic tests complete"