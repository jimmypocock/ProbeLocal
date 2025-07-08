"""Test web search UI functionality"""
import pytest
from playwright.sync_api import Page, expect
import time
from tests.ui.base_test import StreamlitTest


class TestWebSearchUI:
    """Test web search UI features"""
    
    def test_web_search_toggle_exists(self, page: Page):
        """Test that web search toggle is visible"""
        # Wait for app to load
        page.wait_for_selector("h1:has-text('Greg')", timeout=10000)
        
        # Check for web search toggle
        toggle = page.locator("text=🌐 Search Web")
        expect(toggle).to_be_visible()
        
        # Verify it's a toggle/switch element
        toggle_input = page.locator("input[type='checkbox'][aria-label*='Search Web']").or_(
            page.locator("button[role='switch'][aria-label*='Search Web']")
        )
        expect(toggle_input).to_be_visible()
    
    def test_web_search_toggle_functionality(self, page: Page):
        """Test toggling web search on and off"""
        # Wait for app to load
        page.wait_for_selector("h1:has-text('Greg')", timeout=10000)
        
        # Find the toggle
        toggle = page.locator("text=🌐 Search Web").first
        
        # Click to enable
        toggle.click()
        time.sleep(1)  # Wait for state update
        
        # Check that welcome message changes
        expect(page.locator("text=Web Search Mode Active!")).to_be_visible()
        
        # Click to disable
        toggle.click()
        time.sleep(1)
        
        # Check that it goes back to normal
        expect(page.locator("text=Getting Started:")).to_be_visible()
    
    def test_web_only_mode_chat(self, page: Page):
        """Test chat functionality in web-only mode"""
        # Enable web search
        page.locator("text=🌐 Search Web").first.click()
        time.sleep(1)
        
        # Check for web-specific example questions
        expect(page.locator("text=What's the latest news in AI?")).to_be_visible()
        expect(page.locator("text=Explain quantum computing")).to_be_visible()
        
        # Check chat input mentions "the web"
        chat_input = page.locator("textarea[placeholder*='Ask about']")
        expect(chat_input).to_be_visible()
        placeholder = chat_input.get_attribute("placeholder")
        assert "the web" in placeholder.lower()
    
    def test_web_search_with_document(self, page: Page):
        """Test web search toggle with a document loaded"""
        # First upload a document
        self._upload_test_file(page, "test.txt", "Test document content")
        time.sleep(2)
        
        # Enable web search
        page.locator("text=🌐 Search Web").first.click()
        time.sleep(1)
        
        # Chat input should still reference the document
        chat_input = page.locator("textarea[placeholder*='Ask about']")
        placeholder = chat_input.get_attribute("placeholder")
        assert "test.txt" in placeholder
    
    def test_example_questions_change(self, page: Page):
        """Test that example questions change based on mode"""
        # Check document mode questions
        expect(page.locator("text=Upload a document")).to_be_visible()
        
        # Enable web search
        page.locator("text=🌐 Search Web").first.click()
        time.sleep(1)
        
        # Check web mode questions
        expect(page.locator("text=What's the latest news in AI?")).to_be_visible()
        expect(page.locator("text=Tell me about climate change solutions")).to_be_visible()
        
        # Disable web search
        page.locator("text=🌐 Search Web").first.click()
        time.sleep(1)
        
        # Should go back to upload prompt
        expect(page.locator("text=Upload a document")).to_be_visible()
    
    def test_source_indicators_in_response(self, page: Page):
        """Test that responses show correct source indicators"""
        # This test would need API mocking to work properly
        # For now, just verify the UI elements exist
        
        # Enable web search
        page.locator("text=🌐 Search Web").first.click()
        time.sleep(1)
        
        # The UI should be ready to show source indicators
        # We can't test actual responses without mocking the API
        expect(page.locator("text=Web Search Mode Active!")).to_be_visible()
    
    def _upload_test_file(self, page: Page, filename: str, content: str):
        """Helper to upload a test file"""
        # Create a test file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{filename}', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Upload the file
            file_input = page.locator("input[type='file']").first
            file_input.set_input_files(temp_path)
            
            # Wait for upload to complete
            page.wait_for_selector("text=✅ Uploaded", timeout=10000)
        finally:
            # Clean up
            os.unlink(temp_path)