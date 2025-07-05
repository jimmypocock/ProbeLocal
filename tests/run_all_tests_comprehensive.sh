#!/bin/bash

# Greg Comprehensive Test Runner (including UI tests)
# Runs all test suites including UI tests and generates a summary report

set -e

echo "🧪 Greg Comprehensive Test Suite (with UI)"
echo "=========================================="
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
    
    # Check Streamlit
    if ! curl -s http://localhost:2402 > /dev/null 2>&1; then
        echo "❌ Streamlit not running. Please run 'make run' first."
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
SKIP_UI=0
RUN_MODEL_TESTS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --models)
            shift
            MODELS="$@"
            RUN_MODEL_TESTS=1
            break
            ;;
        --skip-ui)
            SKIP_UI=1
            ;;
        --with-models)
            RUN_MODEL_TESTS=1
            ;;
        -h|--help)
            echo "Usage: $0 [--skip-ui] [--with-models] [--models model1 model2 ...]"
            echo ""
            echo "Options:"
            echo "  --skip-ui      Skip UI tests (useful for CI/CD)"
            echo "  --with-models  Include model performance tests"
            echo "  --models       Test specific models (implies --with-models)"
            echo "  -h, --help     Show this help message"
            echo ""
            echo "By default, runs app tests (unit, API, UI, security, performance)"
            echo "Model tests are only run if --with-models is specified"
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
echo "Skip UI Tests: $([ $SKIP_UI -eq 1 ] && echo 'Yes' || echo 'No')"
echo ""

# Run application tests (unit + API + UI)
echo "1️⃣ Running Application Tests..."
echo "================================"
echo "Running unit tests, API functionality, and UI tests..."

# Unit tests
if python -m pytest "$SCRIPT_DIR/unit/" -v; then
    echo "✅ Unit tests completed"
else
    echo "❌ Unit tests failed"
    APP_FAILED=1
fi
echo ""

# API tests
if python "$SCRIPT_DIR/test_app_functionality.py"; then
    echo "✅ API functionality tests completed"
else
    echo "❌ API functionality tests failed"
    APP_FAILED=1
fi
echo ""

# UI tests (if not skipped)
if [ $SKIP_UI -eq 0 ]; then
    # Install Playwright if needed
    if ! python -c "import playwright" 2>/dev/null; then
        echo "📦 Installing Playwright..."
        pip install playwright pytest-playwright
        playwright install chromium
    fi
    
    if python "$SCRIPT_DIR/test_streamlit_ui.py"; then
        echo "✅ UI tests completed"
    else
        echo "❌ UI tests failed"
        APP_FAILED=1
    fi
else
    echo "⚠️ UI Tests: SKIPPED"
fi
echo ""

# Model tests are now separate - only run if explicitly requested
if [ -n "$RUN_MODEL_TESTS" ]; then
    echo "2️⃣ Running Model Tests..."
    echo "========================="
    if python "$SCRIPT_DIR/test_all_models.py" $MODEL_ARGS; then
        echo "✅ Model tests completed"
    else
        echo "❌ Model tests failed"
        MODEL_FAILED=1
    fi
    echo ""

    # Run multi-format tests
    echo "3️⃣ Running Multi-Format Tests..."
    echo "================================"
    if python "$SCRIPT_DIR/test_multiformat_models.py" $MODEL_ARGS; then
        echo "✅ Multi-format tests completed"
    else
        echo "❌ Multi-format tests failed"
        FORMAT_FAILED=1
    fi
    echo ""
fi

# Run security tests
echo "4️⃣ Running Security Tests..."
echo "==========================="
if python "$SCRIPT_DIR/test_security.py"; then
    echo "✅ Security tests completed"
else
    echo "❌ Security tests failed"
    SECURITY_FAILED=1
fi
echo ""

# Run performance tests
echo "5️⃣ Running Performance Tests..."
echo "=============================="
if python "$SCRIPT_DIR/test_performance.py"; then
    echo "✅ Performance tests completed"
else
    echo "❌ Performance tests failed"
    PERFORMANCE_FAILED=1
fi
echo ""

# Generate summary report
echo "📊 Test Summary"
echo "==============="

# Check test results
if [ -z "$APP_FAILED" ]; then
    echo "✅ Application Tests: PASSED"
else
    echo "❌ Application Tests: FAILED"
fi

if [ -n "$RUN_MODEL_TESTS" ]; then
    if [ -z "$MODEL_FAILED" ]; then
        echo "✅ Model Tests: PASSED"
    else
        echo "❌ Model Tests: FAILED"
    fi

    if [ -z "$FORMAT_FAILED" ]; then
        echo "✅ Multi-Format Tests: PASSED"  
    else
        echo "❌ Multi-Format Tests: FAILED"
    fi
fi

if [ -z "$SECURITY_FAILED" ]; then
    echo "✅ Security Tests: PASSED"
else
    echo "❌ Security Tests: FAILED"
fi

if [ -z "$PERFORMANCE_FAILED" ]; then
    echo "✅ Performance Tests: PASSED"
else
    echo "❌ Performance Tests: FAILED"
fi

echo ""
echo "All results saved in: $SCRIPT_DIR/results/"
echo ""

# Exit with appropriate code
if [ -n "$APP_FAILED" ] || [ -n "$MODEL_FAILED" ] || [ -n "$FORMAT_FAILED" ] || [ -n "$SECURITY_FAILED" ] || [ -n "$PERFORMANCE_FAILED" ]; then
    exit 1
else
    echo "🎉 All tests passed!"
    exit 0
fi