# Greg: Your AI Playground - Complete Guide for M3 MacBook Air

**Greg is your local AI playground for experimentation and development. Currently featuring multi-document question-answering with unified vector storage for better cross-document queries. Built for M3 MacBook Air and Apple Silicon Macs, Greg uses Ollama and open-source LLMs to provide completely local, free AI assistance. Features a clean web UI, streaming responses, support for multiple AI models, and optimized performance for machines with 8-24GB RAM.**

## Why M3 MacBook Air is Perfect for This

1. **Unified Memory Architecture**: 8-24GB of fast unified memory shared between CPU/GPU
2. **Neural Engine**: 16-core Neural Engine accelerates ML tasks
3. **Efficiency**: Runs AI models with minimal power consumption
4. **Metal Performance Shaders**: Hardware acceleration for PyTorch

## Prerequisites

Before starting, ensure you have:

- macOS 11 Big Sur or later
- Python 3.9 or higher (`python3 --version`)
- At least 4GB of available RAM
- 10GB of free disk space (for models)
- Homebrew installed (optional but recommended)

To install Homebrew if you don't have it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Quick Start (5 Minutes)

### Complete Installation From Scratch

If you're starting fresh, here's the complete setup:

```bash
# 1. Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Ollama
brew install ollama

# 3. Clone or download this project
git clone <your-repo-url> pdf-rag-m3
cd pdf-rag-m3

# 4. Run the application
./run.sh
```

### Step-by-Step Installation

### Step 1: Install Ollama (One-Time Setup)

**Option 1: Install via Homebrew (Recommended)**

```bash
# Install Ollama
brew install ollama

# Start Ollama service
ollama serve

# In a new terminal, pull the recommended model
ollama pull mistral
```

**Option 2: Download from Ollama website**

1. Visit <https://ollama.com/download/mac>
2. Download and install Ollama.app
3. Drag to Applications folder and open
4. The app will install the `ollama` command line tool

Then pull the model:

```bash
ollama pull mistral
```

### Step 2: Set Up Python Environment

```bash
# Navigate to the project directory
cd /path/to/your/project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Run the Application

**Option 1: One-command startup (Recommended)**

```bash
./run.sh
```

This script will:

- Check if Ollama is installed
- Create a virtual environment if needed
- Install Python dependencies
- Start Ollama service
- Download the Mistral model if not present
- Start the API server
- Launch the Streamlit web interface

**Option 2: Manual startup**

```bash
# Terminal 1: Make sure Ollama is running
ollama serve

# Terminal 2: Start the API (activate venv first)
source venv/bin/activate
python main.py

