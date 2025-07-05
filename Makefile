.PHONY: run install clean help

help:
	@echo "Available commands:"
	@echo "  make run              - Start Greg (preferred port: 2402)"
	@echo "  make install          - Install dependencies"
	@echo "  make clean            - Clean up temporary files"
	@echo "  make monitor          - Show memory and storage usage"
	@echo "  make models           - List available Ollama models"
	@echo ""
	@echo "Testing commands:"
	@echo "  make test             - Run ALL tests (comprehensive: app + models)"
	@echo "  make test-app         - Test application (unit + API + UI)"
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
	@echo "🎮 Testing Application (Unit + API + UI)"
	@echo "======================================"
	@echo "Testing: Unit tests, API endpoints, and Streamlit UI"
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@echo "1️⃣ Running Unit Tests..."
	@./venv/bin/python -m pytest tests/unit/ -v
	@echo ""
	@echo "2️⃣ Testing API Functionality..."
	@./venv/bin/python tests/test_app_functionality.py
	@echo ""
	@echo "3️⃣ Testing Streamlit UI (Comprehensive)..."
	@if ! ./venv/bin/python -c "import selenium" 2>/dev/null; then \
		echo "📦 Installing Selenium..."; \
		./venv/bin/pip install selenium webdriver-manager; \
	fi
	@./venv/bin/python tests/test_streamlit_improved.py


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