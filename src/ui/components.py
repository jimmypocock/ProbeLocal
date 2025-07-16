"""Reusable UI components"""
import streamlit as st
import requests
from typing import Optional, Tuple
from .utils import check_ollama, get_available_models, get_model_info
from .notifications import add_notification
from .session_manager import initialize_session, save_session, get_session_info


def render_header() -> None:
    """Render the main header"""
    st.title("🤖 Greg - AI Playground")
    st.caption("Your Local AI Assistant - 100% Free and Private")


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
            # Import model manager
            from src.ui.model_manager import switch_model, estimate_model_memory
            
            old_model = st.session_state.current_model
            
            # Check memory implications
            new_model_size = estimate_model_memory(selected_model)
            if new_model_size > 8.0:  # Warning for large models
                st.warning(f"⚠️ {selected_model} uses ~{new_model_size:.1f}GB RAM")
            
            # Perform smart model switch
            try:
                switch_model(selected_model, old_model)
                st.session_state.current_model = selected_model
                add_notification(f"✅ Switched to {selected_model}", "success", 3)
            except Exception as e:
                add_notification(f"❌ Failed to switch model: {str(e)}", "error", 5)
                # Revert selection
                st.session_state.current_model = old_model

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
        'delete_confirmed': None
    }

    for key, default_value in additional_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # Save session after initialization
    save_session()


