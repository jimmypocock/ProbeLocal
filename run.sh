#!/bin/bash

# PDF Q&A System Launcher for M3 MacBook Air

# Add Homebrew to PATH for M1/M2/M3 Macs
export PATH="/opt/homebrew/bin:$PATH"

echo "🍎 Starting PDF Q&A System..."
echo "================================"

# Function to cleanup on exit
cleanup() {
    # Only show cleanup message if we haven't already started cleaning up
    if [ -z "$CLEANING_UP" ]; then
        CLEANING_UP=1
        echo -e "\n🧹 Cleaning up..."
        
        # Unload the model to free memory
        echo "📦 Unloading $MODEL_TO_LOAD from memory..."
        ollama run ${MODEL_TO_LOAD:-mistral} "" --keepalive 0 > /dev/null 2>&1 || true
        
        # Kill API server
        if [ -n "$API_PID" ] && kill -0 $API_PID 2>/dev/null; then
            kill -TERM $API_PID 2>/dev/null
            # Give it a moment to shut down gracefully
            wait $API_PID 2>/dev/null
        fi
        
        echo "✅ Shutdown complete"
    fi
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

# CSS is now static - no build needed

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

# Load environment variables to get the configured model
if [ -f .env ]; then
    # Parse .env file more carefully to handle comments and spaces
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ ! "$key" =~ ^[[:space:]]*# ]] && [[ -n "$key" ]]; then
            # Remove leading/trailing whitespace
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            # Remove inline comments
            value=${value%%#*}
            # Trim again after removing comments
            value=$(echo "$value" | xargs)
            # Export if valid
            if [[ -n "$key" ]] && [[ -n "$value" ]]; then
                export "$key=$value"
            fi
        fi
    done < .env
fi

# Use configured model or default to mistral
MODEL_TO_LOAD=${LOCAL_LLM_MODEL:-mistral}

# Check if model is available
if ! ollama list | grep -q "$MODEL_TO_LOAD"; then
    echo "📥 Downloading $MODEL_TO_LOAD model (this may take a few minutes)..."
    ollama pull $MODEL_TO_LOAD
fi

# Pre-load the model to avoid cold start on first query
echo "🔥 Pre-loading $MODEL_TO_LOAD model into memory..."
ollama run $MODEL_TO_LOAD "Hello" --keepalive 24h > /dev/null 2>&1 &
echo "✅ Model $MODEL_TO_LOAD loaded and will stay in memory while app runs"

# Clear vector stores BEFORE starting API
echo "🗑️  Clearing vector stores..."
rm -rf vector_stores/* 2>/dev/null || true
echo "✅ Vector stores cleared"

# Check if port 8080 is in use
if lsof -ti:8080 > /dev/null 2>&1; then
    echo "⚠️  Port 8080 is already in use by another process."
    echo "This could be:"
    echo "  - A previous instance of this app that didn't shut down cleanly"
    echo "  - Another application using port 8080"
    echo ""
    read -p "Do you want to kill the process and continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🧹 Killing process on port 8080..."
        lsof -ti:8080 | xargs kill -9 2>/dev/null || true
        sleep 2
        API_PORT=8080
    else
        echo "🔄 Finding alternative port..."
        # Find next available port starting from 8081
        API_PORT=8081
        while lsof -ti:$API_PORT > /dev/null 2>&1; do
            API_PORT=$((API_PORT + 1))
            if [ $API_PORT -gt 8090 ]; then
                echo "❌ Could not find available port between 8081-8090"
                exit 1
            fi
        done
        echo "✅ Using port $API_PORT instead"
        # Update the port in main.py temporarily for this run
        export GREG_API_PORT=$API_PORT
    fi
else
    API_PORT=8080
fi

# Start the API server
echo "🔧 Starting API server on port $API_PORT..."
# Use exec to replace the shell process, making signal handling cleaner
python -u main.py &
API_PID=$!

# Wait for API to be ready before preprocessing
echo "⏳ Waiting for API to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:$API_PORT/health > /dev/null 2>&1; then
        echo "✅ API is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API failed to start. Check logs/api.log for details."
        exit 1
    fi
    sleep 1
done

# Preprocess documents
echo ""
echo "📚 Preprocessing documents..."
echo "================================"
python scripts/preprocess_documents.py
echo ""


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

# Run streamlit in foreground so script exits cleanly when streamlit stops
if [ -n "$STREAMLIT_PORT" ]; then
    exec streamlit run app.py --server.port $STREAMLIT_PORT
else
    exec streamlit run app.py
fi