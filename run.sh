#!/bin/bash

# PDF Q&A System Launcher for M3 MacBook Air

# Add Homebrew to PATH for M1/M2/M3 Macs
export PATH="/opt/homebrew/bin:$PATH"

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
if [ -f "assets/scripts/build_sass.py" ]; then
    if [ ! -f "assets/styles/css/main.css" ]; then
        echo "🎨 Building CSS from SASS..."
        python assets/scripts/build_sass.py
    fi
    
    # Start SASS watcher in background
    echo "👀 Starting SASS watcher..."
    python assets/scripts/build_sass.py --watch > logs/sass-watch.log 2>&1 &
    SASS_PID=$!
fi

# Check if Ollama is running and find its port
OLLAMA_PORT=""
OLLAMA_PID=""

# First check default port
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    OLLAMA_PORT=11434
    echo "✅ Ollama is already running on default port 11434"
else
    # Check if Ollama process exists and find its port
    OLLAMA_PROCESS=$(ps aux | grep -E "ollama (serve|runner)" | grep -v grep | head -1)
    if [ -n "$OLLAMA_PROCESS" ]; then
        # Try to extract port from process
        POSSIBLE_PORT=$(echo "$OLLAMA_PROCESS" | grep -oE "\-\-port [0-9]+" | grep -oE "[0-9]+")
        if [ -n "$POSSIBLE_PORT" ]; then
            echo "⚠️  Found Ollama running on non-default port: $POSSIBLE_PORT"
            echo "The app expects Ollama on port 11434."
            read -p "Do you want to restart Ollama on the default port? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "🔄 Restarting Ollama on default port..."
                pkill -f "ollama" 2>/dev/null || true
                sleep 2
                ollama serve > logs/ollama.log 2>&1 &
                OLLAMA_PORT=11434
            else
                echo "❌ Cannot continue - app requires Ollama on port 11434"
                echo "Please either:"
                echo "  1. Stop the current Ollama and run this script again"
                echo "  2. Manually start Ollama with: ollama serve"
                exit 1
            fi
        else
            # Ollama process exists but can't find port
            echo "⚠️  Found Ollama process but cannot determine port"
            read -p "Do you want to restart Ollama? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                pkill -f "ollama" 2>/dev/null || true
                sleep 2
                ollama serve > logs/ollama.log 2>&1 &
                OLLAMA_PORT=11434
            else
                exit 1
            fi
        fi
    else
        # No Ollama running at all
        echo "🚀 Starting Ollama service..."
        ollama serve > logs/ollama.log 2>&1 &
        OLLAMA_PORT=11434
    fi
fi

# Wait for Ollama to be ready if we just started it
if [ "$OLLAMA_PORT" == "11434" ] && ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -n "⏳ Waiting for Ollama to start"
    for i in {1..15}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo " ✅"
            break
        fi
        echo -n "."
        sleep 1
    done
    echo
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
python src/utils/check_port.py 2402
PORT_STATUS=$?

if [ $PORT_STATUS -eq 0 ]; then
    echo "✅ Using preferred port 2402"
    STREAMLIT_PORT=2402
elif [ $PORT_STATUS -eq 1 ]; then
    # Port script found alternative
    STREAMLIT_PORT=$(python src/utils/check_port.py 2402 | tail -n 1 | grep -E '^[0-9]+$')
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