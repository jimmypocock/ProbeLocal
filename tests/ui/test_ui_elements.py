"""Test basic UI elements are present"""
import pytest
from tests.ui.base_test import StreamlitTest


class TestUIElements:
    """Test that basic UI elements are present and visible"""
    
    def test_ui_components_visible(self):
        """Test that main UI components are visible"""
        test = StreamlitTest()
        test.start_services()
        test.setup_browser(headless=True)
        
        try:
            test.wait_for_streamlit()
            
            # Check header
            header = test.page.locator('h1:has-text("Greg")')
            assert header.is_visible(), "Header not visible"
            
            # Check file uploader
            file_uploader = test.page.locator('[data-testid="stFileUploader"]')
            assert file_uploader.is_visible(), "File uploader not visible"
            
            # Check sidebar
            sidebar = test.page.locator('[data-testid="stSidebar"]')
            assert sidebar.is_visible(), "Sidebar not visible"
            
            # Check for any alerts/notifications
            alerts = test.page.locator('[data-testid="stAlert"]').all()
            print(f"Found {len(alerts)} alerts")
            for alert in alerts:
                if alert.is_visible():
                    print(f"Alert: {alert.inner_text()}")
            
            # Check for model selector
            selectbox = test.page.locator('[data-testid="stSelectbox"]').first
            assert selectbox.is_visible(), "Model selector not visible"
            
            # Take screenshot
            test.take_screenshot("ui_elements_test")
            
            print("✓ All basic UI elements are visible")
            
        finally:
            test.teardown_browser()
            test.stop_services()