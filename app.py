import streamlit as st
import requests
import json
import subprocess
import psutil
import time
from typing import Dict, Any

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

st.set_page_config(
page_title="Probe Local - PDF Q&A",
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

st.title("🔍 Probe Local - PDF Question Answering")
st.markdown("100% Free, Local, and Private!")

# System status sidebar
with st.sidebar:
    st.header("⚙️ System Status")

    system_info = get_system_info()
    st.metric("Available Memory", f"{system_info['available_memory_gb']:.1f} GB")
    st.progress(1 - system_info['memory_percent'] / 100)

    ollama_status = check_ollama()
    if ollama_status:
        st.success("✅ Ollama is running")
    else:
        st.error("❌ Ollama not running")
        st.code("ollama serve", language="bash")
        st.stop()

    # Get available models from Ollama
    available_models = []
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
    except:
        available_models = ["mistral"]  # Fallback
    
    # Initialize selected model in session state
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = st.session_state.get('current_model', available_models[0] if available_models else "mistral")
    
    # Model selection
    selected_model = st.selectbox(
        "🤖 Select Model",
        available_models,
        index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
        help="Switch between different AI models"
    )
    
    # Check if model changed
    if selected_model != st.session_state.selected_model:
        if st.button("🔄 Switch Model", type="primary", use_container_width=True):
            st.session_state.selected_model = selected_model
            st.session_state.messages = []  # Clear chat history
            st.session_state.current_model = selected_model
            st.success(f"Switched to {selected_model}")
            st.warning("⚠️ Chat history cleared. Please ask your questions again.")
            time.sleep(1)
            st.rerun()
    
    # Show current model info
    if available_models:
        model_size = "Unknown"
        try:
            for model in models_data.get('models', []):
                if model['name'] == st.session_state.selected_model:
                    size_gb = model.get('size', 0) / (1024**3)
                    model_size = f"{size_gb:.1f}GB"
                    break
        except:
            pass
        st.info(f"📊 Current: {st.session_state.selected_model} ({model_size})")

    st.markdown("---")

    st.header("📚 Documents")

    # File upload
    uploaded_file = st.file_uploader("Choose a PDF", type="pdf", key="pdf_uploader")
    
    if uploaded_file is not None:
        # Disable button while processing
        if st.button("📤 Upload & Process", disabled=st.session_state.is_processing):
            st.session_state.is_processing = True
            
            # Create a placeholder for status messages
            status_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            with status_placeholder.container():
                st.info(f"📋 Processing {uploaded_file.name} with {st.session_state.selected_model}...")
            
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            try:
                progress_bar.progress(25)
                response = requests.post("http://localhost:8080/upload", files=files, timeout=300)
                progress_bar.progress(90)
            except requests.exceptions.ConnectionError:
                st.session_state.is_processing = False
                progress_bar.empty()
                status_placeholder.empty()
                st.error("❌ Cannot connect to API server. Please make sure to run: python main.py")
                st.stop()
            except requests.exceptions.Timeout:
                st.session_state.is_processing = False
                progress_bar.empty()
                status_placeholder.empty()
                st.error("❌ Request timed out. The PDF might be too large.")
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
                st.info(f"Pages: {result['pages']} | Chunks: {result['chunks']}")
                st.info(f"Document ID: {result['document_id'][:8]}...")
                
                # Reset processing state
                st.session_state.is_processing = False
                
                # Force a rerun to update the button state
                st.rerun()
            else:
                st.session_state.is_processing = False
                progress_bar.empty()
                status_placeholder.empty()
                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
        
        # Show processing indicator if still processing
        if st.session_state.is_processing:
            st.warning("⏳ Processing in progress... Please wait.")
    
    # Show document list here instead of at the bottom
    st.markdown("---")
    
    # Show current document selection
    if st.session_state.current_document_id:
        st.success(f"📖 Active: {st.session_state.current_document_id[:8]}...")
    else:
        st.warning("⚠️ No document selected")
    
    # List available documents
    try:
        response = requests.get("http://localhost:8080/documents", timeout=2)
        if response.status_code == 200:
            docs = response.json().get('documents', [])
            if docs:
                st.subheader("Available Documents")
                for doc in docs[-10:]:  # Show last 10 documents
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        # Highlight if this is the current document
                        is_current = doc['document_id'] == st.session_state.current_document_id
                        button_label = f"{'✅' if is_current else '📄'} {doc['filename'][:25]}..."
                        # Use callback to avoid double-click issue
                        def select_document(doc_id):
                            st.session_state.current_document_id = doc_id
                            st.session_state.messages = []  # Clear chat when switching
                        
                        st.button(
                            button_label, 
                            key=doc['document_id'], 
                            type="primary" if is_current else "secondary",
                            use_container_width=True,
                            on_click=select_document,
                            args=(doc['document_id'],)
                        )
                    with col2:
                        if st.button("🗑️", key=f"del_{doc['document_id']}", help=f"Delete {doc['filename']}"):
                            # Delete individual document
                            try:
                                del_response = requests.delete(f"http://localhost:8080/documents/{doc['document_id']}", timeout=5)
                                if del_response.status_code == 200:
                                    if st.session_state.current_document_id == doc['document_id']:
                                        st.session_state.current_document_id = None
                                        st.session_state.messages = []  # Clear chat history for deleted doc
                                    st.success("Document deleted successfully!")
                                    time.sleep(0.5)  # Brief pause to show success message
                                    st.rerun()
                                elif del_response.status_code == 404:
                                    st.warning("Document not found")
                                else:
                                    st.error(f"Failed to delete: {del_response.json().get('detail', 'Unknown error')}")
                            except requests.exceptions.RequestException as e:
                                st.error(f"Failed to delete document: {str(e)}")
                
                # Add clear all button
                st.markdown("---")
                if st.button("🗑️ Clear All Documents", type="secondary", use_container_width=True):
                    if st.button("⚠️ Confirm Clear All", type="primary", key="confirm_clear"):
                        try:
                            clear_response = requests.post("http://localhost:8080/clear-all")
                            if clear_response.status_code == 200:
                                st.session_state.current_document_id = None
                                st.session_state.messages = []
                                st.success("All documents cleared!")
                                st.rerun()
                        except:
                            st.error("Failed to clear documents")
            else:
                st.info("No documents uploaded yet")
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API server")
    except Exception:
        # Silent fail for other errors
        pass

# Main area

st.markdown("### 💬 Ask Questions")


# Check if document is loaded
if st.session_state.current_document_id is None:
    st.warning("📚 Please select a document from the sidebar or upload a new PDF.")
    
    # Check if there are any documents available
    try:
        response = requests.get("http://localhost:8080/documents", timeout=2)
        if response.status_code == 200:
            docs = response.json().get('documents', [])
            if docs:
                st.info(f"💡 You have {len(docs)} document(s) available. Click one in the sidebar to start asking questions!")
    except:
        # Silent fail - don't show errors here
        pass
else:
    # Get document name for display
    doc_name = "your document"
    try:
        response = requests.get("http://localhost:8080/documents", timeout=2)
        if response.status_code == 200:
            docs = response.json().get('documents', [])
            for doc in docs:
                if doc['document_id'] == st.session_state.current_document_id:
                    doc_name = doc['filename']
                    break
    except:
        # Silent fail - use generic name
        pass
    
    st.success(f"✅ Ready to answer questions about: **{doc_name}**")

# Chat interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Query input
if st.session_state.current_document_id and (prompt := st.chat_input("Ask about your PDF...")):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response
    with st.chat_message("assistant"):
        with st.spinner("Thinking locally..."):
            # Make API call
            try:
                response = requests.post(
                    "http://localhost:8080/ask",
                    json={
                        "question": prompt,
                        "document_id": st.session_state.current_document_id,
                        "max_results": 5,
                        "model_name": st.session_state.selected_model
                    },
                    timeout=60
                )
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API server. Please make sure to run: python main.py")
                response = None
            except requests.exceptions.Timeout:
                st.error("❌ Request timed out. Please try a simpler question.")
                response = None

            if response and response.status_code == 200:
                result = response.json()
                st.markdown(result['answer'])

                # Show sources in expander
                with st.expander("📍 Sources"):
                    for source in result.get('sources', []):
                        st.caption(f"Page {source.get('page', 'N/A')}: {source.get('content', '')}")

                # Add assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result['answer']
                })
            else:
                st.error("Failed to get response")

# Performance tips in sidebar
with st.sidebar:
    st.markdown("---")
    with st.expander("💡 Performance Tips for M3"):
        st.markdown("""
    - **Mistral**: Best for general documents (7B parameters)
    - **Phi**: Fastest responses, good for simple Q&A (2.7B)
    - **Neural-chat**: Best quality, optimized for Apple Silicon (7B)
    - **CodeLlama**: Best for technical/code documentation
    
    **Tips:**
    - Close other apps to free memory
    - Smaller PDFs process faster
    - First question takes longer (model loading)
    - Subsequent questions are much faster
    """)