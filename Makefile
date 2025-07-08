.PHONY: run install clean help

help:
	@echo "Available commands:"
	@echo "  make run              - Start Greg (preferred port: 2402)"
	@echo "  make install          - Install dependencies"
	@echo "  make clean            - Clean up temporary files"
	@echo "  make monitor          - Show memory and storage usage"
	@echo "  make models           - List available Ollama models"
	@echo "  make download-embeddings - Download embedding models for offline use"
	@echo ""
	@echo "Styling commands:"
	@echo "  make sass             - Build SASS to CSS"
	@echo "  make sass-watch       - Build SASS and watch for changes"
	@echo "  make sass-compressed  - Build minified CSS for production"
	@echo ""
	@echo "Testing commands:"
	@echo "  make test             - Run ALL tests (comprehensive: app + models)"
	@echo "  make test-app         - Test application (unit + API + UI)"
	@echo "  make test-ui          - Test Streamlit UI with browser automation"
	@echo "  make test-integration - Test complete workflows and error scenarios"
	@echo "  make test-models      - Test model compatibility with various formats"
	@echo "  make test-models-quick - Quick test of file format support"
	@echo "  make test-security    - Test security measures (file limits, injections, etc.)"
	@echo "  make test-performance - Test performance (load, memory, response times)"

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

test:
	@echo "🧪 Running Complete Test Suite"
	@echo "=============================="
	@echo "This will run ALL tests: unit, app (API+UI), and models"
	@echo ""
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./tests/run_all_tests_comprehensive.sh

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

sass:
	@echo "🎨 Building SASS to CSS..."
	@python scripts/build_sass.py

sass-watch:
	@echo "👀 Building SASS and watching for changes..."
	@python scripts/build_sass.py --watch

sass-compressed:
	@echo "📦 Building minified CSS for production..."
	@python scripts/build_sass.py --compressed


test-models-quick:
	@echo "⚡ Quick Model Format Test"
	@echo "========================="
	@echo "Testing: One model with multiple file formats"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/test_format_quick.py

test-models:
	@echo "🤖 Testing Specific Models"
	@echo "==========================="
	@echo "Usage: make test-models MODELS='mistral,llama3'"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@if [ -n "$(MODELS)" ]; then \
		./venv/bin/python tests/test_multiformat_models.py --models "$(MODELS)"; \
	else \
		echo "Please specify models: make test-models MODELS='mistral,llama3'"; \
	fi

test-app:
	@echo "🎮 Testing Application (Complete Test Suite)"
	@echo "==========================================="
	@echo "Testing: Unit, API, UI, Integration, Security & Performance"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./tests/run_app_tests.sh

test-fast:
	@echo "⚡ Running Fast Tests Only"
	@echo "========================="
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/run_tests.py --suite all --fast --parallel

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

test-coverage:
	@echo "📊 Running Tests with Coverage"
	@echo "============================"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/run_tests.py --suite all --coverage --fast

test-ci:
	@echo "🤖 Running CI Test Suite"
	@echo "======================"
	@export CI=true
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python -m pytest tests/ -m "not skip_ci" --maxfail=5 -n auto


test-ui:
	@echo "🧪 Running Streamlit UI Tests"
	@echo "============================="
	@echo "Testing UI with browser automation (Selenium)"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python -m pytest tests/ui/ -v --tb=short

test-visual:
	@echo "🎨 Running Visual Regression Tests"
	@echo "=================================="
	@echo "⚠️  Visual regression tests not implemented for Selenium yet"
	@echo "Use manual testing or implement screenshot comparison with Selenium"

test-visual-baseline:
	@echo "📸 Creating Visual Regression Baseline"
	@echo "====================================="
	@python tests/visual_regression/test_visual_regression.py --create-baseline

# Removed duplicate test-integration target


test-security:
	@echo "🔒 Testing Security Measures"
	@echo "============================"
	@echo "Testing: file limits, malicious files, injections, etc."
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/test_security.py

test-performance:
	@echo "⚡ Testing Performance"
	@echo "====================="
	@echo "Testing: load handling, memory usage, response times"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/test_performance.py

storage-report:
	@echo "💾 Storage Cleanup Report:"
	@echo "Documents older than 7 days or exceeding 20 count limit will be auto-removed"
	@find vector_stores -name "*.metadata" -mtime +7 2>/dev/null | wc -l | xargs -I {} echo "  Documents older than 7 days: {}"
	@echo "  Total documents: $$(find vector_stores -name "*.metadata" 2>/dev/null | wc -l | tr -d ' ')"

# Removed duplicate sass targets - see lines 75-85