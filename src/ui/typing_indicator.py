"""Typing indicator component for chat interface"""
import streamlit as st
import time
from typing import Optional, List


def render_typing_indicator(model_name: str = "AI") -> None:
    """Display animated typing indicator"""
    st.markdown(f"""
    <div class="typing-indicator">
        <span>{model_name} is typing</span>
        <div class="typing-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_processing_status(status: str, icon: str = "🤔") -> None:
    """Display processing status with custom message"""
    st.markdown(f"""
    <div class="processing-status">
        <div class="status-icon">{icon}</div>
        <div class="status-text">{status}</div>
        <div class="status-spinner"></div>
    </div>
    """, unsafe_allow_html=True)


def show_model_thinking(model_name: str, thoughts: Optional[List[str]] = None) -> None:
    """Show what the model is 'thinking' about"""
    default_thoughts = [
        "Reading the document...",
        "Understanding your question...",
        "Searching for relevant information...",
        "Formulating response..."
    ]
    
    thoughts = thoughts or default_thoughts
    
    # Cycle through thoughts
    thought_placeholder = st.empty()
    for i, thought in enumerate(thoughts):
        thought_placeholder.markdown(f"""
        <div class="thinking-bubble">
            <div class="thought-icon">💭</div>
            <div class="thought-text">{model_name}: {thought}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if i < len(thoughts) - 1:
            time.sleep(1.5)
    
    # Clear the thinking bubble
    thought_placeholder.empty()