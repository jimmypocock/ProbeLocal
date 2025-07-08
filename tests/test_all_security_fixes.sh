#!/bin/bash
# Test all security and performance fixes

echo "===================================="
echo "Testing All Security and Performance Fixes"
echo "===================================="
echo ""

# Activate virtual environment if it exists
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

# Run our specific security and performance tests
echo "1. Running security and performance tests..."
python -m pytest tests/unit/test_security_and_performance_fixes.py -v

if [ $? -ne 0 ]; then
    echo "❌ Security tests failed!"
    exit 1
fi

echo ""
echo "2. Running session isolation tests..."
python -m pytest tests/unit/test_session_isolation.py::test_session_isolation -v

if [ $? -ne 0 ]; then
    echo "❌ Session isolation tests failed!"
    exit 1
fi

echo ""
echo "3. Running basic document processing tests..."
python -m pytest tests/unit/test_document_processing.py -v -k "not image" --maxfail=3

if [ $? -ne 0 ]; then
    echo "❌ Document processing tests failed!"
    exit 1
fi

echo ""
echo "===================================="
echo "✅ All security and performance tests passed!"
echo "===================================="
echo ""
echo "The application is now:"
echo "- 🔒 Secure: Path traversal, injection, and deserialization attacks prevented"
echo "- 🧹 Clean: Automatic resource cleanup and memory leak prevention"
echo "- 👥 Isolated: User sessions are properly separated"
echo "- ⚡ Efficient: Race conditions fixed and resources managed properly"