# Greg AI Assistant Documentation

## Overview

Greg is an **AI playground** designed for experimenting with various AI capabilities. It's built to be:

- 🏠 **Local** - All processing happens on your machine
- 🔒 **Private** - Your data never leaves your computer
- 💰 **Free** - No API keys or subscriptions required
- 🚀 **Fast** - Optimized for Apple Silicon

## Features

### Current Capabilities

1. **Multi-format Document Processing**
   - PDF files
   - Text files (.txt)
   - CSV files
   - Markdown files (.md)
   - Word documents (.docx)

2. **Question Answering**
   - Natural language queries
   - Context-aware responses
   - Source citations

3. **Local LLM Integration**
   - Supports multiple models via Ollama
   - Model switching on the fly
   - Optimized for different memory configurations

## Technical Architecture

```
Greg System Architecture
├── Frontend (Streamlit)
│   ├── File Upload Interface
│   ├── Question Input
│   └── Response Display
├── Backend (FastAPI)
│   ├── Document Processing
│   ├── Vector Storage (FAISS)
│   └── Query Processing
└── AI Models (Ollama)
    ├── Mistral
    ├── Llama
    └── Phi
```

## Installation Guide

### Prerequisites

- macOS 11+ (optimized for M3)
- Python 3.9+
- 8GB+ RAM recommended

### Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd Greg

# Install dependencies
make install

# Run Greg
make run
```

## Usage Examples

### Basic Q&A

**Question**: "What is Greg designed for?"  
**Answer**: Greg is an AI playground for experimenting with various AI capabilities locally.

### Technical Queries

**Question**: "What models does Greg support?"  
**Answer**: Greg supports Mistral, Llama, and Phi models via Ollama integration.

## Configuration

Greg can be configured via environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOCAL_LLM_MODEL` | Default model to use | mistral |
| `CHUNK_SIZE` | Document chunk size | 1000 |
| `MAX_CONTEXT_LENGTH` | Maximum context window | 4096 |

## Future Roadmap

- [ ] Image processing with OCR
- [ ] Audio transcription
- [ ] Code analysis features
- [ ] Multi-language support
- [ ] Cloud model integration

## Contributing

Greg is open source and welcomes contributions! Please see our contributing guidelines.

## License

Greg is released under the MIT License. See LICENSE file for details.

---

*Last updated: January 2025*  
*Version: 1.1.0*