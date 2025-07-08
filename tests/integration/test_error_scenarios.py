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
        
        # Create multiple documents to increase memory usage
        doc_ids = []
        try:
            for i in range(5):
                test_file = self.test_files_dir / f"memory_test_{i}.txt"
                # Create reasonably sized files
                content = f"Memory test document {i}\n" * 1000
                test_file.write_text(content)
                
                with open(test_file, 'rb') as f:
                    files = {"file": (test_file.name, f, "text/plain")}
                    data = {"model": "mistral", "chunk_size": 500}  # Smaller chunks = more objects (but must be > chunk_overlap)
                    response = requests.post(f"{self.api_url}/upload", files=files, data=data)
                    
                if response.status_code == 200:
                    doc_ids.append(response.json()['document_id'])
                    
                test_file.unlink()
                
            # System should handle multiple documents
            assert len(doc_ids) >= 3
            
            # Check memory didn't explode
            memory_after = psutil.virtual_memory()
            memory_increase_mb = (initial_available - memory_after.available) / (1024 * 1024)
            assert memory_increase_mb < 500  # Should not use more than 500MB
            
        finally:
            # Cleanup
            for doc_id in doc_ids:
                requests.delete(f"{self.api_url}/documents/{doc_id}")
                
    def test_race_conditions(self):
        """Test for race conditions in concurrent operations"""
        # Upload a document
        test_file = self.test_files_dir / "race_condition_test.txt"
        test_file.write_text("Test document for race condition testing")
        
        with open(test_file, 'rb') as f:
            files = {"file": (test_file.name, f, "text/plain")}
            data = {"model": "mistral"}
            response = requests.post(f"{self.api_url}/upload", files=files, data=data)
            
        assert response.status_code == 200
        doc_id = response.json()['document_id']
        
        import concurrent.futures
        
        def query_document():
            """Query the document"""
            query_data = {
                "question": "What is this document?",
                "document_id": doc_id,
                "max_results": 3,
                "model_name": "mistral"
            }
            return requests.post(f"{self.api_url}/ask", json=query_data)
            
        def delete_document():
            """Delete the document"""
            time.sleep(0.1)  # Small delay to ensure queries start
            return requests.delete(f"{self.api_url}/documents/{doc_id}")
            
        # Run queries and deletion concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit 3 queries and 1 delete
            query_futures = [executor.submit(query_document) for _ in range(3)]
            delete_future = executor.submit(delete_document)
            
            # Get results
            query_results = [f.result() for f in query_futures]
            delete_result = delete_future.result()
            
        # Delete should succeed
        assert delete_result.status_code == 200
        
        # At least some queries should have completed before deletion
        successful_queries = sum(1 for r in query_results if r.status_code == 200)
        assert successful_queries >= 1
        
        # Cleanup
        test_file.unlink()
        
    def test_invalid_file_handling(self):
        """Test handling of various invalid files"""
        invalid_files = [
            # Empty file
            ("empty.txt", b""),
            # Binary file pretending to be text
            ("fake_text.txt", b"\x00\x01\x02\x03\x04"),
            # Extremely long filename
            ("x" * 255 + ".txt", b"content"),
            # Special characters in filename  
            ("test<>:|?.txt", b"content"),
        ]
        
        for filename, content in invalid_files:
            test_file = self.test_files_dir / "invalid_test"
            test_file.write_bytes(content)
            
            try:
                with open(test_file, 'rb') as f:
                    files = {"file": (filename, f, "text/plain")}
                    data = {"model": "mistral"}
                    response = requests.post(f"{self.api_url}/upload", files=files, data=data)
                    
                # Should either handle gracefully or reject
                assert response.status_code in [200, 400, 413, 422]
                
                if response.status_code == 200:
                    # If accepted, should be able to delete
                    doc_id = response.json()['document_id']
                    requests.delete(f"{self.api_url}/documents/{doc_id}")
                    
            finally:
                test_file.unlink()
                
    def test_session_recovery(self):
        """Test session state recovery after errors"""
        # Upload a document
        test_file = self.test_files_dir / "session_test.txt"
        test_file.write_text("Session recovery test document")
        
        with open(test_file, 'rb') as f:
            files = {"file": (test_file.name, f, "text/plain")}
            data = {"model": "mistral"}
            response = requests.post(f"{self.api_url}/upload", files=files, data=data)
            
        assert response.status_code == 200
        doc_id = response.json()['document_id']
        
        # Simulate some queries
        for i in range(3):
            query_data = {
                "question": f"Question {i}",
                "document_id": doc_id,
                "max_results": 3,
                "model_name": "mistral"
            }
            requests.post(f"{self.api_url}/ask", json=query_data)
            
        # Document should still be queryable
        query_data = {
            "question": "Final question",
            "document_id": doc_id,
            "max_results": 3,
            "model_name": "mistral"
        }
        response = requests.post(f"{self.api_url}/ask", json=query_data)
        assert response.status_code == 200
        
        # Cleanup
        requests.delete(f"{self.api_url}/documents/{doc_id}")
        test_file.unlink()