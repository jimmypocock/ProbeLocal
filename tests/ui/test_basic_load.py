"""Basic test to verify UI loads correctly"""
import pytest
import time
from pathlib import Path
from .base_test import StreamlitTest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestBasicLoad:
    """Test basic app loading"""
    
    def test_app_loads(self):
        """Test that the app loads successfully"""
        test = StreamlitTest()
        try:
            # Start services
            test.start_services()
            test.setup_driver(headless=True)
            
            # Navigate to app
            test.driver.get(test.app_url)
            
            # Wait for app to load
            wait = WebDriverWait(test.driver, 30)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="stApp"]')))
            
            # Take screenshot first to see what's on the page
            test.take_screenshot("app_loaded")
            
            # Print page title and content for debugging
            print(f"Page title: {test.driver.title}")
            print(f"Page URL: {test.driver.current_url}")
            
            # Check for header
            header_found = False
            try:
                # Look for header with Greg text
                headers = test.driver.find_elements(By.TAG_NAME, "h1")
                for header in headers:
                    if "Greg" in header.text:
                        header_found = True
                        print(f"Header found: {header.text}")
                        break
            except:
                pass
            
            assert header_found, "Could not find app header"
            
            # Check for web search checkbox or file uploader
            ui_element_found = False
            
            # Check for web search checkbox
            try:
                checkboxes = test.driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                for checkbox in checkboxes:
                    parent = checkbox.find_element(By.XPATH, '../..')
                    if "search web" in parent.text.lower():
                        ui_element_found = True
                        print("Found web search checkbox")
                        break
            except:
                pass
            
            # Or check for file uploader
            if not ui_element_found:
                try:
                    file_inputs = test.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
                    if file_inputs:
                        ui_element_found = True
                        print("Found file uploader")
                except:
                    pass
            
            assert ui_element_found, "Could not find file uploader or web search option"
            
        finally:
            test.teardown()
    
    def test_api_health(self):
        """Test that API is healthy"""
        import requests
        test = StreamlitTest()
        try:
            test.start_services()
            
            # Check API health
            response = requests.get(f"{test.api_url}/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
            
        finally:
            test.stop_services()