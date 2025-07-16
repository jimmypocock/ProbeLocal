"""URL input component for web content analysis"""
import streamlit as st
import requests
from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse
from .notifications import add_notification
from .error_display import parse_api_error


def is_valid_url(url: str) -> bool:
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def render_url_input() -> None:
    """Render URL input interface"""
    st.markdown("### 🌐 Analyze Web Content")
    
    # URL input with validation
    url = st.text_input(
        "Enter a URL to fetch and analyze its content",
        placeholder="https://example.com/article",
    )
    
    if url:
        if not is_valid_url(url):
            st.error("❌ Please enter a valid URL (e.g., https://example.com)")
            return
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Show URL preview
            st.info(f"🔗 {url[:80]}{'...' if len(url) > 80 else ''}")
        
        with col2:
            if st.button("📥 Fetch & Analyze", type="primary", use_container_width=True):
                process_url(url)


def process_url(url: str) -> None:
    """Process URL by fetching and converting to document"""
    with st.spinner(f"🌐 Fetching content from {urlparse(url).netloc}..."):
        try:
            # Call API to process URL
            response = requests.post(
                "http://localhost:8080/process-url",
                json={
                    "url": url,
                    "model": st.session_state.get('current_model', 'mistral'),
                    "chunk_size": st.session_state.get('chunk_size', 1000),
                    "temperature": st.session_state.get('temperature', 0.1)
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                document_id = result.get('document_id')
                title = result.get('title', 'Web Content')
                
                # Update session state
                st.session_state.current_document_id = document_id
                st.session_state.messages = []
                
                add_notification(f"✅ Successfully loaded: {title}", "success")
                st.rerun()
            else:
                error_detail = response.json().get('detail', 'Failed to process URL')
                add_notification(f"❌ {error_detail}", "error")
                
        except requests.exceptions.ConnectionError:
            add_notification("🔴 Cannot connect to API. Ensure it's running: `python main.py`", "error")
        except requests.exceptions.Timeout:
            add_notification("⏱️ Request timed out. The webpage might be too large or slow to load.", "error")
        except Exception as e:
            add_notification(f"❌ Error: {str(e)}", "error")


