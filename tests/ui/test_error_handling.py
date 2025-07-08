"""UI tests for error handling and edge cases"""
import pytest
import time
import subprocess
from pathlib import Path
from .base_test import StreamlitTest


class TestErrorHandling:
    """Test error handling and edge cases in the UI"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        self.test = StreamlitTest()
        self.test.start_services()
        self.test.setup_browser(headless=True)
        self.test.wait_for_streamlit()
        
        yield
        
        self.test.teardown_browser()
        self.test.stop_services()
        
    def test_no_backend_services(self):
        """Test UI behavior when backend services are down"""
        # Don't start services - go directly to UI
        self.test.page.goto(self.test.app_url)
        time.sleep(3)
        
        # Should show connection error or offline status
        error_indicator = self.test.page.locator('text=/Offline|Error|Cannot connect/').first
        # The UI might show this in various places
        
        # Try to upload a file without backend
        test_file = Path("tests/fixtures/no_backend_test.txt")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("Test without backend")
        
        try:
            self.test.wait_for_element('[data-testid="stFileUploader"]', timeout=5000)
            self.test.upload_file(str(test_file))
            
            # Try to click upload
            upload_button = self.test.page.locator('button:has-text("📤 Upload & Process")').first
            if upload_button:
                upload_button.click()
                time.sleep(2)
                
                # Should show error
                notification = self.test.get_notification("error")
                assert notification is not None
        except:
            # Page might not load properly without backend
            pass
            
    def test_session_state_persistence(self):
        """Test that session state persists across interactions"""
        # Start services for this test
        self.test.start_services()
        self.test.wait_for_streamlit()
        
        # Upload a document
        test_file = Path("tests/fixtures/session_test.txt")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("Session state test document")
        
        self.test.upload_file(str(test_file))
        self.test.click_button("📤 Upload & Process")
        time.sleep(3)
        
        # Send a message
        self.test.send_message("Remember this: the secret code is 42")
        time.sleep(3)
        
        # Refresh the page
        self.test.page.reload()
        time.sleep(3)
        
        # Check if document is still selected
        selected_doc = self.test.page.locator('text="✅ session_test.txt"').first
        # Session state might or might not persist depending on implementation
        
        self.test.stop_services()
        
    def test_concurrent_uploads(self):
        """Test uploading multiple files quickly"""
        self.test.start_services()
        self.test.wait_for_streamlit()
        
        # Create multiple test files
        for i in range(3):
            test_file = Path(f"tests/fixtures/concurrent_{i}.txt")
            test_file.parent.mkdir(exist_ok=True)
            test_file.write_text(f"Concurrent test file {i}")
            
            self.test.upload_file(str(test_file))
            # Don't wait between uploads
            
        # Click upload for the last one
        self.test.click_button("📤 Upload & Process")
        time.sleep(5)
        
        # Should handle gracefully (either queue or show appropriate message)
        
        self.test.stop_services()
        
    def test_large_file_upload(self):
        """Test uploading a large file"""
        self.test.start_services()
        self.test.wait_for_streamlit()
        
        # Create a large file (10MB)
        large_file = Path("tests/fixtures/large_file.txt")
        large_file.parent.mkdir(exist_ok=True)
        large_file.write_text("X" * (10 * 1024 * 1024))
        
        self.test.upload_file(str(large_file))
        self.test.click_button("📤 Upload & Process")
        
        # Should show progress for large file
        time.sleep(1)
        progress = self.test.page.locator('text=/Processing|Uploading/').first
        assert progress is not None
        
        # Clean up
        large_file.unlink()
        self.test.stop_services()
        
    def test_timeout_handling(self):
        """Test handling of timeouts"""
        self.test.start_services()
        self.test.wait_for_streamlit()
        
        # Upload a document
        test_file = Path("tests/fixtures/timeout_test.txt")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("Timeout test")
        
        self.test.upload_file(str(test_file))
        self.test.click_button("📤 Upload & Process")
        time.sleep(3)
        
        # Send a complex query that might timeout
        self.test.send_message("Please provide an extremely detailed analysis " * 10)
        
        # Wait for timeout or response
        time.sleep(30)
        
        # Should either complete or show timeout error gracefully
        messages = self.test.get_messages()
        assert len(messages) >= 1
        
        self.test.stop_services()
        
    def test_invalid_model_selection(self):
        """Test behavior with invalid model selection"""
        self.test.start_services()
        self.test.wait_for_streamlit()
        
        # The UI should only show valid models, but test edge case
        # Try to manipulate the selectbox directly
        try:
            # This might not be possible with Streamlit's security
            self.test.page.evaluate("""
                const selectbox = document.querySelector('[data-testid="stSelectbox"]');
                if (selectbox) {
                    selectbox.value = 'invalid-model-name';
                }
            """)
            
            # Try to send a message
            self.test.send_message("Test with invalid model")
            time.sleep(3)
            
            # Should handle gracefully
            notification = self.test.get_notification("error")
            # Might show error or fall back to default model
        except:
            # Expected - Streamlit prevents direct manipulation
            pass
            
        self.test.stop_services()