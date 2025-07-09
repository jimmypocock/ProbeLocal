#!/bin/bash
# Run quick test suite: unit + streamlit tests only (no api/integration/performance)

set -e

echo "🧪 Running Quick Test Suite"
echo "=========================="
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Check if venv exists
if [ ! -f venv/bin/python ]; then
    echo "❌ Virtual environment not found. Please run 'make install' first"
    exit 1
fi

# Track overall success
ALL_PASSED=true

# Run unit tests
echo "1️⃣  Running Unit Tests..."
echo "========================"
if ./venv/bin/python -m pytest tests/unit/ -v --tb=short; then
    echo "✅ Unit tests passed"
else
    echo "❌ Unit tests failed"
    ALL_PASSED=false
fi
echo ""

# Run Streamlit logic tests
echo "2️⃣  Running Streamlit Logic Tests..."
echo "==================================="
if ./venv/bin/python -m pytest tests/streamlit/ -v --tb=short; then
    echo "✅ Streamlit tests passed"
else
    echo "❌ Streamlit tests failed"
    ALL_PASSED=false
fi
echo ""

# No API tests in quick mode

# Summary
echo ""
echo "================================"
if [ "$ALL_PASSED" = true ]; then
    echo "✅ All quick tests passed!"
    echo ""
    echo "To run the full test suite:"
    echo "  - Run 'make test' for all tests"
    echo "  - Run 'make test-api' for API tests"
    echo "  - Run 'make test-integration' for integration tests"
    exit 0
else
    echo "❌ Some tests failed. Please review the output above."
    exit 1
fi