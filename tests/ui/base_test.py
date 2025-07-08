"""Base test class for Streamlit UI tests - using Selenium"""
from .selenium_base import SeleniumStreamlitTest

# Alias for backward compatibility
StreamlitTest = SeleniumStreamlitTest