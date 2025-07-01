import streamlit as st
import requests
import json
import subprocess
import psutil
import time
from typing import Dict, Any, Optional, List

# Check system resources
def get_system_info():
    memory = psutil.virtual_memory()
    return {
        "total_memory_gb": memory.total / (1024**3),
        "available_memory_gb": memory.available / (1024**3),
        "memory_percent": memory.percent
    }

# Check if Ollama is running
def check_ollama():
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

# Get document info
def get_document_info(doc_id: str) -> Optional[Dict]:
    """Get information about a specific document"""
    try:
        response = requests.get("http://localhost:8080/documents", timeout=2)
        if response.status_code == 200:
            docs = response.json().get('documents', [])
            for doc in docs:
                if doc['document_id'] == doc_id:
                    return doc
    except:
        pass
    return None

# Get model info
def get_model_info(models_data: Dict, model_name: str) -> Dict:
    """Get information about a specific model"""
    for model in models_data.get('models', []):
        if model['name'] == model_name:
            size_gb = model.get('size', 0) / (1024**3)
            # Determine model speed/quality characteristics
            if 'phi' in model_name.lower():
                speed = "⚡ Fast"
                quality = "Good"
            elif 'mistral' in model_name.lower():
                speed = "💨 Balanced" 
                quality = "Excellent"
            elif 'deepseek' in model_name.lower():
                speed = "🚀 Fast"
                quality = "Very Good"
            elif 'llama' in model_name.lower():
                speed = "⚖️ Moderate"
                quality = "Excellent"
            else:
                speed = "🔄 Variable"
                quality = "Good"
            
            return {
                'size': f"{size_gb:.1f}GB",
                'speed': speed,
                'quality': quality
            }
    return {'size': 'Unknown', 'speed': 'Unknown', 'quality': 'Unknown'}

