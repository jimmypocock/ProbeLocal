# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Greg is an AI playground featuring a Retrieval-Augmented Generation (RAG) system with three main components:

1. **Ollama Service** (port 11434): Runs local LLMs (Mistral, Llama, Phi, Deepseek)
2. **FastAPI Backend** (port 8080): Handles document processing, vector storage, and Q&A logic
3. **Streamlit Frontend** (port 2402): Provides web UI for document upload and querying

## Critical: How to Work with This Project

### 1. ALWAYS Use Make Commands
This project uses a Makefile for ALL operations. Never run Python commands directly.

### 2. Virtual Environment
The virtual environment is managed automatically by the Makefile and scripts. You do NOT need to:
- Manually activate venv
- Run pip install
- Run playwright install

Everything is handled by `make install` and the startup scripts.

### 3. Starting the Application
```bash
# ONE COMMAND starts everything (recommended):
make run

# This automatically:
# - Checks/installs dependencies
# - Starts Ollama
# - Starts API server
# - Starts SASS watcher
# - Starts Streamlit UI
```

## Testing the Application

### Complete Test Suite
```bash
# Run ALL tests (comprehensive)
make test

# Test specific components
make test-app          # Unit + API + UI tests
make test-ui           # Streamlit UI tests only
make test-integration  # End-to-end workflows
make test-models       # Model compatibility
make test-security     # Security measures
make test-performance  # Performance benchmarks
```

### Test Infrastructure
- **UI Tests**: Use Playwright for browser automation
- **Test Runner**: `tests/green_test_runner.py` orchestrates all tests
- **Fixtures**: Test files in `tests/fixtures/`
- **Results**: JSON reports in `tests/results/`

### Common Test Issues & Solutions

1. **Playwright Browser Error**:
   - The test runner automatically installs browsers if needed
   - If services are already running (via `make run`), tests detect and use them

2. **Port Conflicts**:
   - Tests check if services are already running before starting new instances
   - No need to stop `make run` before testing

3. **Import Errors**:
   - All imports should use `from src.module` format
   - Never use relative imports in tests

## Important Make Commands

### Development
- `make run` - Start everything (recommended)
- `make dev` - Development mode
- `make clean` - Clean temporary files
- `make monitor` - Monitor resources
- `make models` - List available models

### Styling
- `make sass` - Build CSS once
- `make sass-watch` - Auto-rebuild CSS (runs with `make run`)
- `make sass-compressed` - Production build

### Testing
- `make test` - Run complete test suite
- `make test-app` - Application tests
- `make test-ui` - UI tests only
- `make test-models MODELS='mistral,llama3'` - Test specific models

## Architecture Details

### Data Flow
1. Documents uploaded via Streamlit (port 2402) → FastAPI (port 8080)
2. FastAPI processes documents → chunks → embeddings → FAISS vector store
3. User queries → FAISS similarity search → context retrieval → Ollama LLM → response

### File Structure
```
/
├── src/                    # Core application code
│   ├── ui/                # Streamlit UI components
│   ├── performance/       # Performance monitoring
│   └── *.py              # Core modules
├── static/
│   ├── scss/             # SASS source files
│   └── css/              # Compiled CSS (gitignored)
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── ui/               # UI tests (Playwright)
│   └── fixtures/         # Test data
├── vector_stores/        # Persistent FAISS indexes
├── uploads/              # Temporary file storage
├── app.py               # Streamlit frontend
├── main.py              # FastAPI backend
├── run.sh               # Startup script
└── Makefile             # All commands
```

### Key Modules
- `src/config.py`: Environment configuration and memory optimization
- `src/document_processor.py`: Multi-format document processing
- `src/qa_chain.py`: RAG pipeline with FAISS vector search
- `src/ui/components.py`: Reusable Streamlit components
- `src/ui/lazy_loading.py`: Document list with pagination

### Session State Management
Streamlit session state is initialized in `app.py` and `src/ui/components.py`:
- Messages, document IDs, notifications
- Model selection, settings
- Auto-saves important state changes

### Vector Store Persistence
- Stores saved in `vector_stores/{document_id}.faiss`
- Metadata in `{document_id}_metadata.json`
- Auto-cleanup: >7 days old or >20 documents

### Error Handling Best Practices
- Connection errors show helpful messages
- Processing timeouts: 300s for large files
- Memory monitoring prevents OOM
- All errors logged with context

## Model Compatibility

### Known Issues
- **Deepseek**: Requires minimal parameters (only `num_ctx`)
- Some models don't support `num_thread`, `repeat_penalty`, or custom `stop` tokens
- Model config stored in `src/model_config.json`

### Testing Models
```bash
# Test all models with PDF Q&A
make test-models

# Test specific models
make test-models MODELS='deepseek,mistral'

# Quick format compatibility test
make test-models-quick
```

## CSS/Styling System

### SASS Structure
- Source: `static/scss/`
- Output: `static/css/` (gitignored)
- Auto-compilation with `make run`
- BEM naming convention
- Design tokens for consistency

### Adding Styles
1. Edit SCSS files in `static/scss/`
2. Changes compile automatically with `make run`
3. Use existing variables and mixins
4. Follow component-based organization

## Best Practices

### When Making Changes
1. Run `make run` to start the app
2. Make changes to code
3. Test with `make test-app` or specific test commands
4. Verify UI changes visually
5. Run `make test` before committing

### Common Pitfalls to Avoid
- Don't manually manage venv - use make commands
- Don't add inline CSS - use SCSS files
- Don't skip tests - all must pass
- Don't use relative imports - use `from src.module`
- Don't hardcode ports - use config values

### Debugging Tips
- Check service status with `make monitor`
- UI test screenshots saved to `tests/ui/screenshots/`
- Logs available in terminal output
- Use `--verbose` flag for detailed test output

## Quick Reference

```bash
# Start development
make run

# Run all tests
make test

# Clean and restart
make clean && make run

# Check what's running
make monitor

# Update styles
# (automatic with make run, but can force rebuild)
make sass
```

Remember: This is a monorepo with integrated services. The Makefile is your primary interface for all operations.