#!/bin/bash

# PDF Q&A System Launcher for M3 MacBook Air

echo "🍎 Starting PDF Q&A System..."
echo "================================"

# Function to cleanup on exit
cleanup() {
    echo -e "\n🧹 Cleaning up..."
    if [ -n "$API_PID" ]; then
        kill $API_PID 2>/dev/null
    fi
    if [ -n "$SASS_PID" ]; then
        kill $SASS_PID 2>/dev/null
    fi
    echo "✅ Shutdown complete"
    exit 0
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed. Please install it using one of these methods:"
    echo ""
    echo "Option 1: Install via Homebrew (recommended):"
    echo "  brew install ollama"
    echo ""
    echo "Option 2: Download from website:"
    echo "  https://ollama.com/download/mac"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Set offline mode for HuggingFace to prevent HTTP 429 errors
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1

# Install dependencies if needed
if ! python -c "import langchain" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Build CSS if needed or start SASS watcher
if [ -f "scripts/build_sass.py" ]; then
    if [ ! -f "static/css/main.css" ]; then
        echo "🎨 Building CSS from SASS..."
        python scripts/build_sass.py
    fi
    
    # Start SASS watcher in background
    echo "👀 Starting SASS watcher..."
    python scripts/build_sass.py --watch > sass-watch.log 2>&1 &
    SASS_PID=$!
fi

# Start Ollama in background if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "🚀 Starting Ollama service..."
    ollama serve > ollama.log 2>&1 &
    sleep 3
fi

# Check if model is available
if ! ollama list | grep -q "mistral"; then
    echo "📥 Downloading Mistral model (this may take a few minutes)..."
    ollama pull mistral
fi

# Start the API server
echo "🔧 Starting API server..."
python main.py &
API_PID=$!

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
sleep 5

# Check port availability
echo "🔍 Checking port availability..."
python check_port.py 2402
PORT_STATUS=$?

if [ $PORT_STATUS -eq 0 ]; then
    echo "✅ Using preferred port 2402"
    STREAMLIT_PORT=2402
elif [ $PORT_STATUS -eq 1 ]; then
    # Port script found alternative
    STREAMLIT_PORT=$(python check_port.py 2402 | tail -n 1 | grep -E '^[0-9]+$')
    echo "⚠️  Using alternative port $STREAMLIT_PORT"
else
    echo "💡 Using system-assigned port"
    STREAMLIT_PORT=""
fi

# Start Streamlit
echo "🎨 Starting web interface..."
if [ -n "$STREAMLIT_PORT" ]; then
    streamlit run app.py --server.port $STREAMLIT_PORT
else
    streamlit run app.py
fi