# Terminal 3: Start the UI (activate venv first)
source venv/bin/activate
streamlit run app.py
```

That's it! Open <http://localhost:8501> and start uploading PDFs.

**Note**: The API runs on port 8080 by default. If you need to change it, update the port in both `main.py` and `app.py`.

## Available Models (All Free)

### For M3 with 8GB RAM

- **Phi (2.7B)** - Fastest, good for simple Q&A

  ```bash
  ollama pull phi
  ```

- **Mistral (7B)** - Best balance of speed and quality

  ```bash
  ollama pull mistral
  ```

### For M3 with 16GB RAM (Recommended for better accuracy)

- **Mistral (7B)** - Best balance, leaves RAM for other apps

  ```bash
  ollama pull mistral
  ```

- **Neural-Chat (7B)** - Intel-optimized, good for structured data

  ```bash
  ollama pull neural-chat
  ```

- **Llama 2 (7B)** - Alternative with good reasoning

  ```bash
  ollama pull llama2
  ```

- **Dolphin-Mistral (7B)** - Fine-tuned for following instructions

  ```bash
  ollama pull dolphin-mistral
  ```

### For M3 with 24GB+ RAM

- **Llama 2 (13B)** - Much better accuracy

  ```bash
  ollama pull llama2:13b
  ```

- **Mixtral (8x7B)** - State-of-the-art

  ```bash
  ollama pull mixtral
  ```

## Performance Expectations

### Processing Speed (M3 Base Model - 8GB)

| PDF Size  | Model   | Processing Time | Q&A Response Time |
| --------- | ------- | --------------- | ----------------- |
| 10 pages  | Phi     | 30-45 seconds   | 2-3 seconds       |
| 10 pages  | Mistral | 45-60 seconds   | 3-5 seconds       |
| 50 pages  | Phi     | 2-3 minutes     | 2-3 seconds       |
| 50 pages  | Mistral | 3-4 minutes     | 3-5 seconds       |
| 100 pages | Phi     | 5-7 minutes     | 3-4 seconds       |
| 100 pages | Mistral | 7-10 minutes    | 4-6 seconds       |

### Memory Usage

- **Idle**: ~500MB
- **PDF Processing**: 2-4GB
- **During Q&A**: 4-6GB (Mistral), 2-3GB (Phi)

## Optimizing for Your M3

### For 8GB Models (Base M3 Air)

Edit `.env`:

```bash
# Optimized for 8GB
LOCAL_LLM_MODEL=phi  # Smaller model
CHUNK_SIZE=500       # Smaller chunks
BATCH_SIZE=2         # Smaller batches
MAX_CONTEXT_LENGTH=1024
```

### For 16GB Models

Edit `.env`:

```bash
# Optimized for 16GB
LOCAL_LLM_MODEL=mistral
CHUNK_SIZE=1000
BATCH_SIZE=8
MAX_CONTEXT_LENGTH=4096
```

### For 24GB Models

Edit `.env`:

```bash
# Optimized for 24GB
LOCAL_LLM_MODEL=mixtral
CHUNK_SIZE=1500
BATCH_SIZE=16
MAX_CONTEXT_LENGTH=8192
```

## Tips for Best Performance

### 1. **Memory Management**

```bash
# Check available memory before processing large PDFs
# In Python:
import psutil
print(f"Available: {psutil.virtual_memory().available / (1024**3):.1f} GB")
```

### 2. **Model Preloading**

Keep Ollama running in the background:

```bash
# Add to ~/.zshrc for auto-start
alias ollama-start="ollama serve > /dev/null 2>&1 &"
```

### 3. **Batch Processing**

For multiple PDFs, process during low-usage times:

```python
# Process PDFs overnight
import schedule
schedule.every().day.at("22:00").do(process_pdfs)
```

### 4. **Use Activity Monitor**

- Monitor Memory Pressure
- Check if using Swap (should avoid)
- Ensure CPU isn't thermal throttling

## Common Issues & Solutions

### Issue: "Ollama not running"

```bash
# Solution: Start Ollama
ollama serve

# Or run in background
nohup ollama serve > ollama.log 2>&1 &
```

### Issue: "Model too slow"

```bash
# Switch to smaller model
ollama pull phi
# Update .env: LOCAL_LLM_MODEL=phi
```

### Issue: "Out of memory"

```bash
# 1. Use smaller model
# 2. Reduce batch size in .env
# 3. Close other applications
# 4. Process smaller PDFs
```

### Issue: "Import errors"

```bash
# Ensure correct Python version
python --version  # Should be 3.9+

# Reinstall with Apple Silicon support
pip uninstall torch
pip install torch torchvision torchaudio
```

### Issue: "Cannot connect to API server"

```bash
# Make sure the API is running
python main.py

# Or use the all-in-one script
./run.sh
```

### Issue: "Request timed out"

```bash
# Processing large PDFs can take time
# Try with a smaller PDF first
# Or increase timeout in app.py
```

## Advanced Optimizations

### 1. **GPU Acceleration**

The app automatically uses Metal Performance Shaders:

```python
# Verify MPS is available
import torch
print(torch.backends.mps.is_available())  # Should be True
```

### 2. **Parallel Processing**

```python
# In .env
NUM_THREADS=8  # M3 has 8 cores
```

### 3. **Custom Model Parameters**

```python
# For better quality (slower)
ollama run mistral --verbose \
  --parameter temperature 0.3 \
  --parameter top_p 0.9 \
  --parameter repeat_penalty 1.2
