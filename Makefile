.PHONY: run install clean help

help:
	@echo "Available commands:"
	@echo "  make run              - Start the PDF Q&A application"
	@echo "  make install          - Install dependencies"
	@echo "  make clean            - Clean up temporary files"
	@echo "  make monitor          - Show memory and storage usage"
	@echo "  make models           - List available Ollama models"
	@echo "  make test-models      - Test models with invoice Q&A"
	@echo "  make test-story       - Test models with story comprehension"
	@echo "  make test-all         - Run all test suites"
	@echo "  make test-models-quick - Quick parameter compatibility test"

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
	@echo "Running tests..."
	@./venv/bin/python -m pytest tests/

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

test-models:
	@echo "🧪 Testing Model Compatibility..."
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/test_all_models.py

test-models-quick:
	@echo "🧪 Quick Model Compatibility Test..."
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/integration/test_model_compatibility.py

test-story:
	@echo "📖 Testing Story Comprehension..."
	@if [ ! -f venv/bin/python ]; then echo "❌ Please run 'make install' first"; exit 1; fi
	@./venv/bin/python tests/test_story_comprehension.py

test-all:
	@echo "🧪 Running All Tests..."
	@./tests/run_all_tests.sh

storage-report:
	@echo "💾 Storage Cleanup Report:"
	@echo "Documents older than 7 days or exceeding 20 count limit will be auto-removed"
	@find vector_stores -name "*.metadata" -mtime +7 2>/dev/null | wc -l | xargs -I {} echo "  Documents older than 7 days: {}"
	@echo "  Total documents: $$(find vector_stores -name "*.metadata" 2>/dev/null | wc -l | tr -d ' ')"