# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

### Starting the Application
- **Full startup (recommended)**: `make run` or `./run.sh`
- **Development mode**: Start each component in separate terminals:
  ```bash
  # Terminal 1: Ollama service
  ollama serve
  
  # Terminal 2: API server
  source venv/bin/activate && python main.py
  
  # Terminal 3: Web UI
  source venv/bin/activate && streamlit run app.py
  ```

### Common Commands
- **Install dependencies**: `make install`
- **Clean temporary files**: `make clean`
- **Monitor system resources**: `make monitor`
- **List available models**: `make models`
- **Test model compatibility**: `make test-models` or `python test_models.py --models deepseek`
- **Fix deepseek issues**: `python fix_deepseek.py`
- **Lint/typecheck**: No specific commands configured - ask user if needed

## Architecture Overview

ProbeLocal is a Retrieval-Augmented Generation (RAG) system with three main components:

1. **Ollama Service** (port 11434): Runs local LLMs (Mistral, Llama, Phi)
2. **FastAPI Backend** (port 8080): Handles PDF processing, vector storage, and Q&A logic
3. **Streamlit Frontend** (port 8501): Provides web UI for document upload and querying

### Key Modules
- `src/config.py`: Environment configuration and memory optimization
- `src/document_processor.py`: PDF chunking with LangChain
- `src/local_llm.py`: Ollama integration for LLM queries
- `src/qa_chain.py`: RAG pipeline with FAISS vector search
- `main.py`: FastAPI endpoints for document management
- `app.py`: Streamlit UI with session state management

### Data Flow
1. PDFs uploaded via Streamlit → FastAPI
2. FastAPI processes PDFs → chunks → embeddings → FAISS vector store
3. User queries → FAISS similarity search → context retrieval → Ollama LLM → response

### Memory Optimization
The system automatically adjusts chunk size, batch size, and context length based on available RAM (8GB/16GB/24GB+). Configuration is loaded from `.env` file.

## Important Implementation Details

### Session State Management
Streamlit requires proper session state initialization at the top of `app.py`:
```python
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'current_document_id' not in st.session_state:
    st.session_state.current_document_id = None
```

### Vector Store Persistence
- Vector stores saved in `vector_stores/{document_id}.faiss`
- Metadata stored alongside in `{document_id}_metadata.json`
- Stores persist across restarts but can be cleaned with `make clean`

### Error Handling
- Connection errors between services should show helpful messages
- Processing timeouts set to 300s for large PDFs
- Memory monitoring prevents OOM errors

### Apple Silicon Optimization
- Uses Metal Performance Shaders via PyTorch
- CPU thread count optimized for efficiency cores
- Unified memory architecture leveraged for large models

## Model Compatibility

### Known Issues
- **Deepseek**: Requires minimal parameters (only `num_ctx`) to avoid 422 errors
- Some models don't support `num_thread`, `repeat_penalty`, or custom `stop` tokens

### Testing Models

#### Comprehensive PDF Testing (Recommended)
Run `make test-models` to test all models with actual PDF Q&A:
- Uploads a test PDF invoice
- Tests 10 different questions per model
- Measures accuracy, response time, and error rates
- Identifies 422 errors and other issues
- Results saved to `tests/results/`

```bash
# Test all models
make test-models

# Test specific models
python tests/test_all_models.py --models deepseek mistral

# Test with custom PDF
python tests/test_all_models.py --pdf /path/to/your.pdf
```

#### Quick Parameter Testing
Run `make test-models-quick` for rapid parameter compatibility testing:
- Tests different parameter combinations
- Generates `src/model_config.json`
- No PDF processing required

### Quick Fixes
- For deepseek 422 error: Run `python tests/unit/fix_deepseek.py`
- Model config stored in `src/model_config.json`
- Model-specific parameters are automatically loaded