```

## Example Workflow

### 1. Research Papers

```bash
# Use mistral for academic content
LOCAL_LLM_MODEL=mistral
CHUNK_SIZE=1000  # Larger chunks for context

# Good questions:
"What methodology did the authors use?"
"What were the main findings?"
"What are the limitations of this study?"
```

### 2. Technical Documentation

```bash
# Use codellama for code-heavy docs
ollama pull codellama:7b
LOCAL_LLM_MODEL=codellama:7b

# Good questions:
"How do I configure the database?"
"Show me the API endpoints"
"What are the error codes?"
```

### 3. Books/Long Documents

```bash
# Use phi for speed on long docs
LOCAL_LLM_MODEL=phi
CHUNK_SIZE=800

# Good questions:
"Summarize chapter 3"
"What does the author say about X?"
"Find mentions of Y character"
```

## Cost Analysis

### Completely Free Stack

- **LLM**: Ollama + Open Source Models - $0
- **Embeddings**: Sentence Transformers - $0
- **Vector DB**: FAISS - $0
- **Framework**: LangChain - $0
- **API**: FastAPI - $0
- **UI**: Streamlit - $0
- **Total Monthly Cost**: $0

### Comparison to Cloud

- OpenAI API: ~$50-200/month
- AWS Deployment: ~$100-500/month
- Your M3 Setup: $0/month + electricity (~$2/month)

## Limitations

### Understanding the Technology

This system uses **Retrieval-Augmented Generation (RAG)**, which means:

1. Your PDF is split into small chunks (~2000 characters each)
2. When you ask a question, it searches for the 5 most relevant chunks
3. Only those 5 chunks are given to the AI to formulate an answer
4. The AI never sees your entire document at once

Think of it as having a very smart assistant who can only look at 5 pages at a time from your document.

### What This System CAN Do Well ✅

| Document Type | Size | Use Cases | Success Rate |
|--------------|------|-----------|--------------|
| **Invoices** | 1-20 pages | Find totals, dates, line items | 95% |
| **Reports/Papers** | 10-50 pages | Extract findings, methodologies, conclusions | 85% |
| **Technical Docs** | 20-100 pages | Find specific procedures, configurations | 75% |
| **Contracts** | 5-30 pages | Locate specific clauses, terms | 80% |
| **Presentations** | 10-50 slides | Find specific information, data points | 85% |

**Best for:**

- ✅ Finding specific information (numbers, dates, names)
- ✅ Answering focused questions about particular sections
- ✅ Extracting data from structured documents
- ✅ Quick lookups and fact-finding
- ✅ Processing multiple separate documents

### What This System CANNOT Do Well ❌

| Document Type | Why It Struggles | What Happens |
|--------------|------------------|--------------|
| **Books/Novels** | Can't maintain narrative context across chapters | Gets random fragments, loses plot |
| **Legal Documents** | Can't cross-reference between distant sections | Misses important related clauses |
| **Academic Textbooks** | Can't build cumulative understanding | Treats each chunk in isolation |
| **Complex Manuals** | Can't follow multi-step procedures across pages | Loses sequence of steps |
| **Financial Reports** | Can't aggregate data from multiple tables | Sees fragments, not full picture |

**Not suitable for:**

- ❌ Understanding narrative or story progression
- ❌ Comprehensive document summarization
- ❌ Cross-referencing between distant sections
- ❌ Questions requiring whole-document context
- ❌ Complex calculations across multiple data points

### Practical Examples

#### ✅ Good Questions

- "What is the invoice total?"
- "What methodology is described in section 3?"
- "What is the configuration for the database?"
- "When is the payment due date?"
- "What are the key findings on page 15?"

#### ❌ Poor Questions

- "Summarize this entire book"
- "How does the character develop throughout the story?"
- "What are all the financial implications across all sections?"
- "Create a comprehensive summary of all chapters"
- "How do all the concepts in this textbook relate to each other?"

### Technical Constraints

1. **Context Window**: Only 4-8K tokens (roughly 5-10 pages) can be processed at once
2. **Chunk Isolation**: Each chunk is evaluated independently
3. **No Memory**: The system doesn't remember previous questions
4. **Local Model Limits**: 7-8B parameter models have limited reasoning compared to GPT-4/Claude

### Workarounds for Better Results

1. **For Books/Long Documents:**
   - Split into chapters and upload separately
   - Ask specific, located questions ("What happens in chapter 3?")
   - Use as a "smart search" tool rather than a comprehension tool

2. **For Complex Analysis:**
   - Break down complex questions into simple, specific ones
   - Reference specific sections ("What does section 4.2 say about...")
   - Upload related documents separately

3. **For Better Accuracy:**
   - Use more specific models (Llama 3 for general, DeepSeek Coder for technical)
   - Increase chunk size in .env for documents with longer passages
   - Ask the same question differently to verify answers

### When to Use Alternative Solutions

Consider cloud-based solutions (ChatGPT, Claude) when you need to:

- Analyze entire books or very long documents
- Understand complex relationships across a document
- Generate comprehensive summaries
- Perform analysis requiring full document context

This local solution excels at privacy, cost (free), and specific information extraction, but has inherent limitations due to the chunking approach and local model constraints.

## Privacy & Security

### What Stays Local

- ✅ Your PDFs never leave your machine
- ✅ All processing happens on your M3
- ✅ No API keys needed
- ✅ No internet required after setup
- ✅ No usage tracking or telemetry

### Security Best Practices

```bash
# 1. Encrypt sensitive PDFs at rest
# 2. Use FileVault on macOS
# 3. Don't expose ports publicly
# 4. Regular backups of vector stores
```

## Benchmarks on M3

### Real-World Tests (M3 Base 8GB)

| Task        | Mistral 7B | Phi 2.7B | Time Saved |
| ----------- | ---------- | -------- | ---------- |
| Load Model  | 5-7s       | 2-3s     | 60% faster |
| 10-page PDF | 45s        | 30s      | 33% faster |
| Simple Q&A  | 3-4s       | 1-2s     | 50% faster |
| Complex Q&A | 5-7s       | 3-4s     | 40% faster |
| Memory Used | 5-6GB      | 2-3GB    | 50% less   |

## Testing

### Quick Start

```bash
# Run complete test suite (all except models)
make test

