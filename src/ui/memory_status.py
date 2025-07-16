"""Memory status indicator for model management"""
import streamlit as st
import psutil
from src.ui.model_manager import get_loaded_models, estimate_model_memory


def render_memory_status():
    """Show current memory usage and loaded models"""
    # Get system memory info
    memory = psutil.virtual_memory()
    used_gb = (memory.total - memory.available) / (1024**3)
    total_gb = memory.total / (1024**3)
    percent = memory.percent
    
    # Get the actual active model from session state
    current_model = st.session_state.get('current_model', 'llama3:8b')
    loaded_models = [current_model] if current_model else []
    
    # Estimate model memory usage
    model_memory = sum(estimate_model_memory(m) for m in loaded_models)
    
    # Display memory info directly (no expander)
    st.markdown("### 💾 Memory Status")
    st.caption(f"{percent:.0f}% used ({used_gb:.1f}/{total_gb:.0f}GB)")
    
    # Show memory bar
    progress = min(percent / 100, 1.0)
    st.progress(progress)
    
    if loaded_models:
        st.markdown("**Loaded Model:**")
        for model in loaded_models:
            size = estimate_model_memory(model)
            st.caption(f"• {model} (~{size:.1f}GB)")
    else:
        st.caption("No models loaded")
    
    # Warnings/recommendations
    if percent > 85:
        st.error("⚠️ High memory usage! Consider switching to a smaller model.")
    elif model_memory > 8:
        st.warning("⚠️ Multiple large models loaded. Consider unloading unused models.")
    
    st.markdown("---")