"""Retry button component for failed operations"""
import streamlit as st
from typing import Callable, Optional, Dict, Any
import time


def render_retry_button(
    operation_key: str,
    operation: Callable,
    operation_args: Optional[Dict[str, Any]] = None,
    button_text: str = "🔄 Retry",
    help_text: str = "Click to retry the failed operation"
) -> Optional[Any]:
    """
    Render a retry button for failed operations
    
    Args:
        operation_key: Unique key for the operation
        operation: Function to call on retry
        operation_args: Arguments to pass to the operation
        button_text: Text to display on the button
        help_text: Help text for the button
        
    Returns:
        Result of the operation if retried, None otherwise
    """
    if operation_args is None:
        operation_args = {}
    
    # Generate unique button key
    button_key = f"retry_{operation_key}_{int(time.time())}"
    
    if st.button(button_text, key=button_key, help=help_text, type="secondary"):
        # Show spinner during retry
        with st.spinner("Retrying operation..."):
            try:
                result = operation(**operation_args)
                return result
            except Exception as e:
                st.error(f"Retry failed: {str(e)}")
                return None
    
    return None


def render_retry_with_delay(
    operation_key: str,
    operation: Callable,
    operation_args: Optional[Dict[str, Any]] = None,
    delay: int = 3,
    auto_retry: bool = False
) -> Optional[Any]:
    """
    Render a retry button with optional countdown and auto-retry
    
    Args:
        operation_key: Unique key for the operation
        operation: Function to call on retry
        operation_args: Arguments to pass to the operation
        delay: Delay in seconds before allowing retry
        auto_retry: Whether to automatically retry after delay
        
    Returns:
        Result of the operation if retried, None otherwise
    """
    if operation_args is None:
        operation_args = {}
    
    # Track retry state
    retry_state_key = f"retry_state_{operation_key}"
    if retry_state_key not in st.session_state:
        st.session_state[retry_state_key] = {
            'attempts': 0,
            'last_attempt': 0,
            'countdown_active': False
        }
    
    state = st.session_state[retry_state_key]
    current_time = time.time()
    
    # Check if we're in cooldown
    time_since_last = current_time - state['last_attempt']
    if time_since_last < delay:
        remaining = int(delay - time_since_last)
        st.warning(f"⏱️ Retry available in {remaining} seconds...")
        
        if auto_retry and remaining == 0:
            # Auto-retry
            state['countdown_active'] = False
            return _perform_retry(operation, operation_args, state)
    else:
        # Show retry button
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button(
                f"🔄 Retry (Attempt {state['attempts'] + 1})",
                key=f"retry_btn_{operation_key}",
                type="secondary",
                use_container_width=True
            ):
                return _perform_retry(operation, operation_args, state)
        
        with col2:
            if state['attempts'] > 0:
                st.caption(f"Last: {int(time_since_last)}s ago")
    
    return None


def _perform_retry(operation: Callable, args: Dict, state: Dict) -> Optional[Any]:
    """Helper to perform the retry operation"""
    state['attempts'] += 1
    state['last_attempt'] = time.time()
    
    with st.spinner(f"Retrying... (Attempt {state['attempts']})"):
        try:
            result = operation(**args)
            st.success("✅ Operation successful!")
            # Reset attempts on success
            state['attempts'] = 0
            return result
        except Exception as e:
            st.error(f"❌ Attempt {state['attempts']} failed: {str(e)}")
            
            # Suggest next steps based on attempt count
            if state['attempts'] >= 3:
                st.info("💡 Multiple retries failed. Please check your connection and service status.")
            
            return None


def render_smart_retry(error_context: Dict[str, Any]) -> None:
    """
    Render context-aware retry options based on the error
    
    Args:
        error_context: Dictionary containing error details and context
    """
    error_type = error_context.get('type', 'unknown')
    error_msg = error_context.get('message', '')
    operation = error_context.get('operation')
    args = error_context.get('args', {})
    
    # Different retry strategies based on error type
    if error_type == 'connection':
        st.error("🔴 Connection Error")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Retry Connection", type="primary", use_container_width=True):
                with st.spinner("Reconnecting..."):
                    try:
                        result = operation(**args) if operation else None
                        st.success("✅ Connected successfully!")
                        st.rerun()
                    except:
                        st.error("Still unable to connect. Please check if services are running.")
        
        with col2:
            if st.button("🔧 Check Services", type="secondary", use_container_width=True):
                st.info("""
                **Check these services:**
                1. API: `python main.py`
                2. Ollama: `ollama serve`
                3. Model: `ollama list`
                """)
    
    elif error_type == 'timeout':
        st.warning("⏱️ Operation Timed Out")
        if st.button("🔄 Retry with Extended Timeout", type="primary"):
            # Retry with longer timeout
            extended_args = args.copy()
            extended_args['timeout'] = args.get('timeout', 30) * 2
            with st.spinner(f"Retrying with {extended_args['timeout']}s timeout..."):
                try:
                    result = operation(**extended_args) if operation else None
                    st.success("✅ Operation completed!")
                    st.rerun()
                except:
                    st.error("Operation still timed out. The file might be too large.")
    
    elif error_type == 'validation':
        st.error(f"❌ Validation Error: {error_msg}")
        st.info("Please correct the input and try again.")
    
    else:
        # Generic retry
        render_retry_button(
            operation_key=error_context.get('key', 'generic'),
            operation=operation,
            operation_args=args,
            help_text="Click to retry the operation"
        )