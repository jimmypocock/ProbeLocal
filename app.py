import os

# Set offline mode for HuggingFace to prevent HTTP 429 errors
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

import streamlit as st
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
    handle_file_upload,
    render_document_list,
    process_pending_deletions
)
from src.ui.drag_drop import render_drag_drop_upload
from src.ui.url_input import render_url_input, render_url_examples
from src.performance.optimizations import Debouncer, optimize_rerun
from src.ui.chat_interface import (
    render_example_questions,
    display_chat_messages,
    handle_pending_question,
    handle_chat_input,
    render_welcome_message
)
from src.ui.settings import render_settings_section

# Configure page with better defaults
st.set_page_config(
    page_title="Greg - AI Playground",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
init_session_state()

# Load app styles
load_app_styles()

# Process any pending deletions first
if process_pending_deletions():
    st.rerun()

# Header with status
render_header()

# Main chat area
with st.container():
    # Model selection in main area for better visibility
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.header("💬 Chat")
    with col2:
        selected_model = render_model_selector()
    with col3:
        # Web search toggle
        st.write("")  # Add spacing to align with selectbox
        use_web = st.toggle(
            "🌐 Search Web",
            value=st.session_state.get('use_web_search', False),
            help="Enable web search to supplement document answers",
            key="web_search_toggle"
        )
        st.session_state.use_web_search = use_web
    
    # Show notifications
    show_notifications()
    
    # Chat interface
    render_welcome_message()  # This now handles the state
    
    if st.session_state.current_document_id:  # Now includes "web_only"
        # Example questions
        if st.session_state.current_document_id != "web_only" or st.session_state.get('use_web_search'):
            render_example_questions()
        
        # Chat messages container
        chat_container = st.container()
        
        with chat_container:
            # Display existing messages
            display_chat_messages()
        
        # Process pending questions from example buttons
        handle_pending_question(chat_container)
        
        # Chat input
        if st.session_state.current_document_id == "web_only":
            doc_name = "the web"
        else:
            doc_name = st.session_state.document_info.get('filename', 'the document')
        handle_chat_input(chat_container, doc_name)

# Sidebar with document management and settings
with st.sidebar:
    # Document Management Section
    st.header("📚 Documents")
    
    # Current document status
    render_document_status()
    
    # Use drag-and-drop upload component
    uploaded_files = render_drag_drop_upload()
    
    if uploaded_files:
        # Process the first file (we can extend to handle multiple files later)
        uploaded_file = uploaded_files[0]
        handle_file_upload(
            uploaded_file,
            st.session_state.current_model,
            st.session_state.chunk_size,
            st.session_state.temperature
        )
    
    # URL input section
    st.markdown("---")
    with st.expander("🌐 Load from URL", expanded=False):
        render_url_input()
        
        # Check for pending URL from examples
        if 'pending_url' in st.session_state and st.session_state.pending_url:
            st.text_input("URL", value=st.session_state.pending_url, key="url_input_field")
            st.session_state.pending_url = None
    
    # Document search with debouncing
    st.markdown("---")
    
    # Initialize debouncer
    if 'debouncer' not in st.session_state:
        st.session_state.debouncer = Debouncer(delay=0.3)
    
    # Search input
    search_query = st.text_input("🔍 Search documents", placeholder="Type to filter...", key="doc_search")
    
    # Update search query with debouncing
    if 'last_search_query' not in st.session_state:
        st.session_state.last_search_query = ""
    
    # Only update if search query changed
    if search_query != st.session_state.last_search_query:
        st.session_state.last_search_query = search_query
        # Use debouncer to prevent excessive reruns
        if optimize_rerun('doc_search', cooldown=0.3):
            st.rerun()
    
    # Document list
    render_document_list(search_query)
    
    st.markdown("---")
    
    # Settings section
    render_settings_section()

# Load compiled CSS styles
load_app_styles()

# Render toast notifications
render_toasts()