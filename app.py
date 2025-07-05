import streamlit as st
import requests
import json
import subprocess
import psutil
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Configure page with better defaults
st.set_page_config(
    page_title="Greg - AI Playground",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
            # Determine model characteristics
            if 'phi' in model_name.lower():
                speed = "⚡ Lightning Fast"
                quality = "Good for simple tasks"
            elif 'mistral' in model_name.lower():
                speed = "🚀 Fast" 
                quality = "Excellent all-around"
            elif 'deepseek' in model_name.lower():
                speed = "💨 Very Fast"
                quality = "Great for technical content"
            elif 'llama' in model_name.lower():
                speed = "⚖️ Balanced"
                quality = "Best comprehension"
            else:
                speed = "🔄 Variable"
                quality = "Good general use"
            
            return {
                'size': f"{size_gb:.1f}GB",
                'speed': speed,
                'quality': quality
            }
    return {'size': 'Unknown', 'speed': 'Unknown', 'quality': 'Unknown'}

# Initialize session state with better defaults
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'current_document_id' not in st.session_state:
    st.session_state.current_document_id = None
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = None
if 'current_model' not in st.session_state:
    st.session_state.current_model = None
if 'document_info' not in st.session_state:
    st.session_state.document_info = {}
if 'notifications' not in st.session_state:
    st.session_state.notifications = []
if 'document_search' not in st.session_state:
    st.session_state.document_search = ""
if 'chunk_size' not in st.session_state:
    st.session_state.chunk_size = 800
if 'temperature' not in st.session_state:
    st.session_state.temperature = 0.7
if 'max_results' not in st.session_state:
    st.session_state.max_results = 5
if 'show_advanced' not in st.session_state:
    st.session_state.show_advanced = False
if 'delete_confirmed' not in st.session_state:
    st.session_state.delete_confirmed = None

# Notification system
def add_notification(message: str, type: str = "info", duration: int = 5):
    """Add a notification that persists for a specified duration"""
    st.session_state.notifications.append({
        "message": message,
        "type": type,
        "timestamp": datetime.now(),
        "duration": duration
    })

def show_notifications():
    """Display active notifications"""
    current_time = datetime.now()
    active_notifications = []
    
    for notif in st.session_state.notifications:
        if current_time - notif["timestamp"] < timedelta(seconds=notif["duration"]):
            active_notifications.append(notif)
    
    st.session_state.notifications = active_notifications
    
    for notif in active_notifications:
        if notif["type"] == "success":
            st.success(notif["message"])
        elif notif["type"] == "error":
            st.error(notif["message"])
        elif notif["type"] == "warning":
            st.warning(notif["message"])
        else:
            st.info(notif["message"])

# Header with better visual hierarchy
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title("🤖 Greg - AI Playground")
    st.caption("Your Local AI Assistant - 100% Free and Private")

with col2:
    # Quick status indicators
    ollama_status = check_ollama()
    if ollama_status:
        st.success("✅ System Ready")
    else:
        st.error("❌ Ollama Offline")

with col3:
    # Help button
    with st.popover("❓ Help"):
        st.markdown("""
        **Quick Start:**
        1. Upload a document (PDF, TXT, etc.)
        2. Select an AI model
        3. Ask questions!
        
        **Tips:**
        - Drag & drop files to upload
        - Use @ to reference documents
        - Try example questions
        """)

# Main chat area
with st.container():
    # Model selection in main area for better visibility
    col1, col2 = st.columns([2, 1])
    with col1:
        st.header("💬 Chat")
    with col2:
        # Model selector
        available_models = []
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models_data = response.json()
                available_models = [model['name'] for model in models_data.get('models', [])]
        except:
            available_models = ["mistral"]
        
        if available_models:
            selected_model = st.selectbox(
                "AI Model",
                available_models,
                index=available_models.index(st.session_state.current_model) if st.session_state.current_model in available_models else 0,
                key="model_selector"
            )
            
            if selected_model != st.session_state.current_model:
                st.session_state.current_model = selected_model
                add_notification(f"🔄 Switched to {selected_model}", "info", 3)
    
    # Show notifications
    show_notifications()
    
    # Chat interface
    if st.session_state.current_document_id:
        # Example questions
        if not st.session_state.messages:
            st.info("💡 **Try these questions:**")
            example_questions = [
                "What is this document about?",
                "Summarize the key points",
                "What are the main findings?",
                "Extract all important dates"
            ]
            cols = st.columns(2)
            for i, question in enumerate(example_questions):
                with cols[i % 2]:
                    if st.button(f"📝 {question}", key=f"example_{i}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": question})
                        st.rerun()
        
        # Display chat messages with better formatting
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Add copy button for assistant messages
                if message["role"] == "assistant":
                    if st.button("📋 Copy", key=f"copy_{len(st.session_state.messages)}"):
                        st.write("Copied to clipboard!")  # Note: Real clipboard functionality requires JavaScript
        
        # Chat input with better placeholder
        doc_name = st.session_state.document_info.get('filename', 'the document')
        if prompt := st.chat_input(f"Ask about {doc_name}..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Get response with typing indicator
            with st.chat_message("assistant"):
                with st.spinner(f"🤔 {st.session_state.current_model} is thinking..."):
                    start_time = time.time()
                    
                    try:
                        response = requests.post(
                            "http://localhost:8080/ask",
                            json={
                                "question": prompt,
                                "document_id": st.session_state.current_document_id,
                                "max_results": st.session_state.max_results,
                                "model_name": st.session_state.current_model,
                                "temperature": st.session_state.temperature
                            },
                            timeout=60
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            response_time = time.time() - start_time
                            
                            # Display answer with sources inline
                            st.markdown(result['answer'])
                            
                            if result.get('sources'):
                                st.caption(f"📍 Based on {len(result['sources'])} sources • {response_time:.1f}s")
                            
                            # Add to messages
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": result['answer']
                            })
                        else:
                            error_msg = f"❌ Error: {response.json().get('detail', 'Failed to get response')}"
                            st.error(error_msg)
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": error_msg
                            })
                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
            
            st.rerun()
    else:
        # Welcome message
        st.markdown("### 👋 Welcome to Greg!")
        st.info("""
        **Getting Started:**
        1. Upload a document on the left
        2. Select an AI model above
        3. Start asking questions!
        
        **Supported formats:** PDF, TXT, CSV, Markdown, Word, Excel, Images
        """)

