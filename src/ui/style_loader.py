"""Style loader utility for loading CSS in Streamlit"""

import streamlit as st
from pathlib import Path


def load_app_styles():
    """Load the main CSS file"""
    css_path = Path("assets/css/main.css")
    
    if css_path.exists():
        with open(css_path, "r") as f:
            css_content = f.read()
        
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    else:
        st.warning(f"CSS file not found: {css_path}")


def inject_custom_css(css: str):
    """Inject custom CSS directly"""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# For backward compatibility
def load_app_styles_compat(force_reload: bool = False):
    """Compatibility wrapper"""
    # Just call the main function
    load_app_styles()