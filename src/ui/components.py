"""Reusable UI components"""
import streamlit as st
import requests
from typing import Optional, Tuple
from .utils import check_ollama, get_available_models, get_model_info
from .notifications import add_notification
from .connection_status import render_compact_status, render_status_card
from .session_manager import initialize_session, save_session, get_session_info


def render_header() -> None:
    """Render the main header with status indicators"""
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

    with col1:
        st.title("🤖 Greg - AI Playground")
        st.caption("Your Local AI Assistant - 100% Free and Private")

    with col2:
        # Service status indicators
        st.markdown("**Status:**")
        render_compact_status()

    with col3:
        # System status expander
        render_status_card()

    with col4:
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


def render_model_selector() -> Optional[str]:
    """Render model selector and return selected model"""
    available_models = get_available_models()

    if available_models:
        selected_model = st.selectbox(
            "AI Model",
            available_models,
            index=(available_models.index(st.session_state.current_model)
                   if st.session_state.current_model in available_models else 0),
            key="model_selector"
        )

        if selected_model != st.session_state.current_model:
            st.session_state.current_model = selected_model
            add_notification(f"🔄 Switched to {selected_model}", "info", 3)

        return selected_model
    return None


def init_session_state() -> None:
    """Initialize all session state variables"""
    # Use the new isolated session manager
    initialize_session()
    
    # Additional defaults not handled by session manager
    additional_defaults = {
        'notifications': [],
        'toast_notifications': [],  # Add toast notifications
        'toast_shown': set(),  # Track shown toasts
        'document_search': "",
        'show_advanced': False,
        'delete_confirmed': None,
        'pending_question': None,
        'use_streaming': True  # Enable streaming by default
    }

    for key, default_value in additional_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # Save session after initialization
    save_session()