# Process any pending deletions
if st.session_state.delete_confirmed:
    doc_id = st.session_state.delete_confirmed
    doc_name = st.session_state.get('delete_doc_name', 'document')
    
    # Perform the deletion
    try:
        response = requests.delete(
            f"http://localhost:8080/documents/{doc_id}", 
            timeout=10
        )
        if response.status_code == 200:
            # Clear state if this was the current document
            if st.session_state.current_document_id == doc_id:
                st.session_state.current_document_id = None
                st.session_state.messages = []
            add_notification(f"✅ Deleted {doc_name}", "success")
        else:
            add_notification(f"❌ Failed to delete {doc_name}", "error")
    except Exception as e:
        add_notification(f"❌ Error: {str(e)}", "error")
    
    # Clear the deletion state
    st.session_state.delete_confirmed = None
    st.session_state.delete_doc_name = None
    st.rerun()

# Sidebar with document management and settings
with st.sidebar:
    # Document Management Section
    st.header("📚 Documents")
    
    # Current document status
    if st.session_state.current_document_id:
        doc_info = get_document_info(st.session_state.current_document_id)
        if doc_info:
            st.success(f"📖 Active: {doc_info['filename'][:25]}...")
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"Chunks: {doc_info.get('chunks', 'N/A')}")
            with col2:
                st.caption(f"Pages: {doc_info.get('pages', 'N/A')}")
    else:
        st.info("📋 No document selected")
    
    # Upload area with improved progress
    uploaded_file = st.file_uploader(
        "Upload Document", 
        type=["pdf", "txt", "csv", "md", "docx", "xlsx", "png", "jpg", "jpeg"],
        help="Supported: PDF, TXT, CSV, Markdown, Word, Excel, Images"
    )
    
    if uploaded_file:
        if st.button("📤 Upload & Process", type="primary", use_container_width=True):
            # Progress indicators
            progress_text = st.empty()
            progress_bar = st.progress(0)
            
            # Smooth progress animation
            for i in range(0, 60, 5):
                progress_text.text(f"Uploading... {i}%")
                progress_bar.progress(i / 100)
                time.sleep(0.05)
            
            # Upload
            files = {"file": (uploaded_file.name, uploaded_file, "application/octet-stream")}
            data = {
                "model": st.session_state.current_model or "mistral",
                "chunk_size": st.session_state.chunk_size,
                "temperature": st.session_state.temperature
            }
            
            try:
                response = requests.post("http://localhost:8080/upload", files=files, data=data, timeout=300)
                
                # Complete progress
                for i in range(60, 101, 2):
                    progress_text.text(f"Processing... {i}%")
                    progress_bar.progress(i / 100)
                    time.sleep(0.02)
                
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.current_document_id = result['document_id']
                    add_notification(f"✅ Uploaded {uploaded_file.name} successfully!", "success")
                    progress_text.empty()
                    progress_bar.empty()
                    st.rerun()
                else:
                    add_notification(f"❌ Upload failed: {response.json().get('detail', 'Unknown error')}", "error")
                    progress_text.empty()
                    progress_bar.empty()
            except Exception as e:
                add_notification(f"❌ Error: {str(e)}", "error")
                progress_text.empty()
                progress_bar.empty()
    
    # Document search
    st.markdown("---")
    search_query = st.text_input("🔍 Search documents", placeholder="Type to filter...")
    
    # Document list - simplified without confirmation dialog
    try:
        response = requests.get("http://localhost:8080/documents", timeout=5)
        if response.status_code == 200:
            all_docs = response.json().get('documents', [])
            
            # Filter documents
            if search_query:
                docs = [doc for doc in all_docs if search_query.lower() in doc['filename'].lower()]
            else:
                docs = all_docs
            
            if docs:
                st.caption(f"📄 {len(docs)} document{'s' if len(docs) != 1 else ''}")
                
                # Simple document list
                for doc in docs[-50:]:  # Show last 50
                    col1, col2 = st.columns([5, 1])
                    
                    with col1:
                        is_current = doc['document_id'] == st.session_state.current_document_id
                        if is_current:
                            st.markdown(f"**✅ {doc['filename'][:30]}...**")
                        else:
                            if st.button(
                                f"📄 {doc['filename'][:30]}...", 
                                key=f"doc_{doc['document_id']}",
                                use_container_width=True
                            ):
                                st.session_state.current_document_id = doc['document_id']
                                st.session_state.messages = []
                                st.session_state.document_info = doc
                                st.rerun()
                    
                    with col2:
                        # Direct delete - no confirmation dialog
                        if st.button("🗑️", key=f"del_{doc['document_id']}", help="Delete"):
                            # Set deletion state and rerun to process
                            st.session_state.delete_confirmed = doc['document_id']
                            st.session_state.delete_doc_name = doc['filename']
                            st.rerun()
            else:
                st.info("📂 No documents yet")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Cannot load documents: {str(e)}")
    except (KeyError, ValueError) as e:
        st.error(f"❌ Document data error: {str(e)}")
    
    st.markdown("---")
    
    # Settings section follows
    st.header("⚙️ Settings")
    # Compact system monitor
    with st.expander("📊 System Status", expanded=False):
        system_info = get_system_info()
        st.metric("Available Memory", f"{system_info['available_memory_gb']:.1f}GB")
        st.progress(1 - system_info['memory_percent'] / 100)
        
        # Storage stats
        try:
            storage_response = requests.get("http://localhost:8080/storage-stats", timeout=2)
            if storage_response.status_code == 200:
                stats = storage_response.json()
                st.metric("Documents", f"{stats['document_count']}/{stats['max_documents']}")
                st.metric("Storage Used", f"{stats['total_size_mb']:.1f}MB")
        except:
            pass
    
    
    # Quick presets at the top
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Precise Mode", use_container_width=True, help="Best for facts & data"):
            st.session_state.chunk_size = 500
            st.session_state.temperature = 0.3
            st.session_state.max_results = 3
            add_notification("✅ Switched to Precise Mode", "success", 3)
            
    with col2:
        if st.button("📚 Creative Mode", use_container_width=True, help="Best for stories & ideas"):
            st.session_state.chunk_size = 1500
            st.session_state.temperature = 0.7
            st.session_state.max_results = 10
            add_notification("✅ Switched to Creative Mode", "success", 3)
    
    # Advanced settings (simplified)
    if st.checkbox("Show Advanced Settings"):
        st.session_state.temperature = st.slider(
            "Creativity",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperature,
            step=0.1,
            help="0 = Factual, 1 = Creative"
        )
        
        st.session_state.max_results = st.slider(
            "Context Sources",
            min_value=3,
            max_value=20,
            value=st.session_state.max_results,
            help="More sources = comprehensive answers"
        )
        
        st.session_state.chunk_size = st.slider(
            "Chunk Size",
            min_value=300,
            max_value=2000,
            value=st.session_state.chunk_size,
            step=100,
            help="Affects new uploads only"
        )
    
    # Clear chat button
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            add_notification("💬 Chat cleared", "info", 2)
            st.rerun()

# Custom CSS for better UX
st.markdown("""
<style>
    /* Better file uploader */
    [data-testid="stFileUploader"] {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    
    /* Notification styling */
    .stAlert {
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(-100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    /* Better button hover */
    button:hover {
        transform: translateY(-1px);
        transition: transform 0.2s;
    }
    
    /* Chat message styling */
    [data-testid="stChatMessage"] {
        border-radius: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)