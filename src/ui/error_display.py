"""Error display components for better UX"""
import streamlit as st
import re
from typing import Optional


def format_error_message(error_text: str) -> str:
    """Format error messages with proper markdown and styling"""
    # Convert markdown code blocks
    error_text = re.sub(r'```(\w+)?', '```', error_text)
    
    # Ensure proper formatting
    return error_text.strip()


def display_error_with_retry(error_msg: str, retry_action: Optional[callable] = None) -> None:
    """Display error with optional retry button"""
    # Create expandable error container
    with st.container():
        # Parse error type from message
        if "🔴" in error_msg:
            st.error(error_msg, icon="🔴")
        elif "🟡" in error_msg:
            st.warning(error_msg, icon="🟡")
        elif "⚠️" in error_msg:
            st.warning(error_msg, icon="⚠️")
        else:
            st.error(error_msg)
        
        # Add retry button if action provided
        if retry_action:
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("🔄 Retry", type="primary", use_container_width=True):
                    retry_action()
            with col2:
                if st.button("❓ Get Help", use_container_width=True):
                    show_help_dialog()


def show_help_dialog() -> None:
    """Show help dialog with common solutions"""
    with st.expander("💡 Troubleshooting Help", expanded=True):
        st.markdown("""
        ### Common Solutions
        
        **1. Ollama Not Running?**
        ```bash
        # Start Ollama
        ollama serve
        
        # Install a model
        ollama pull mistral
        ```
        
        **2. API Connection Failed?**
        ```bash
        # Start the API
        python main.py
        ```
        
        **3. Out of Memory?**
        - Close other applications
        - Try smaller documents
        - Reduce chunk size in settings
        
        **4. Model Errors?**
        - Try switching to 'mistral' model
        - Check model compatibility
        
        ### Need More Help?
        - Check the [GitHub Issues](https://github.com/anthropics/claude-code/issues)
        - Review the logs in your terminal
        """)


def display_connection_status(service: str, is_connected: bool) -> None:
    """Display connection status indicator"""
    if is_connected:
        st.success(f"✅ {service} Connected")
    else:
        error_msg = {
            "Ollama": "🔴 Ollama not running - Run `ollama serve` to start",
            "API": "🔴 API not running - Run `python main.py` to start",
            "Models": "🟡 No models found - Run `ollama pull mistral` to install"
        }.get(service, f"🔴 {service} disconnected")
        
        st.error(error_msg)


def parse_api_error(response_json: dict) -> str:
    """Parse API error response and return formatted message"""
    if 'detail' in response_json:
        detail = response_json['detail']
        
        # If detail is already a formatted error message, return it
        if isinstance(detail, str) and any(icon in detail for icon in ['🔴', '🟡', '⚠️', '❌']):
            return detail
        
        # Otherwise, format it
        return f"❌ **API Error**\n\n{detail}"
    
    return "❌ Unknown error occurred"