# Quick tests for development (no services needed)
make test-quick        # Unit + Streamlit tests only (~1 minute)

# Run specific test suites
make test-unit         # Unit tests (includes security tests)
make test-integration  # Integration tests
make test-streamlit    # Native Streamlit logic tests
make test-api          # API endpoint tests
make test-performance  # Performance optimization tests

# Visual regression testing
make test-screens           # Run visual regression tests
make test-screens-baseline  # Create baseline screenshots

# Model testing
make test-models-quick         # Quick test with current documents
make test-models MODELS="mistral"  # Test specific model
make test-models MODELS="mistral,llama3,deepseek-llm,deepseek-coder"  # Test all
```

### Test Categories

#### 1. **Unit Tests** (`make test-unit`)

- **Purpose**: Test individual functions and classes in isolation
- **Speed**: Very fast (< 30 seconds)
- **Coverage**: Document processing, streaming, utilities, security validations
- **When to run**: After every code change

#### 2. **Integration Tests** (`make test-integration`)

- **Purpose**: Test component interactions and workflows
- **Speed**: Moderate (1-3 minutes)
- **Coverage**: Full workflows, error scenarios, web search integration
- **When to run**: Before commits, after major changes

#### 3. **API Tests** (`make test-api`)

- **Purpose**: Test all FastAPI endpoints
- **Speed**: Fast (< 1 minute)
- **Coverage**: Upload, query, delete, health checks
- **When to run**: After API changes

#### 4. **Streamlit Tests** (`make test-streamlit`)

- **Purpose**: Test Streamlit app logic without browser
- **Speed**: Fast (< 30 seconds)
- **Coverage**: App state, component rendering, interactions
- **When to run**: After Streamlit code changes

#### 5. **Performance Tests** (`make test-performance`)

- **Purpose**: Test system performance and resource usage
- **Speed**: Moderate (2-3 minutes)
- **Coverage**: Load handling, memory usage, response times, caching
- **When to run**: Before releases, after optimization work

#### 6. **Visual Regression Tests** (`make test-screens`)

- **Purpose**: Catch visual UI changes across different viewports
- **Speed**: Moderate (2-3 minutes)
- **Coverage**: UI screenshots across desktop, laptop, tablet, mobile
- **When to run**: After UI changes, before releases

#### 7. **Model Tests** (`make test-models`)

- **Purpose**: Test how well models can differentiate between documents in unified store
- **Speed**: Slow (varies by models tested)
- **Coverage**: Document differentiation, cross-document queries, model accuracy
- **When to run**: When adding new models or changing processing logic
- **Isolated**: Uses separate test documents folder - doesn't interfere with your data

### Test Organization

```
tests/
├── unit/              # Fast, isolated unit tests
├── integration/       # Tests requiring multiple components
├── api/               # API endpoint tests
├── streamlit/         # Native Streamlit app tests
├── performance/       # Performance and optimization tests
├── visual_regression/ # Visual regression screenshot tests
├── fixtures/          # Test data files
└── utilities/         # Helper scripts
```

### Running Tests

#### During Development

```bash
# Quick tests during coding (recommended)
make test-quick

