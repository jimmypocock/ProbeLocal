"""Connection status indicator component"""
import streamlit as st
import requests
import time
from typing import Dict, Tuple, Optional
import subprocess
import sys


def check_ollama_status() -> Tuple[bool, str]:
    """Check if Ollama service is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            # Get list of models
            data = response.json()
            models = data.get('models', [])
            if models:
                model_names = [m['name'] for m in models[:3]]  # Show first 3
                return True, f"Running ({len(models)} models)"
            else:
                return True, "Running (no models)"
        else:
            return False, "Not responding"
    except requests.exceptions.ConnectionError:
        return False, "Not running"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, f"Error: {str(e)[:30]}"


def check_api_status() -> Tuple[bool, str]:
    """Check if API service is running"""
    try:
        response = requests.get("http://localhost:8080/health", timeout=2)
        if response.status_code == 200:
            return True, "Running"
        else:
            return False, f"Error {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Not running"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, f"Error: {str(e)[:30]}"


def render_connection_status() -> None:
    """Render connection status indicators"""
    # Create columns for status indicators
    col1, col2 = st.columns(2)
    
    with col1:
        ollama_ok, ollama_status = check_ollama_status()
        if ollama_ok:
            st.success(f"🟢 Ollama: {ollama_status}")
        else:
            st.error(f"🔴 Ollama: {ollama_status}")
            if st.button("Start Ollama", key="start_ollama", use_container_width=True):
                with st.spinner("Starting Ollama..."):
                    try:
                        subprocess.Popen(["ollama", "serve"], 
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        time.sleep(3)  # Give it time to start
                        st.rerun()
                    except:
                        st.error("Failed to start Ollama. Please run: `ollama serve`")
    
    with col2:
        api_ok, api_status = check_api_status()
        if api_ok:
            st.success(f"🟢 API: {api_status}")
        else:
            st.error(f"🔴 API: {api_status}")
            if st.button("Start API", key="start_api", use_container_width=True):
                with st.spinner("Starting API..."):
                    try:
                        subprocess.Popen([sys.executable, "main.py"],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        time.sleep(3)  # Give it time to start
                        st.rerun()
                    except:
                        st.error("Failed to start API. Please run: `python main.py`")


def render_compact_status() -> None:
    """Render compact status indicator in header"""
    ollama_ok, _ = check_ollama_status()
    api_ok, _ = check_api_status()
    
    status_icons = []
    if ollama_ok:
        status_icons.append("🟢")
    else:
        status_icons.append("🔴")
    
    if api_ok:
        status_icons.append("🟢")
    else:
        status_icons.append("🔴")
    
    # Show status with hover tooltip
    status_text = "".join(status_icons)
    help_text = f"Ollama: {'✓' if ollama_ok else '✗'} | API: {'✓' if api_ok else '✗'}"
    
    st.markdown(
        f'<span title="{help_text}" class="status-help">{status_text}</span>',
        unsafe_allow_html=True
    )


def get_service_health() -> Dict[str, bool]:
    """Get health status of all services"""
    ollama_ok, _ = check_ollama_status()
    api_ok, _ = check_api_status()
    
    return {
        'ollama': ollama_ok,
        'api': api_ok,
        'all_healthy': ollama_ok and api_ok
    }


def render_status_card() -> None:
    """Render a detailed status card"""
    with st.expander("🔧 System Status", expanded=False):
        # Overall health
        health = get_service_health()
        if health['all_healthy']:
            st.success("✅ All systems operational")
        else:
            st.warning("⚠️ Some services need attention")
        
        # Detailed status
        st.markdown("### Service Status")
        
        # Ollama
        ollama_ok, ollama_status = check_ollama_status()
        col1, col2, col3 = st.columns([1, 3, 2])
        with col1:
            st.write("🤖 Ollama")
        with col2:
            if ollama_ok:
                st.success(ollama_status)
            else:
                st.error(ollama_status)
        with col3:
            if not ollama_ok:
                if st.button("Fix", key="fix_ollama"):
                    st.code("ollama serve", language="bash")
        
        # API
        api_ok, api_status = check_api_status()
        col1, col2, col3 = st.columns([1, 3, 2])
        with col1:
            st.write("🌐 API")
        with col2:
            if api_ok:
                st.success(api_status)
            else:
                st.error(api_status)
        with col3:
            if not api_ok:
                if st.button("Fix", key="fix_api"):
                    st.code("python main.py", language="bash")
        
        # Model info if Ollama is running
        if ollama_ok:
            st.markdown("### Available Models")
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    if models:
                        for model in models[:5]:  # Show up to 5 models
                            size_gb = model.get('size', 0) / 1e9
                            st.caption(f"• {model['name']} ({size_gb:.1f} GB)")
                    else:
                        st.info("No models installed. Run: `ollama pull mistral`")
            except:
                pass


def auto_refresh_status(refresh_interval: int = 30) -> None:
    """Auto-refresh connection status at intervals"""
    # Initialize last check time
    if 'last_status_check' not in st.session_state:
        st.session_state.last_status_check = 0
    
    current_time = time.time()
    if current_time - st.session_state.last_status_check > refresh_interval:
        st.session_state.last_status_check = current_time
        st.rerun()