st.set_page_config(
    page_title="ProbeLocal - PDF Q&A",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state variables
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'current_document_id' not in st.session_state:
    st.session_state.current_document_id = None
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = None
if 'current_model' not in st.session_state:
    st.session_state.current_model = None
if 'document_info' not in st.session_state:
    st.session_state.document_info = {}

st.title("🔍 ProbeLocal - PDF Question Answering")
st.markdown("100% Free, Local, and Private!")

# System status sidebar
with st.sidebar:
    st.header("⚙️ System Status")

    system_info = get_system_info()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Memory", f"{system_info['available_memory_gb']:.1f}GB")
    with col2:
        st.metric("Usage", f"{system_info['memory_percent']:.0f}%")
    st.progress(1 - system_info['memory_percent'] / 100)

    ollama_status = check_ollama()
    if ollama_status:
        st.success("✅ Ollama is running")
    else:
        st.error("❌ Ollama not running")
        st.code("ollama serve", language="bash")
        st.stop()

    st.markdown("---")
    
    # Document Management Section (moved up)
    st.header("📚 Documents")
    
    # Show current document status
    if st.session_state.current_document_id:
        doc_info = get_document_info(st.session_state.current_document_id)
        if doc_info:
            st.success(f"📖 Active: {doc_info['filename'][:25]}...")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"Pages: {doc_info.get('pages', 'N/A')}")
            with col2:
                st.caption(f"Chunks: {doc_info.get('chunks', 'N/A')}")
            with col3:
                st.caption("Status: ✅ Ready")
            st.session_state.document_info = doc_info
    else:
        st.warning("⚠️ No document selected")
        st.caption("Upload a PDF or select from below")
    
    # File upload
    uploaded_file = st.file_uploader("Upload New PDF", type="pdf", key="pdf_uploader")
    
    if uploaded_file is not None:
        # Disable button while processing
        if st.button("📤 Upload & Process", disabled=st.session_state.is_processing, type="primary", use_container_width=True):
            st.session_state.is_processing = True
            
            # Create a placeholder for status messages
            status_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            with status_placeholder.container():
                st.info(f"📋 Processing {uploaded_file.name}...")
            
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            data = {"model": st.session_state.current_model or "mistral"}
            
            try:
                progress_bar.progress(25)
                response = requests.post("http://localhost:8080/upload", files=files, data=data, timeout=300)
                progress_bar.progress(90)
            except requests.exceptions.ConnectionError:
                st.session_state.is_processing = False
                progress_bar.empty()
                status_placeholder.empty()
                st.error("❌ Cannot connect to API server")
                st.stop()
            except Exception as e:
                st.session_state.is_processing = False
                progress_bar.empty()
                status_placeholder.empty()
                st.error(f"❌ Error: {str(e)}")
                st.stop()

            progress_bar.progress(100)
            
            if response.status_code == 200:
                result = response.json()
                st.session_state.current_document_id = result['document_id']
                
                # Clear progress and status
                progress_bar.empty()
                status_placeholder.empty()
                
                # Show success messages
                st.success(f"✅ Processed in {result.get('processing_time', 0):.1f}s")
                
                # Reset processing state
                st.session_state.is_processing = False
                
                # Force a rerun to update the UI
                st.rerun()
            else:
                st.session_state.is_processing = False
                progress_bar.empty()
                status_placeholder.empty()
                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
    
    # List available documents
    try:
        response = requests.get("http://localhost:8080/documents", timeout=2)
        if response.status_code == 200:
            docs = response.json().get('documents', [])
            if docs:
                st.caption(f"Available Documents ({len(docs)})")
                for doc in docs[-10:]:  # Show last 10 documents
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        # Highlight if this is the current document
                        is_current = doc['document_id'] == st.session_state.current_document_id
                        button_label = f"{'✅' if is_current else '📄'} {doc['filename'][:20]}..."
                        
                        if st.button(
                            button_label, 
                            key=doc['document_id'], 
                            type="primary" if is_current else "secondary",
                            use_container_width=True,
                            disabled=is_current
                        ):
                            st.session_state.current_document_id = doc['document_id']
                            st.session_state.messages = []  # Clear chat when switching
                            st.session_state.document_info = doc
                            st.rerun()
                    with col2:
                        if st.button("🗑️", key=f"del_{doc['document_id']}", help=f"Delete {doc['filename']}"):
                            try:
                                del_response = requests.delete(f"http://localhost:8080/documents/{doc['document_id']}")
                                if del_response.status_code == 200:
                                    if st.session_state.current_document_id == doc['document_id']:
                                        st.session_state.current_document_id = None
                                        st.session_state.messages = []
                                        st.session_state.document_info = {}
                                    st.rerun()
                            except:
                                st.error("Failed to delete")
            else:
                st.info("No documents uploaded yet")
    except:
        st.info("Connecting to server...")
    
    st.markdown("---")
    
    # Model Selection Section
    st.header("🤖 AI Model")
    
    # Get available models from Ollama
    available_models = []
    models_data = {}
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
    except:
        available_models = ["mistral"]  # Fallback
    
    # Initialize selected model in session state
    if not st.session_state.current_model and available_models:
        st.session_state.current_model = available_models[0]
    
    # Model selection with instant switching
    selected_model = st.selectbox(
        "Select Model",
        available_models,
        index=available_models.index(st.session_state.current_model) if st.session_state.current_model in available_models else 0,
        help="Switch between different AI models instantly"
    )
    
    # Instant model switching without clearing chat
    if selected_model != st.session_state.current_model:
        st.session_state.current_model = selected_model
        st.info(f"🔄 Switched to {selected_model}")
        time.sleep(0.5)
        st.rerun()
    
    # Show model info
    if st.session_state.current_model and models_data:
        model_info = get_model_info(models_data, st.session_state.current_model)
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"Size: {model_info['size']}")
            st.caption(f"Speed: {model_info['speed']}")
        with col2:
            st.caption(f"Quality: {model_info['quality']}")
            st.caption("Status: 🟢 Ready")

    st.markdown("---")
    
    # Performance tips
    with st.expander("💡 Tips", expanded=False):
        st.markdown("""
        **Model Selection:**
        - **Mistral**: Best overall balance
        - **Phi**: Fastest responses
        - **DeepSeek**: Good for technical content
        - **Llama3**: Excellent comprehension
        
        **Performance:**
        - First question loads the model
        - Subsequent questions are faster
        - Smaller PDFs process quicker
        """)

