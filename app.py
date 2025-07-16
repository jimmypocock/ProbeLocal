import os

# Set offline mode for HuggingFace to prevent HTTP 429 errors
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

import streamlit as st
import requests
import time
from src.ui.components import (
    render_header, 
    render_model_selector, 
    init_session_state
)
from src.ui.style_loader import load_app_styles
from src.ui.notifications import show_notifications
from src.ui.toast_notifications import render_toasts
from src.ui.document_manager import (
    render_document_status,
    render_document_list
)
from src.ui.url_input import render_url_input
from src.ui.chat_interface import (
    display_chat_messages,
    handle_chat_input,
    render_welcome_message
)
from src.ui.settings import render_settings_section

# Configure page with better defaults
st.set_page_config(
    page_title="Hello, I'm Greg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS immediately after page config
# This is the earliest point we can inject CSS in Streamlit
load_app_styles()

# Initialize session state
init_session_state()

# Removed the processed file markers cleanup - no longer needed

# Header with status
render_header()

# Main chat area
with st.container():
    # Model selection in main area for better visibility
    col1, col2 = st.columns([2, 1])
    with col1:
        st.header("Chat")
    with col2:
        selected_model = render_model_selector()
    
    # Web search toggle under Chat header
    use_web = st.toggle(
        "Search Web",
        value=st.session_state.get('use_web_search', True),  # Default to True
        help="Enable web search to supplement document answers",
        key="web_search_toggle"
    )
    st.session_state.use_web_search = use_web
    
    # Show notifications
    show_notifications()
    
    # Chat interface
    # Check if we have documents
    has_documents = False
    try:
        response = requests.get("http://localhost:8080/documents", timeout=2)
        if response.status_code == 200:
            has_documents = len(response.json().get('documents', [])) > 0
    except:
        pass
    
    if has_documents or st.session_state.get('use_web_search'):
        # Chat messages container
        chat_container = st.container()
        
        with chat_container:
            # Display existing messages
            display_chat_messages()
        
        # Chat input
        if has_documents:
            handle_chat_input(chat_container, "your documents")
        else:
            handle_chat_input(chat_container, "the web")
    else:
        st.info("📂 No documents in context. Add documents to the /documents folder and restart, or enable web search above.")

# Sidebar with document management and settings
with st.sidebar:
    # Memory status at the top
    from src.ui.memory_status import render_memory_status
    render_memory_status()
    # Get document count
    doc_count = 0
    try:
        response = requests.get("http://localhost:8080/documents", timeout=2)
        if response.status_code == 200:
            doc_count = len(response.json().get('documents', []))
    except:
        pass
    
    # Documents in Context
    st.header(f"Documents in Context ({doc_count})")
    
    # Current document status
    render_document_status()
    
    # Document list (read-only)
    render_document_list()
    
    st.markdown("---")
    
    # URL input section
    render_url_input()
    
    # Check for pending URL from examples
    if 'pending_url' in st.session_state and st.session_state.pending_url:
        st.text_input("URL", value=st.session_state.pending_url, key="url_input_field")
        st.session_state.pending_url = None
    
    st.markdown("---")
    
    # Settings section
    render_settings_section()

# Render toast notifications
render_toasts()