# Or run individual suites
make test-unit test-streamlit
```

#### Before Committing

```bash
# Run full test suite
make test

# If UI changes were made
make test-screens
```

#### Advanced Testing

```bash
# Run tests with verbose output
./venv/bin/python -m pytest tests/unit/ -vvs

# Run specific test file
./venv/bin/python -m pytest tests/unit/test_document_processing.py

# Run with coverage
./venv/bin/python tests/run_tests.py --coverage

# Run tests matching pattern
./venv/bin/python tests/run_tests.py --pattern "test_web_search"
```

### Model Testing in Detail

#### Available Models for Testing

The test suite **automatically detects all models** installed on your computer via Ollama.

**Popular Models to Install:**
```bash
# Models you might have or can install
mistral         # Best balance of speed and quality (4.1GB)
llama3          # Meta's latest model 8B (4.7GB)
llama2          # Meta's previous model 7B/13B/70B
deepseek-llm    # DeepSeek's language model 7B (4.0GB)
deepseek-coder  # DeepSeek's code-focused model 6.7B (3.8GB)
phi             # Microsoft's small model 2.7B (1.6GB)
phi3            # Microsoft's latest small model 3.8B (2.3GB)
codellama       # Meta's code-focused model 7B/13B/34B
gemma           # Google's small model 2B/7B
gemma2          # Google's latest model 9B/27B
qwen            # Alibaba's model 0.5B/1.8B/4B/7B/14B/72B
qwen2           # Alibaba's latest model 0.5B/1.5B/7B
neural-chat     # Intel's optimized model 7B
mixtral         # Mistral's MoE model 8x7B
dolphin-mistral # Fine-tuned Mistral
llava           # Vision-language model 7B/13B
vicuna          # Fine-tuned LLaMA 7B/13B
orca-mini       # Microsoft's small model 3B/7B/13B
```

To see what you have installed:
```bash
ollama list
```

#### Quick Model Test
```bash
# Test with whatever documents are currently in your app
make test-models-quick
```
This runs a quick differentiation test to see if the model can distinguish between your current documents.

#### Full Model Testing
```bash
# Test ALL models installed on your computer (automatic detection)
make test-models

# Or explicitly test all models
make test-models MODELS="all"

# Test specific models only
make test-models MODELS="mistral"

# Test multiple specific models
make test-models MODELS="mistral,llama3"