# Main area
# Clear ready state indicator
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    if st.session_state.current_document_id and st.session_state.current_model:
        doc_name = st.session_state.document_info.get('filename', 'Document')
        st.success(f"🚀 Ready! Asking questions about: **{doc_name}**")
    else:
        missing = []
        if not st.session_state.current_document_id:
            missing.append("document")
        if not st.session_state.current_model:
            missing.append("model")
        st.info(f"📋 Please select a {' and '.join(missing)} to get started")

with col2:
    if st.session_state.current_document_id:
        if st.button("🔄 Clear Chat", type="secondary"):
            st.session_state.messages = []
            st.rerun()

with col3:
    if st.session_state.current_document_id and st.session_state.document_info:
        # Context usage indicator
        chunks = st.session_state.document_info.get('chunks', 0)
        # Estimate based on typical context window
        max_context = 4096
        estimated_usage = min(chunks * 100, max_context)  # Rough estimate
        usage_percent = (estimated_usage / max_context) * 100
        st.metric("Context", f"{usage_percent:.0f}%", help=f"Using ~{chunks} chunks from document")

# Chat interface
if st.session_state.current_document_id:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show context info for assistant messages
            if message["role"] == "assistant" and "context_info" in message:
                with st.expander("📊 Response Details", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.caption(f"Model: {message['context_info'].get('model', 'N/A')}")
                    with col2:
                        st.caption(f"Time: {message['context_info'].get('response_time', 0):.1f}s")
                    with col3:
                        st.caption(f"Sources: {message['context_info'].get('sources_count', 0)}")

    # Query input
    if prompt := st.chat_input("Ask about your PDF..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get response
        with st.chat_message("assistant"):
            with st.spinner(f"Thinking with {st.session_state.current_model}..."):
                start_time = time.time()
                
                # Make API call
                try:
                    response = requests.post(
                        "http://localhost:8080/ask",
                        json={
                            "question": prompt,
                            "document_id": st.session_state.current_document_id,
                            "max_results": 5,
                            "model_name": st.session_state.current_model
                        },
                        timeout=60
                    )
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to API server")
                    response = None
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out. Try a simpler question.")
                    response = None
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    response = None

                if response and response.status_code == 200:
                    result = response.json()
                    response_time = time.time() - start_time
                    
                    # Display answer
                    st.markdown(result['answer'])
                    
                    # Context info for the message
                    context_info = {
                        'model': st.session_state.current_model,
                        'response_time': response_time,
                        'sources_count': len(result.get('sources', []))
                    }
                    
                    # Show sources in expander
                    if result.get('sources'):
                        with st.expander(f"📍 Sources ({len(result['sources'])} chunks used)"):
                            for i, source in enumerate(result['sources'], 1):
                                st.caption(f"**Chunk {i}** (Page {source.get('page', 'N/A')})")
                                st.text(source.get('content', '')[:200] + "...")

                    # Add assistant message with context info
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result['answer'],
                        "context_info": context_info
                    })
                else:
                    error_msg = "Failed to get response. Please try again."
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
else:
    # No document selected - show helpful message
    st.markdown("### 💬 Ask Questions")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("👈 Please select or upload a document from the sidebar to start asking questions")
    
    # Check if there are any documents available
    try:
        response = requests.get("http://localhost:8080/documents", timeout=2)
        if response.status_code == 200:
            docs = response.json().get('documents', [])
            if docs:
                st.markdown("### 📚 Recent Documents")
                for doc in docs[-3:]:
                    if st.button(f"📄 {doc['filename']}", key=f"main_{doc['document_id']}", use_container_width=True):
                        st.session_state.current_document_id = doc['document_id']
                        st.session_state.document_info = doc
                        st.rerun()
    except:
        pass