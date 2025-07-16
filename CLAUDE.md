# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Greg is a local AI playground featuring a Retrieval-Augmented Generation (RAG) system with automatic document preprocessing:

1. **Ollama Service** (port 11434): Runs local LLMs (Mistral, Llama, Phi, Deepseek)
2. **FastAPI Backend** (port 8080): Handles document processing, vector storage, and Q&A logic
3. **Streamlit Frontend** (port 2402): Read-only UI for document Q&A and web search
4. **Document Preprocessing**: Automatic processing of documents in `/documents` folder at startup

## Critical: How to Work with This Project

### 1. ALWAYS Use Make Commands
This project uses a Makefile for ALL operations. Never run Python commands directly.

### 2. Virtual Environment
The virtual environment is managed automatically by the Makefile and scripts. You do NOT need to:
- Manually activate venv
- Run pip install
- Run playwright install

Everything is handled by `make install` and the startup scripts.

### 3. Document Management
Documents are managed via the filesystem, not through the UI:
- Place documents in the `/documents` folder
- Run `make run` to process them automatically
- All documents are processed at startup
- To add/remove documents, restart the app

### 4. Starting the Application
```bash
# ONE COMMAND starts everything (recommended):
make run

# This automatically:
# - Checks/installs dependencies
# - Starts Ollama
# - Starts API server
# - Clears vector stores
# - Processes all documents in /documents folder
# - Starts Streamlit UI
```

## Testing the Application

### Testing Strategy
Greg uses a streamlined testing approach focused on reliability and speed:

1. **Unit Tests** - Fast tests including security validations
2. **Native Streamlit Tests** - Logic tests using AppTest framework
3. **API Tests** - Comprehensive backend coverage
4. **Integration Tests** - Service interaction tests
5. **Performance Tests** - Optimization and caching tests

### Quick Test Commands
```bash
# Run all tests (recommended)
make test

# Quick tests for development (no services needed)
make test-quick        # Unit + Streamlit tests only (~1 minute)

# Individual test suites
make test-unit         # Unit tests (includes security)
make test-streamlit    # Native logic tests (~30s)
make test-api          # API endpoint tests (~1 minute)
make test-integration  # Integration tests
make test-performance  # Performance tests

# Visual regression testing
make test-screens           # Run visual regression tests
make test-screens-baseline  # Create baseline screenshots

# Model testing
make test-models       # Test specific models
make test-models-quick # Quick compatibility test
```

### Test Infrastructure
- **No Browser Tests**: We removed Selenium tests in favor of native Streamlit tests
- **Test Runner**: Simplified test runner in `tests/run_tests.py`
- **Fixtures**: Test files in `tests/fixtures/`
- **Security Tests**: Included in unit tests

### Common Test Issues & Solutions

1. **Port Conflicts**:
   - Tests check if services are already running before starting new instances
   - No need to stop `make run` before testing

2. **Import Errors**:
   - All imports should use `from src.module` format
   - Never use relative imports in tests

3. **Model Tests**:
   - Require models to be downloaded first
   - Use `make test-models MODELS='mistral'` to test specific models

### Best Practices for Testing
- Run `make test-quick` during development for fast feedback
- Run `make test` before committing
- Use `make test-streamlit` for quick logic checks
- Run `make test-screens` after UI changes
- Model tests are separate from regular tests
- All tests should pass before merging

## Important Make Commands

### Development
- `make run` - Start everything (recommended)
- `make dev` - Development mode
- `make clean` - Clean temporary files
- `make monitor` - Monitor resources
- `make models` - List available models

### Styling
- CSS is now in plain CSS format at `assets/css/main.css`
- No SASS compilation needed anymore
- Styles are loaded via `src/ui/style_loader.py`

### Testing
- `make test` - Run all tests (unit + streamlit + API + integration + performance)
- `make test-quick` - Quick tests only (unit + streamlit, no services needed)
- `make test-unit` - Unit tests (includes security tests)
- `make test-streamlit` - Native Streamlit logic tests (fastest)
- `make test-api` - API endpoint tests
- `make test-integration` - Integration tests
- `make test-performance` - Performance optimization tests
- `make test-screens` - Visual regression tests
- `make test-screens-baseline` - Create baseline screenshots
- `make test-models MODELS='mistral,llama3'` - Test specific models
- `make test-models-quick` - Quick model compatibility test