# Test whatever models you just downloaded
make test-models MODELS="phi,codellama,gemma,qwen,neural-chat"
```

#### How Model Tests Work

The model tests use a **unified document store** approach:
1. **Isolated Environment**: Creates a separate `test_documents/` folder (doesn't touch your data)
2. **Test Documents**: Copies test files (invoices, stories) in multiple formats (Excel, Markdown, Word)
3. **Preprocessing**: Creates a test vector store in `test_vector_stores/`
4. **Differentiation Testing**: Tests if models can:
   - Find information in specific documents
   - Not confuse similar content across documents
   - Answer cross-document comparison questions
   - Maintain accuracy with mixed document types

#### Test Questions Include
- "What is the invoice number in the Excel file?" (document-specific)
- "Which invoice has the highest total amount?" (cross-document comparison)
- "List all the invoice numbers from all documents." (aggregation)

#### Installing Additional Models
```bash
# Download more models for testing
ollama pull phi           # 2.7B - Very fast, good for quick tests
ollama pull codellama      # 7B - Great for technical documents
ollama pull gemma:2b       # 2B - Google's efficient model
ollama pull qwen:4b        # 4B - Good multilingual support
ollama pull neural-chat    # 7B - Intel-optimized

# Then test all of them automatically
make test-models  # Auto-detects and tests ALL installed models
```

#### Understanding Test Results
The tests measure:
- **Accuracy**: How often the model finds the correct information
- **Response Time**: How fast each model responds
- **Differentiation**: Whether the model retrieves from the correct document

Example output:
```
Model: mistral
  Accuracy: 81.8% (9/11 questions correct)
  Avg Response: 3.2s
  
Model: llama3
  Accuracy: 90.9% (10/11 questions correct)
  Avg Response: 4.1s
```

### Important Notes

1. **Services**: Some tests require running services. Use `make run` first or let tests start them automatically
2. **No browser tests**: We use native Streamlit tests instead of Selenium for reliability
3. **Model tests**: Require Ollama models to be downloaded first
4. **Test data**: Located in `tests/fixtures/`
5. **Visual tests**: Require Playwright (automatically installed when running)
6. **Isolated testing**: Model tests use separate folders and don't interfere with your documents

### Troubleshooting Tests

#### Import Errors

```bash
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Service Connection Errors

```bash
# Start services
make run

# Check what's running
make monitor
```

#### Debug Mode

```bash
# Run with full output
make test-unit PYTEST_ARGS="-vvs"

# Debug single test
./venv/bin/python -m pytest tests/unit/test_file.py::test_name -vvs --pdb
```

## Development & Styling

### CSS System

Greg uses a plain CSS approach for maintainable, minimal styling:

```bash
# CSS is loaded automatically when running the app
make run
```

### Working with Styles

- **CSS Source**: `assets/css/main.css` - Single CSS file
- **No compilation needed**: Direct CSS editing
- **Component styles**: All styles in one organized file
- **Minimal approach**: Only essential styles included

### Never use inline styles in Python - Use CSS classes instead

```python
# Good ✅
st.markdown('<div class="chat-message">Hello</div>', unsafe_allow_html=True)

# Bad ❌
st.markdown('<div style="color: red;">Hello</div>', unsafe_allow_html=True)
```

### Offline Mode Configuration

For completely offline operation without HuggingFace requests:

```bash
# Environment variables (automatically set)
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1

# Pre-download embedding models
make download-embeddings
```

## Next Steps

1. **Start Simple**: Use Phi for initial testing
2. **Run Tests**: Use `make test` to verify everything works
3. **Quick Model Test**: Run `make test-models-quick` to verify file format support
4. **Full Testing**: Run `make test-models` to compare all models
5. **Optimize**: Tune parameters based on test results
6. **Scale**: Add more models as needed

## Community Resources

- **Ollama Discord**: <https://discord.gg/ollama>
- **LangChain Community**: <https://github.com/langchain-ai/langchain>
- **Apple ML Forums**: <https://developer.apple.com/forums/tags/machine-learning>

## Troubleshooting Checklist

- [ ] Ollama installed and running?
- [ ] Python 3.9+ installed?
- [ ] Virtual environment activated?
- [ ] All dependencies installed?
- [ ] At least 4GB RAM available?
- [ ] Model downloaded?
- [ ] .env file configured?

## Success Metrics

You'll know it's working when:

- PDF uploads complete in < 5 minutes
- Questions answered in < 5 seconds
- Memory usage stays under 75%
- No fan noise during Q&A
- Accurate, relevant answers

Enjoy your free, private, and powerful PDF Q&A system! 🎉
