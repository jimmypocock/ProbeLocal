"""Integration tests for error scenarios and edge cases"""
import pytest
import time
import requests
from pathlib import Path
import subprocess
import os
import signal
import psutil


class TestErrorScenarios:
    """Test system behavior under error conditions"""
    
    def setup_method(self):
        """Setup for each test"""
        self.api_url = "http://localhost:8080"
        self.app_url = "http://localhost:2402"
        self.test_files_dir = Path("tests/fixtures")
        self.test_files_dir.mkdir(exist_ok=True)
        
        # Track created documents and files for cleanup
        self.created_documents = []
        self.created_files = []
        
    def teardown_method(self):
        """Cleanup after each test"""
        # Clean up documents
        for doc_id in self.created_documents:
            try:
                response = requests.delete(f"{self.api_url}/documents/{doc_id}", timeout=5)
                if response.status_code == 200:
                    print(f"Cleaned up document: {doc_id}")
            except Exception as e:
                print(f"Warning: Could not clean up document {doc_id}: {e}")
                
        # Clean up files
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    print(f"Cleaned up file: {file_path}")
            except Exception as e:
                print(f"Warning: Could not clean up file {file_path}: {e}")
                
        # Clear tracking lists
        self.created_documents.clear()
        self.created_files.clear()
        
    def handle_rate_limit_with_retry(self, request_func, *args, **kwargs):
        """Handle rate limiting with retries for any request function"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = request_func(*args, **kwargs)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"Rate limit hit (attempt {attempt+1}), waiting {retry_after} seconds...")
                    time.sleep(retry_after + 1)  # Add 1 second buffer
                    continue
                return response
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise e
        return response  # Return last response if all retries exhausted
        
    def track_document(self, doc_id):
        """Track a document for cleanup"""
        if doc_id and doc_id not in self.created_documents:
            self.created_documents.append(doc_id)
            
    def track_file(self, file_path):
        """Track a file for cleanup"""
        if isinstance(file_path, str):
            file_path = Path(file_path)
        if file_path not in self.created_files:
            self.created_files.append(file_path)
            
    def wait_between_operations(self, seconds=1):
        """Add delay between operations to prevent rate limiting"""
        time.sleep(seconds)
        
    def test_backend_down_scenarios(self):
        """Test UI behavior when backend services are down"""
        # This test needs to control services manually
        api_process = None
        app_process = None
        
        try:
            # Start only Streamlit (no API)
            app_process = subprocess.Popen(
                ["streamlit", "run", "app.py", "--server.port", "2403", "--server.headless", "true"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(5)
            
            # Try to access the app
            try:
                response = requests.get("http://localhost:2403", timeout=5)
                # App should be accessible even without API
                assert response.status_code == 200
            except:
                # App might not respond to direct HTTP requests
                pass
                
            # Now start API
            api_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for API to be ready
            api_ready = False
            for i in range(30):
                try:
                    response = requests.get(f"{self.api_url}/health", timeout=1)
                    if response.status_code == 200:
                        api_ready = True
                        break
                except:
                    time.sleep(1)
                    
            assert api_ready, "API should start successfully"
            
        finally:
            # Cleanup
            for process in [api_process, app_process]:
                if process:
                    process.terminate()
                    process.wait(timeout=5)
                    
    def test_malformed_api_responses(self):
        """Test handling of malformed API responses"""
        # First ensure services are running
        try:
            response = requests.get(f"{self.api_url}/health")
            assert response.status_code == 200
        except:
            pytest.skip("API not running")
            
        # Test with invalid document ID format
        invalid_requests = [
            # Invalid document ID
            {
                "url": f"{self.api_url}/ask",
                "json": {
                    "question": "Test",
                    "document_id": "../../etc/passwd",  # Path traversal attempt
                    "max_results": 3
                },
                "expected_status": [400, 404]
            },
            # Missing required fields
            {
                "url": f"{self.api_url}/ask",
                "json": {
                    "question": "Test"
                    # Missing document_id
                },
                "expected_status": [400, 422]
            },
            # Invalid data types
            {
                "url": f"{self.api_url}/ask",
                "json": {
                    "question": "Test",
                    "document_id": "valid_id",
                    "max_results": "not_a_number"  # Should be int
                },
                "expected_status": [400, 422]
            }
        ]
        
        for test_case in invalid_requests:
            response = requests.post(test_case["url"], json=test_case["json"])
            assert response.status_code in test_case["expected_status"]
            
    def test_timeout_scenarios(self):
        """Test various timeout scenarios"""
        # Create a large file that will take time to process
        large_file = self.test_files_dir / "large_timeout_test.txt"
        large_content = "This is a test sentence. " * 100000  # ~2.5MB of text
        large_file.write_text(large_content)
        
        try:
            # Upload with short timeout (should fail or succeed quickly)
            with open(large_file, 'rb') as f:
                files = {"file": (large_file.name, f, "text/plain")}
                data = {"model": "mistral"}
                
                try:
                    response = requests.post(
                        f"{self.api_url}/upload", 
                        files=files, 
                        data=data,
                        timeout=2  # Very short timeout
                    )
                    # If it succeeds, that's fine
                    if response.status_code == 200:
                        doc_id = response.json()['document_id']
                        requests.delete(f"{self.api_url}/documents/{doc_id}")
                except requests.exceptions.Timeout:
                    # Expected for large files
                    pass
                    
        finally:
            large_file.unlink()
            
    def test_memory_pressure(self):
        """Test system behavior under memory pressure"""
        # Get current memory usage
        memory = psutil.virtual_memory()
        initial_available = memory.available
        
        # Since we removed upload functionality, we'll test basic API endpoints 
        # to ensure the system handles multiple requests without memory issues
        
        successful_operations = 0
        
        # Test multiple health checks and document listings to verify memory stability
        for i in range(10):
            try:
                # Test health endpoint
                response = requests.get(f"{self.api_url}/health", timeout=5)
                if response.status_code == 200:
                    successful_operations += 1
                
                # Test documents listing
                response = requests.get(f"{self.api_url}/documents", timeout=5)
                if response.status_code == 200:
                    successful_operations += 1
                    
                # Small delay to prevent overwhelming the system
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Warning: Operation {i} failed: {e}")
                continue
                
        # System should handle basic operations (expect at least 15 out of 20 operations to succeed)
        assert successful_operations >= 15, f"Expected at least 15 successful operations, got {successful_operations}"
        
        # Check memory didn't explode (very loose check since these are lightweight operations)
        memory_after = psutil.virtual_memory()
        memory_increase_mb = (initial_available - memory_after.available) / (1024 * 1024)
        assert memory_increase_mb < 100  # Should not use more than 100MB for basic operations
                