## Architecture Details

### Data Flow
1. Documents placed in `/documents` folder
2. On startup: preprocessing script → FastAPI → unified document processor → chunks → embeddings → single FAISS vector store
3. User queries → UnifiedQAChain routes query → FAISS similarity search → context retrieval → Ollama LLM → streaming response
4. Web search queries → Direct to LLM with web context
5. All documents stored in single vector store with source metadata for proper attribution

### File Structure
```
/
├── documents/            # Place your documents here (gitignored)
│   └── README.md        # Instructions for users
├── scripts/              # Utility scripts
│   └── preprocess_documents.py  # Document preprocessing
├── src/                  # Core application code
│   ├── ui/              # Streamlit UI components
│   ├── performance/     # Performance monitoring
│   └── *.py            # Core modules
├── assets/
│   └── css/            # CSS files (main.css)
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   ├── streamlit/      # Streamlit native tests
│   ├── api/            # API tests
│   ├── performance/    # Performance tests
│   ├── results/        # Test output files (gitignored)
│   └── fixtures/       # Test data
├── vector_stores/      # Persistent FAISS indexes (cleared on startup)
├── uploads/            # Temporary file storage
├── app.py             # Streamlit frontend
├── main.py            # FastAPI backend
├── run.sh             # Startup script
└── Makefile             # All commands
```

### Key Modules
- `src/config.py`: Environment configuration and memory optimization
- `src/unified_document_processor.py`: Unified multi-document processing into single vector store
- `src/qa_chain_unified.py`: Unified QA chain with intelligent routing and streaming
- `src/ui/components.py`: Reusable Streamlit components
- `src/ui/lazy_loading.py`: Document list with pagination
- `src/ui/drag_drop.py`: Custom drag & drop file upload with hidden Streamlit uploader
- `src/ui/style_loader.py`: CSS loading utility
- `src/ui/memory_status.py`: Memory monitoring component
- `src/ui/model_manager.py`: Model selection and management
- `src/memory_safe_embeddings.py`: Memory-efficient embeddings with caching

### Session State Management
Streamlit session state is initialized in `app.py` and `src/ui/components.py`:
- Messages, document IDs, notifications
- Model selection, settings
- Auto-saves important state changes

### Vector Store Persistence
- Single unified store saved in `vector_stores/unified_store.faiss`
- Metadata in `unified_store_metadata.json`
- All documents indexed in one store with source attribution
- Cleared and rebuilt on each startup for consistency

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

### CSS Structure
- Main CSS file: `assets/css/main.css`
- Loaded via `src/ui/style_loader.py`
- Minimal CSS approach - only essential styles
- No build process required

### CSS Components
The CSS file includes styles for:
- Typing indicators and animations
- Toast notifications
- Document list and pagination
- Drag & drop upload area
- Upload progress bars
- Status indicators
- Basic responsive behavior

### Adding Styles
1. Edit `assets/css/main.css` directly
2. Keep styles minimal and component-focused
3. Use CSS custom properties for theming
4. Follow existing naming conventions

## Document Management
The app uses a simple filesystem-based document management approach:
- Documents are placed in the `/documents` folder
- All documents are processed automatically on startup
- No UI-based upload/delete operations
- To change documents, add/remove files and restart the app
- This design works WITH Streamlit's nature, not against it

## Best Practices

### When Making Changes
1. Run `make run` to start the app
2. Make changes to code
3. Test with `make test` or specific test commands
4. Verify UI changes visually
5. Run `make test` before committing

### Common Pitfalls to Avoid
- Don't manually manage venv - use make commands
- Don't add inline CSS - use the main CSS file
- Don't skip tests - all must pass
- Don't use relative imports - use `from src.module`
- Don't hardcode ports - use config values

### Debugging Tips
- Check service status with `make monitor`
- Logs available in terminal output
- Use `--verbose` flag for detailed test output

### Common UI Issues
- **Duplicate drag & drop areas**: The custom drag & drop component hides the Streamlit file uploader using CSS
- **Console warnings**: Streamlit's browser feature detection warnings are harmless
- **CSS not updating**: Hard refresh the browser (Cmd+Shift+R or Ctrl+Shift+R)

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
```

Remember: This is a monorepo with integrated services. The Makefile is your primary interface for all operations.