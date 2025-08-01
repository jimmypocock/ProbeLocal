"""Integration tests for complete user workflows"""
import pytest
import time
import requests
from pathlib import Path
from typing import Dict, Any
import subprocess
import os
import signal


class TestFullWorkflows:
    """Test complete user workflows from upload to query to delete"""
    
    @classmethod
    def setup_class(cls):
        """Start services once for all tests"""
        cls.api_url = "http://localhost:8080"
        cls.app_url = "http://localhost:2402"
        cls.test_files_dir = Path("tests/fixtures")
        cls.test_files_dir.mkdir(exist_ok=True)
        
        # Start services
        cls.api_process = None
        cls.app_process = None
        cls._start_services()
        
    def handle_rate_limit(self, response, operation_name="operation"):
        """Handle rate limit errors with exponential backoff"""
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"\nRate limit hit for {operation_name}, waiting {retry_after} seconds...")
            time.sleep(retry_after + 1)  # Add 1 second buffer
            return True
        return False
        
    def wait_between_operations(self, seconds=2):
        """Add delay between operations to prevent rate limiting"""
        time.sleep(seconds)
        
    @classmethod
    def teardown_class(cls):
        """Stop services after all tests"""
        cls._stop_services()
        
    @classmethod
    def _start_services(cls):
        """Start API and Streamlit services if not already running"""
        # Check if API is already running
        api_running = False
        try:
            response = requests.get(f"{cls.api_url}/health", timeout=1)
            if response.status_code == 200:
                api_running = True
                print("API server already running, reusing it")
        except:
            pass
            
        if not api_running:
            # Start API
            cls.api_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for API to be ready
            for i in range(30):
                try:
                    response = requests.get(f"{cls.api_url}/health", timeout=1)
                    if response.status_code == 200:
                        break
                except:
                    time.sleep(1)
            else:
                raise TimeoutError("API server failed to start")
                
        # Check if Streamlit is already running  
        app_running = False
        try:
            response = requests.get(cls.app_url, timeout=1)
            app_running = True
            print("Streamlit app already running, reusing it")
        except:
            pass
            
        if not app_running:
            # Start Streamlit
            cls.app_process = subprocess.Popen(
                ["streamlit", "run", "app.py", "--server.port", "2402", "--server.headless", "true"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Give Streamlit time to start
            time.sleep(5)
        
    @classmethod
    def _stop_services(cls):
        """Stop services that were started by this test"""
        for process in [cls.api_process, cls.app_process]:
            if process:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
                except:
                    try:
                        process.kill()
                    except:
                        pass  # Process might already be dead
                    
    def test_complete_document_lifecycle(self):
        """Test upload → process → query → delete workflow"""
        # Step 1: Upload document
        test_file = self.test_files_dir / "lifecycle_test.txt"
        test_file.write_text("""
        Integration Test Document
        
        This document contains information about integration testing.
        Key concepts include:
        - End-to-end testing
        - System integration
        - Workflow validation
        - User journey testing
        
        Integration tests verify that different components work together correctly.
        """)
        
        # Upload with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            with open(test_file, 'rb') as f:
                files = {"file": ("lifecycle_test.txt", f, "text/plain")}
                data = {"model": "mistral", "chunk_size": 500, "temperature": 0.7}
                response = requests.post(f"{self.api_url}/upload", files=files, data=data)
                
            if response.status_code == 200:
                break
            elif self.handle_rate_limit(response, f"upload (attempt {attempt+1})"):
                continue
            else:
                assert False, f"Upload failed: {response.status_code} - {response.text}"
                
        upload_result = response.json()
        doc_id = upload_result['document_id']
        assert doc_id is not None
        
        # Wait between operations
        self.wait_between_operations()
        
        # Step 2: Verify document appears in list
        response = requests.get(f"{self.api_url}/documents")
        assert response.status_code == 200
        docs = response.json()['documents']
        doc_ids = [d['document_id'] for d in docs]
        assert doc_id in doc_ids
        
        # Step 3: Query the document
        query_data = {
            "question": "What are the key concepts of integration testing?",
            "document_id": doc_id,
            "max_results": 5,
            "model_name": "mistral",
            "temperature": 0.7
        }
        response = requests.post(f"{self.api_url}/ask", json=query_data)
        assert response.status_code == 200
        
        answer = response.json()
        assert 'answer' in answer
        assert 'End-to-end testing' in answer['answer'] or 'integration' in answer['answer'].lower()
        assert 'sources' in answer
        
        # Step 4: Delete the document
        response = requests.delete(f"{self.api_url}/documents/{doc_id}")
        assert response.status_code == 200
        
        # Step 5: Verify document is gone
        response = requests.get(f"{self.api_url}/documents")
        docs = response.json()['documents']
        doc_ids = [d['document_id'] for d in docs]
        assert doc_id not in doc_ids
        
        # Step 6: Verify querying deleted document fails
        response = requests.post(f"{self.api_url}/ask", json=query_data)
        assert response.status_code == 404
        
    def test_multiple_documents_workflow(self):
        """Test working with multiple documents"""
        doc_ids = []
        
        # Upload multiple documents with spacing
        for i in range(3):
            test_file = self.test_files_dir / f"multi_doc_{i}.txt"
            test_file.write_text(f"Document {i}: This is test document number {i}.")
            
            # Upload with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                with open(test_file, 'rb') as f:
                    files = {"file": (test_file.name, f, "text/plain")}
                    data = {"model": "mistral"}
                    response = requests.post(f"{self.api_url}/upload", files=files, data=data)
                    
                if response.status_code == 200:
                    break
                elif self.handle_rate_limit(response, f"upload doc {i} (attempt {attempt+1})"):
                    continue
                else:
                    assert False, f"Upload failed: {response.status_code} - {response.text}"
                    
            doc_ids.append(response.json()['document_id'])
            
            # Wait between uploads to avoid rate limiting
            self.wait_between_operations(3)
            
        # Query each document with spacing
        for i, doc_id in enumerate(doc_ids):
            query_data = {
                "question": "What document number is this?",
                "document_id": doc_id,
                "max_results": 3,
                "model_name": "mistral"
            }
            
            # Query with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                response = requests.post(f"{self.api_url}/ask", json=query_data)
                
                if response.status_code == 200:
                    break
                elif self.handle_rate_limit(response, f"query doc {i} (attempt {attempt+1})"):
                    continue
                else:
                    assert False, f"Query failed: {response.status_code} - {response.text}"
                    
            answer = response.json()['answer']
            assert f"{i}" in answer or f"number {i}" in answer.lower()
            
            # Wait between queries
            self.wait_between_operations(1)
            
        # Clean up
        for doc_id in doc_ids:
            requests.delete(f"{self.api_url}/documents/{doc_id}")
            
    def test_different_file_formats_workflow(self):
        """Test workflow with different file formats"""
        test_formats = {
            "test.txt": "Plain text content for testing.",
            "test.md": "# Markdown Test\n\nThis is **markdown** content.",
            "test.csv": "Name,Value\nTest,123\nDemo,456"
        }
        
        for filename, content in test_formats.items():
            # Upload
            test_file = self.test_files_dir / filename
            test_file.write_text(content)
            
            with open(test_file, 'rb') as f:
                files = {"file": (filename, f, "application/octet-stream")}
                data = {"model": "mistral"}
                response = requests.post(f"{self.api_url}/upload", files=files, data=data)
                
            assert response.status_code == 200
            doc_id = response.json()['document_id']
            
            # Query
            query_data = {
                "question": "What type of content is this?",
                "document_id": doc_id,
                "max_results": 3,
                "model_name": "mistral"
            }
            response = requests.post(f"{self.api_url}/ask", json=query_data)
            assert response.status_code == 200
            
            # Cleanup
            requests.delete(f"{self.api_url}/documents/{doc_id}")
            test_file.unlink()
            
    def test_concurrent_workflow(self):
        """Test concurrent operations"""
        import concurrent.futures
        
        def process_document(doc_num):
            """Upload, query, and delete a document"""
            # Upload
            test_file = self.test_files_dir / f"concurrent_{doc_num}.txt"
            test_file.write_text(f"Concurrent test document {doc_num}")
            
            with open(test_file, 'rb') as f:
                files = {"file": (test_file.name, f, "text/plain")}
                data = {"model": "mistral"}
                response = requests.post(f"{self.api_url}/upload", files=files, data=data)
                
            if response.status_code != 200:
                return False
                
            doc_id = response.json()['document_id']
            
            # Query
            query_data = {
                "question": "What document is this?",
                "document_id": doc_id,
                "max_results": 3,
                "model_name": "mistral"
            }
            response = requests.post(f"{self.api_url}/ask", json=query_data)
            
            # Cleanup
            requests.delete(f"{self.api_url}/documents/{doc_id}")
            test_file.unlink()
            
            return response.status_code == 200
            
        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_document, i) for i in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
        # At least 2 should succeed
        assert sum(results) >= 2
        
    def test_model_switching_workflow(self):
        """Test switching models during a session"""
        # Upload document
        test_file = self.test_files_dir / "model_switch_test.txt"
        test_file.write_text("This is a test for model switching functionality.")
        
        # Upload with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            with open(test_file, 'rb') as f:
                files = {"file": (test_file.name, f, "text/plain")}
                data = {"model": "mistral"}
                response = requests.post(f"{self.api_url}/upload", files=files, data=data)
                
            if response.status_code == 200:
                break
            elif self.handle_rate_limit(response, f"upload (attempt {attempt+1})"):
                continue
            else:
                assert False, f"Upload failed: {response.status_code} - {response.text}"
                
        doc_id = response.json()['document_id']
        
        # Wait between operations
        self.wait_between_operations()
        
        # Get available models
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            all_models = [m['name'] for m in response.json().get('models', [])]
            # Filter to only models that are allowed by the API
            # The API has a whitelist of allowed models - must match exactly
            allowed_models = {
                'mistral', 'mistral:latest',
                'llama2', 'llama2:latest', 'llama2:7b', 'llama2:13b',
                'llama3', 'llama3:latest', 'llama3:8b', 'llama3:70b',
                'phi', 'phi:latest', 'phi3', 'phi3:latest',
                'deepseek-coder', 'deepseek-coder:latest',
                'neural-chat', 'neural-chat:latest',
                'dolphin-mistral', 'dolphin-mistral:latest',
                'mixtral', 'mixtral:latest'
            }
            
            # Only use models that are in both Ollama and allowed list
            models = [m for m in all_models if m.lower() in allowed_models]
            
            if not models:
                models = ["mistral"]
        else:
            models = ["mistral"]
            
        # Query with different models
        for i, model in enumerate(models[:2]):  # Test first 2 models
            query_data = {
                "question": "What is this document about?",
                "document_id": doc_id,
                "max_results": 3,
                "model_name": model,
                "temperature": 0.7
            }
            
            # Query with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                response = requests.post(f"{self.api_url}/ask", json=query_data)
                
                if response.status_code == 200:
                    break
                elif self.handle_rate_limit(response, f"query with {model} (attempt {attempt+1})"):
                    continue
                else:
                    assert False, f"Query failed: {response.status_code} - {response.text}"
                    
            # Wait between model switches
            if i < len(models[:2]) - 1:
                self.wait_between_operations(2)
            
        # Cleanup
        requests.delete(f"{self.api_url}/documents/{doc_id}")
        test_file.unlink()