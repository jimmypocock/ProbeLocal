.PHONY: run install clean help

help:
	@echo "Available commands:"
	@echo "  make run              - Start Greg (preferred port: 2402)"
	@echo "  make install          - Install dependencies"
	@echo "  make clean            - Clean up temporary files"
	@echo "  make clean-logs       - Clean up log files"
	@echo "  make monitor          - Show memory and storage usage"
	@echo "  make models           - List available Ollama models"
	@echo "  make download-embeddings - Download embedding models for offline use"
	@echo ""
	@echo "Testing commands:"
	@echo "  make test             - Run complete test suite (all except models)"
	@echo "  make test-quick       - Quick tests only (unit + streamlit, no services needed)"
	@echo "  make test-unit        - Unit tests for individual components"
	@echo "  make test-streamlit   - Native Streamlit logic tests (fast, reliable)"
	@echo "  make test-api         - Comprehensive API endpoint tests"
	@echo "  make test-integration - Test complete workflows and error scenarios"
	@echo "  make test-ui          - Test Streamlit UI with browser automation"
	@echo "  make test-performance - Test performance (load, memory, response times)"
	@echo "  make test-security    - Test security measures (file limits, injections, etc.)"
	@echo "  make test-visual      - Manual visual testing checklist"
	@echo "  make test-screens     - Run visual regression tests with Playwright"
	@echo "  make test-screens-baseline - Create baseline screenshots for visual tests"
	@echo "  make test-models      - Test all installed models (auto-detects)"
	@echo "  make test-models-quick - Quick test with current documents"
	@echo "  make list-models      - Show all models available for testing"
	@echo "  make test-critical    - Minimal critical-path browser tests"

run:
	@./run.sh

install:
	@echo "Installing dependencies..."
	@python3 -m venv venv
	@./venv/bin/pip install --upgrade pip
	@./venv/bin/pip install -r requirements.txt
	@echo "✅ Dependencies installed"

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf uploads/* vector_stores/* 2>/dev/null || true
	@echo "✅ Cleanup complete"

clean-logs:
	@echo "🧹 Cleaning log files..."
	@rm -f logs/*.log 2>/dev/null || true
	@echo "✅ Logs cleaned"

dev:
	@echo "Starting in development mode..."
	@./run.sh --dev

monitor:
	@echo "📊 System Resource Usage:"
	@echo "========================"
	@echo "Memory:"
	@echo "  Ollama: $$(ps aux | grep "ollama serve" | grep -v grep | awk '{print $$6/1024 " MB"}' || echo "Not running")"
	@echo "  Python API: $$(ps aux | grep "python main.py" | grep -v grep | awk '{print $$6/1024 " MB"}' || echo "Not running")"
	@echo "  Streamlit: $$(ps aux | grep "streamlit run" | grep -v grep | awk '{print $$6/1024 " MB"}' || echo "Not running")"
	@echo "  Total System: $$(( $$(sysctl -n hw.memsize) / 1024 / 1024 )) MB"
	@echo ""
	@echo "Storage:"
	@if [ -d "vector_stores" ]; then echo "  Vector stores: $$(du -sh vector_stores | cut -f1)"; else echo "  Vector stores: 0B"; fi
	@if [ -d "uploads" ]; then echo "  Uploads: $$(du -sh uploads | cut -f1)"; else echo "  Uploads: 0B"; fi
	@echo "  Document count: $$(find vector_stores -name "*.metadata" 2>/dev/null | wc -l | tr -d ' ')"
	@echo ""
	@echo "Ollama Models:"
	@which ollama >/dev/null 2>&1 && ollama list | tail -n +2 | awk '{print "  " $$1 " (" $$3 " " $$4 ")"}' || echo "  Ollama not found in PATH"

models:
	@echo "📦 Available Ollama Models:"
	@ollama list

download-embeddings:
	@echo "📥 Downloading Embedding Models for Offline Use..."
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python download_embeddings.py

storage-report:
	@echo "💾 Storage Cleanup Report:"
	@echo "Documents older than 7 days or exceeding 20 count limit will be auto-removed"
	@find vector_stores -name "*.metadata" -mtime +7 2>/dev/null | wc -l | xargs -I {} echo "  Documents older than 7 days: {}"
	@echo "  Total documents: $$(find vector_stores -name "*.metadata" 2>/dev/null | wc -l | tr -d ' ')"

test:
	@echo "🎮 Testing Application (Complete Test Suite)"
	@echo "==========================================="
	@echo "Testing: Unit, API, Integration, Streamlit & Performance"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./tests/run_app_tests.sh

test-models-quick:
	@echo "⚡ Quick Model Differentiation Test"
	@echo "=================================="
	@echo "Testing: Can model differentiate between documents in unified store"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/integration/test_model_quick.py

list-models:
	@echo "📋 Available Models for Testing"
	@echo "==============================="
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python scripts/list_testable_models.py

test-models-direct:
	@echo "🚀 Direct Model Testing (Fast)"
	@echo "=============================="
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@if [ -n "$(MODELS)" ]; then \
		echo "Testing specified models: $(MODELS)"; \
		./venv/bin/python tests/integration/test_unified_models_direct.py --models "$(MODELS)"; \
	else \
		echo "Auto-detecting and testing all installed models..."; \
		./venv/bin/python tests/integration/test_unified_models_direct.py; \
	fi

test-models:
	@echo "🤖 Testing Models"
	@echo "================="
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@if [ -n "$(MODELS)" ]; then \
		echo "Testing specified models: $(MODELS)"; \
		./venv/bin/python tests/integration/test_unified_models_isolated.py --models "$(MODELS)"; \
	else \
		echo "Auto-detecting and testing all installed models..."; \
		./venv/bin/python tests/integration/test_unified_models_isolated.py; \
	fi

test-quick:
	@echo "⚡ Running Quick Tests (Unit + Streamlit)"
	@echo "========================================"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./tests/run_tests_quick.sh

test-unit:
	@echo "🧪 Running Unit Tests"
	@echo "=================="
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/run_tests.py --suite unit

test-integration:
	@echo "🔗 Running Integration Tests"
	@echo "=========================="
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/run_tests.py --suite integration

test-streamlit:
	@echo "⚡ Running Native Streamlit AppTests"
	@echo "===================================="
	@echo "Testing app logic without browser overhead"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python -m pytest tests/streamlit/ -v

test-api:
	@echo "🌐 Running Comprehensive API Tests"
	@echo "=================================="
	@echo "Testing all backend endpoints and functionality"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python -m pytest tests/api/ -v

test-performance:
	@echo "⚡ Testing Performance"
	@echo "====================="
	@echo "Testing: load handling, memory usage, response times"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python -m pytest tests/performance/ -v

test-screens:
	@echo "📸 Running Visual Regression Tests"
	@echo "=================================="
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@echo "Checking for Playwright installation..."
	@./venv/bin/python -c "import playwright" 2>/dev/null || (echo "Installing Playwright..." && ./venv/bin/pip install playwright && ./venv/bin/playwright install chromium)
	@echo "Running visual regression tests..."
	@./venv/bin/python tests/visual_regression/test_visual_regression.py

test-screens-baseline:
	@echo "📷 Creating Baseline Screenshots"
	@echo "================================"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@echo "Checking for Playwright installation..."
	@./venv/bin/python -c "import playwright" 2>/dev/null || (echo "Installing Playwright..." && ./venv/bin/pip install playwright && ./venv/bin/playwright install chromium)
	@echo "Creating baseline screenshots..."
	@./venv/bin/python tests/visual_regression/test_visual_regression.py --create-baseline

# Removed duplicate sass targets - see lines 75-85