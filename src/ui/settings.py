"""Settings UI components"""
import streamlit as st
from .utils import get_system_info, get_storage_stats
from .notifications import add_notification
from .session_manager import save_session


def render_system_monitor() -> None:
    """Render system monitor in an expander"""
    with st.expander("📊 System Status", expanded=False):
        system_info = get_system_info()
        st.metric("Available Memory", f"{system_info['available_memory_gb']:.1f}GB")
        st.progress(1 - system_info['memory_percent'] / 100)

        # Storage stats
        stats = get_storage_stats()
        if stats and 'error' not in stats:
            st.metric("Documents", f"{stats.get('total_documents', 0)}/{stats.get('max_documents', 20)}")
            st.metric("Storage Used", f"{stats.get('total_size_mb', 0):.1f}MB")


def render_preset_buttons() -> None:
    """Render quick preset buttons"""
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Precise Mode", use_container_width=True, help="Best for facts & data"):
            st.session_state.chunk_size = 500
            st.session_state.temperature = 0.3
            st.session_state.max_results = 3
            save_session()  # Save settings change
            add_notification("✅ Switched to Precise Mode", "success", 3)

    with col2:
        if st.button("📚 Creative Mode", use_container_width=True, help="Best for stories & ideas"):
            st.session_state.chunk_size = 1500
            st.session_state.temperature = 0.7
            st.session_state.max_results = 10
            save_session()  # Save settings change
            add_notification("✅ Switched to Creative Mode", "success", 3)


def render_advanced_settings() -> None:
    """Render advanced settings controls"""
    if st.checkbox("Show Advanced Settings"):
        # Temperature slider
        new_temp = st.slider(
            "Creativity",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperature,
            step=0.1,
            help="0 = Factual, 1 = Creative",
            key="temp_slider"
        )
        if new_temp != st.session_state.temperature:
            st.session_state.temperature = new_temp
            save_session()
        
        # Streaming toggle
        new_streaming = st.toggle(
            "⚡ Response Streaming",
            value=st.session_state.get('use_streaming', True),
            help="Stream responses as they're generated for faster feedback",
            key="streaming_toggle"
        )
        if new_streaming != st.session_state.get('use_streaming', True):
            st.session_state.use_streaming = new_streaming
            save_session()

        # Max results slider
        new_max_results = st.slider(
            "Context Sources",
            min_value=3,
            max_value=20,
            value=st.session_state.max_results,
            help="More sources = comprehensive answers",
            key="max_results_slider"
        )
        if new_max_results != st.session_state.max_results:
            st.session_state.max_results = new_max_results
            save_session()

        # Chunk size slider
        new_chunk_size = st.slider(
            "Chunk Size",
            min_value=300,
            max_value=2000,
            value=st.session_state.chunk_size,
            step=100,
            help="Affects new uploads only",
            key="chunk_size_slider"
        )
        if new_chunk_size != st.session_state.chunk_size:
            st.session_state.chunk_size = new_chunk_size
            save_session()


def render_clear_chat_button() -> None:
    """Render clear chat button if there are messages"""
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            save_session()  # Save after clearing chat
            add_notification("💬 Chat cleared", "info", 2)
            st.rerun()


def render_settings_section() -> None:
    """Render the complete settings section"""
    st.header("⚙️ Settings")
    render_system_monitor()
    render_preset_buttons()
    render_advanced_settings()
    render_clear_chat_button()
