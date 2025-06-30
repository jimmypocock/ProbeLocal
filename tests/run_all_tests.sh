#!/bin/bash

# ProbeLocal Comprehensive Test Runner
# Runs all test suites and generates a summary report

set -e

echo "🧪 ProbeLocal Comprehensive Test Suite"
echo "====================================="
echo ""

# Check if services are running
check_services() {
    echo "Checking services..."
    
    # Check Ollama
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "❌ Ollama service not running. Please run 'make run' first."
        exit 1
    fi
    
    # Check API
    if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "❌ API service not running. Please run 'make run' first."
        exit 1
    fi
    
    echo "✅ All services running"
    echo ""
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Activate virtual environment
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo "❌ Virtual environment not found. Please run 'make install' first."
    exit 1
fi

# Check services
check_services

# Parse arguments
MODELS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --models)
            shift
            MODELS="$@"
            break
            ;;
        -h|--help)
            echo "Usage: $0 [--models model1 model2 ...]"
            echo ""
            echo "Options:"
            echo "  --models    Specific models to test (default: all available)"
            echo "  -h, --help  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h for help"
            exit 1
            ;;
    esac
    shift
done

# Create results directory
mkdir -p "$SCRIPT_DIR/results"

# Build model arguments
MODEL_ARGS=""
if [ -n "$MODELS" ]; then
    MODEL_ARGS="--models $MODELS"
fi

echo "📋 Test Configuration"
echo "===================="
if [ -n "$MODELS" ]; then
    echo "Models: $MODELS"
else
    echo "Models: All available"
fi
echo ""

# Run invoice Q&A tests
echo "1️⃣ Running Invoice Q&A Tests..."
echo "==============================="
if python "$SCRIPT_DIR/test_all_models.py" $MODEL_ARGS; then
    echo "✅ Invoice tests completed"
else
    echo "❌ Invoice tests failed"
    INVOICE_FAILED=1
fi
echo ""

# Run story comprehension tests
echo "2️⃣ Running Story Comprehension Tests..."
echo "======================================"
if [ -f "$SCRIPT_DIR/fixtures/test_story.pdf" ]; then
    if python "$SCRIPT_DIR/test_story_comprehension.py" $MODEL_ARGS; then
        echo "✅ Story comprehension tests completed"
    else
        echo "❌ Story comprehension tests failed"
        STORY_FAILED=1
    fi
else
    echo "⚠️  Story PDF not found at $SCRIPT_DIR/fixtures/test_story.pdf"
    echo "   Please convert tests/test_story.txt to PDF first"
    STORY_SKIPPED=1
fi
echo ""

# Generate summary report
echo "📊 Test Summary"
echo "==============="

# Find latest result files
LATEST_INVOICE=$(ls -t "$SCRIPT_DIR/results"/model_test_results_*.json 2>/dev/null | head -1)
LATEST_STORY=$(ls -t "$SCRIPT_DIR/results"/story_comprehension_*.json 2>/dev/null | head -1)

if [ -n "$LATEST_INVOICE" ] && [ -z "$INVOICE_FAILED" ]; then
    echo "✅ Invoice Q&A Tests: PASSED"
    echo "   Results: $(basename "$LATEST_INVOICE")"
else
    echo "❌ Invoice Q&A Tests: FAILED"
fi

if [ -n "$LATEST_STORY" ] && [ -z "$STORY_FAILED" ]; then
    echo "✅ Story Comprehension Tests: PASSED"
    echo "   Results: $(basename "$LATEST_STORY")"
elif [ -n "$STORY_SKIPPED" ]; then
    echo "⚠️  Story Comprehension Tests: SKIPPED"
else
    echo "❌ Story Comprehension Tests: FAILED"
fi

echo ""
echo "All results saved in: $SCRIPT_DIR/results/"
echo ""

# Exit with appropriate code
if [ -n "$INVOICE_FAILED" ] || [ -n "$STORY_FAILED" ]; then
    exit 1
else
    exit 0
fi