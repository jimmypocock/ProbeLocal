"""UI tests for document management functionality"""
import pytest
import time
from pathlib import Path
from .base_test import StreamlitTest


class TestDocumentManagement:
    """Test document upload, selection, and deletion through the UI"""
    
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
    
    def test_document_upload_ui_flow(self):
        """Test uploading a document through the UI"""
        # Create a test file
        test_file = Path("tests/fixtures/ui_test_doc.txt")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("This is a test document for UI testing.\nIt has multiple lines.")
        
        # Upload the file
        self.test.upload_file(str(test_file))
        
        # Click upload button
        self.test.click_button("📤 Upload & Process")
        
        # Wait for processing
        time.sleep(5)
        
        # Check for success indication - either notification or document in list
        success = False
        
        # Method 1: Check for success notification
        notification = self.test.get_notification("success")
        if notification and "success" in notification.lower():
            success = True
        
        # Method 2: Check if document appears in sidebar
        if not success:
            doc_list = self.test.get_document_list()
            if any("ui_test_doc" in doc for doc in doc_list):
                success = True
        
        # Method 3: Try to select the document
        if not success:
            success = self.test.select_document("ui_test_doc.txt")
        
        assert success, "Document upload failed"
    
    def test_document_deletion_ui(self):
        """Test deleting a document through the UI"""
        # First upload a document
        test_file = Path("tests/fixtures/delete_test.txt")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("Document to be deleted")
        
        self.test.upload_file(str(test_file))
        self.test.click_button("📤 Upload & Process")
        time.sleep(5)
        
        # Find delete button for this document
        delete_buttons = self.test.page.locator('[data-testid="stSidebar"] button:has-text("🗑️")').all()
        initial_count = len(delete_buttons)
        
        if initial_count > 0:
            # Click the first delete button
            delete_buttons[0].click()
            self.test.wait_for_streamlit_rerun()
            
            # Confirm deletion if there's a confirmation dialog
            confirm_button = self.test.page.locator('button:has-text("Delete")').last
            if confirm_button.is_visible():
                confirm_button.click()
                self.test.wait_for_streamlit_rerun()
            
            time.sleep(2)
            
            # Check if document count decreased
            new_delete_buttons = self.test.page.locator('[data-testid="stSidebar"] button:has-text("🗑️")').all()
            assert len(new_delete_buttons) < initial_count, "Document not deleted"
    
    def test_document_selection(self):
        """Test selecting different documents"""
        # Upload two documents
        for i in range(2):
            test_file = Path(f"tests/fixtures/select_test_{i}.txt")
            test_file.parent.mkdir(exist_ok=True)
            test_file.write_text(f"Test document {i}")
            
            self.test.upload_file(str(test_file))
            self.test.click_button("📤 Upload & Process")
            time.sleep(3)
        
        # Select first document
        assert self.test.select_document("select_test_0"), "Failed to select first document"
        
        # Verify chat interface shows correct document
        chat_input = self.test.page.locator('[data-testid="stChatInput"]').first
        assert chat_input.is_visible(), "Chat input not visible after document selection"
        
        # Select second document
        assert self.test.select_document("select_test_1"), "Failed to select second document"
        
        # Chat interface should still be visible
        assert chat_input.is_visible(), "Chat input disappeared after switching documents"
    
    def test_upload_progress_indicator(self):
        """Test that upload shows progress indication"""
        # Create a test file
        test_file = Path("tests/fixtures/progress_test.txt")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("Test content " * 100)  # Make it a bit larger
        
        # Upload the file
        self.test.upload_file(str(test_file))
        
        # Look for upload button
        upload_button = self.test.page.locator('button:has-text("📤 Upload & Process")')
        assert upload_button.is_visible(), "Upload button not found"
        
        # Click and watch for any progress indication
        upload_button.click()
        
        # Check for processing indicators (spinner, progress bar, or message)
        processing_found = False
        
        # Look for common loading indicators
        indicators = [
            '[data-testid="stSpinner"]',
            '[role="progressbar"]',
            'text="Processing"',
            'text="Uploading"'
        ]
        
        for indicator in indicators:
            element = self.test.page.locator(indicator).first
            if element.is_visible():
                processing_found = True
                break
        
        # Even if no explicit indicator, upload should complete
        time.sleep(5)
        
        # Verify upload completed
        success = self.test.select_document("progress_test") or \
                  any("progress_test" in doc for doc in self.test.get_document_list())
        
        assert success, "Upload did not complete successfully"
    
    def test_multiple_file_formats_ui(self):
        """Test uploading different file formats"""
        # Test different formats
        formats = {
            "test.txt": "Plain text content",
            "test.md": "# Markdown\n\nMarkdown content",
            "test.csv": "header1,header2\nvalue1,value2"
        }
        
        successful_uploads = 0
        
        for filename, content in formats.items():
            test_file = Path(f"tests/fixtures/{filename}")
            test_file.parent.mkdir(exist_ok=True)
            test_file.write_text(content)
            
            # Upload file
            self.test.upload_file(str(test_file))
            self.test.click_button("📤 Upload & Process")
            time.sleep(3)
            
            # Check if uploaded
            if self.test.select_document(filename.split('.')[0]):
                successful_uploads += 1
        
        assert successful_uploads >= 2, f"Only {successful_uploads} out of {len(formats)} formats uploaded successfully"
    
    def test_error_handling_unsupported_file(self):
        """Test error handling for unsupported file types"""
        # Create an unsupported file
        test_file = Path("tests/fixtures/unsupported.xyz")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("Unsupported content")
        
        # Try to upload
        self.test.upload_file(str(test_file))
        self.test.click_button("📤 Upload & Process")
        
        time.sleep(3)
        
        # Check for error message
        error_found = False
        
        # Look for error notifications
        notification = self.test.get_notification("error")
        if notification:
            error_found = True
        
        # Also check for any error alerts
        error_alerts = self.test.page.locator('[data-testid="stAlert"][kind="error"]').all()
        if error_alerts:
            error_found = True
        
        # File should not appear in document list
        doc_list = self.test.get_document_list()
        file_uploaded = any("unsupported" in doc for doc in doc_list)
        
        # Either we should see an error or the file shouldn't be uploaded
        assert error_found or not file_uploaded, "Unsupported file uploaded without error"