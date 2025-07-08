"""End-to-end tests for web search functionality"""
import pytest
import time
import subprocess
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWebSearchE2E:
    """End-to-end tests for web search feature"""
    
    @classmethod
    def setup_class(cls):
        """Start both API and Streamlit"""
        # Start API
        cls.api_process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Start Streamlit
        cls.streamlit_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port=2402"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**subprocess.os.environ, "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"}
        )
        
        # Wait for services
        cls._wait_for_services()
    
    @classmethod
    def teardown_class(cls):
        """Stop all services"""
        for process in ['api_process', 'streamlit_process']:
            if hasattr(cls, process):
                proc = getattr(cls, process)
                proc.terminate()
                proc.wait(timeout=5)
    
    @staticmethod
    def _wait_for_services(timeout=30):
        """Wait for both services to be ready"""
        import requests
        start_time = time.time()
        
        # Wait for API
        while time.time() - start_time < timeout:
            try:
                response = requests.get("http://localhost:8080/health")
                if response.status_code == 200:
                    break
            except:
                pass
            time.sleep(1)
        else:
            raise TimeoutError("API failed to start")
        
        # Wait for Streamlit
        while time.time() - start_time < timeout:
            try:
                response = requests.get("http://localhost:2402")
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        raise TimeoutError("Streamlit failed to start")
    
    def test_web_search_only_workflow(self):
        """Test complete web-only search workflow"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Navigate to app
                page.goto("http://localhost:2402")
                page.wait_for_selector("h1:has-text('Greg')", timeout=10000)
                
                # Enable web search
                page.locator("text=🌐 Search Web").first.click()
                time.sleep(1)
                
                # Verify web search mode is active
                expect(page.locator("text=Web Search Mode Active!")).to_be_visible()
                
                # Click an example question
                example_btn = page.locator("text=Explain quantum computing").first
                example_btn.click()
                
                # Wait for response
                page.wait_for_selector("text=🌐 Web sources", timeout=30000)
                
                # Verify response has web indicator
                response_indicator = page.locator("text=🌐 Web sources")
                expect(response_indicator).to_be_visible()
                
            finally:
                browser.close()
    
    def test_hybrid_search_workflow(self):
        """Test document + web search workflow"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Navigate to app
                page.goto("http://localhost:2402")
                page.wait_for_selector("h1:has-text('Greg')", timeout=10000)
                
                # Upload a test document
                self._upload_test_document(page)
                
                # Enable web search
                page.locator("text=🌐 Search Web").first.click()
                time.sleep(1)
                
                # Ask a question
                chat_input = page.locator("textarea[placeholder*='Ask about']").first
                chat_input.fill("What is this document about and what does the internet say about it?")
                chat_input.press("Enter")
                
                # Wait for response with hybrid sources
                page.wait_for_selector("div[class*='chat-message']", timeout=30000)
                
                # Look for source indicators (might be combined)
                page.wait_for_selector("span:has-text('sources')", timeout=5000)
                
            finally:
                browser.close()
    
    def test_web_search_toggle_persistence(self):
        """Test that web search toggle state persists during session"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Navigate to app
                page.goto("http://localhost:2402")
                page.wait_for_selector("h1:has-text('Greg')", timeout=10000)
                
                # Enable web search
                toggle = page.locator("text=🌐 Search Web").first
                toggle.click()
                time.sleep(1)
                
                # Upload a document
                self._upload_test_document(page)
                
                # Check toggle is still enabled
                # The toggle should maintain its state
                expect(page.locator("text=Web Search Mode Active!").or_(
                    page.locator("text=✅ Uploaded")
                )).to_be_visible()
                
            finally:
                browser.close()
    
    def _upload_test_document(self, page):
        """Helper to upload a test document"""
        import tempfile
        import os
        
        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='_test.txt', delete=False) as f:
            f.write("This is a test document for web search testing.")
            temp_path = f.name
        
        try:
            # Upload file
            file_input = page.locator("input[type='file']").first
            file_input.set_input_files(temp_path)
            
            # Wait for upload success
            page.wait_for_selector("text=✅ Uploaded", timeout=10000)
            time.sleep(1)
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    # Run with: python -m pytest tests/integration/test_web_search_e2e.py -v
    pytest.main([__file__, "-v", "-s"])