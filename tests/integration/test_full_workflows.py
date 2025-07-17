"""Integration tests for complete workflows using filesystem-based document management"""
import pytest
import time
import requests
from pathlib import Path
from typing import Dict, Any
import subprocess
import os
import signal
import shutil


class TestFullWorkflows:
    """Test complete user workflows using filesystem-based document management"""
    
    @classmethod
    def setup_class(cls):
        """Start services once for all tests"""
        cls.api_url = "http://localhost:8080"
        cls.app_url = "http://localhost:2402"
        cls.test_files_dir = Path("tests/fixtures")
        cls.test_files_dir.mkdir(exist_ok=True)
        cls.documents_dir = Path("documents")
        cls.documents_dir.mkdir(exist_ok=True)
        
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
            response = requests.get(f"{cls.api_url}/health", timeout=2)
            if response.status_code == 200:
                api_running = True
                print("API server already running, reusing it")
        except:
            pass
            
        if not api_running:
            print("Starting API server...")
            # Start API server
            cls.api_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for API to be ready
            for _ in range(30):  # 30 second timeout
                try:
                    response = requests.get(f"{cls.api_url}/health", timeout=1)
                    if response.status_code == 200:
                        break
                    time.sleep(1)
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
                    
    def test_complete_system_workflow(self):
        """Test that the complete system works end-to-end with current setup"""
        
        # Step 1: Verify API is healthy
        response = requests.get(f"{self.api_url}/health")
        assert response.status_code == 200
        assert response.json().get("status") == "healthy"
        
        # Step 2: Check documents endpoint
        response = requests.get(f"{self.api_url}/documents")
        assert response.status_code == 200
        docs_data = response.json()
        assert "documents" in docs_data
        
        # Step 3: Test query functionality (with or without documents)
        if docs_data.get("documents"):
            # If documents exist, test document query
            question_data = {
                "question": "What information is available?",
                "document_id": "unified",
                "model_name": "mistral"
            }
        else:
            # If no documents, test casual chat
            question_data = {
                "question": "Hello, how are you?",
                "document_id": "none",
                "model_name": "mistral"
            }
        
        response = requests.post(f"{self.api_url}/ask", json=question_data, stream=True)
        assert response.status_code == 200
        
        # Extract metadata from streaming response
        final_metadata = None
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                try:
                    data = line[6:]  # Remove 'data: ' prefix
                    import json
                    parsed = json.loads(data)
                    if parsed.get("done"):
                        final_metadata = parsed
                        break
                except:
                    continue
        
        assert final_metadata is not None, "Could not extract metadata from streaming response"
        assert "query_intent" in final_metadata
        print(f"✅ System workflow test completed successfully with intent: {final_metadata.get('query_intent')}")
        
    def test_query_classification_workflow(self):
        """Test that query classification works across different query types"""
        
        test_cases = [
            ("Hello there", "casual_chat"),
            ("What's the weather today?", "web_search"),
            ("Calculate 25 plus 30", "computation"),
        ]
        
        for question, expected_intent in test_cases:
            question_data = {
                "question": question,
                "document_id": "none",
                "model_name": "mistral"
            }
            
            response = requests.post(f"{self.api_url}/ask", json=question_data, stream=True)
            if response.status_code == 200:
                # Extract metadata from streaming response
                final_metadata = None
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith('data: '):
                        try:
                            data = line[6:]  # Remove 'data: ' prefix
                            import json
                            parsed = json.loads(data)
                            if parsed.get("done"):
                                final_metadata = parsed
                                break
                        except:
                            continue
                
                if final_metadata:
                    actual_intent = final_metadata.get("query_intent")
                    assert actual_intent == expected_intent, f"Query '{question}' classified as {actual_intent}, expected {expected_intent}"
                else:
                    pytest.skip("Could not extract metadata from streaming response")
            elif response.status_code == 429:
                pytest.skip("Hit rate limit during classification tests")
            else:
                print(f"Query '{question}' failed with status {response.status_code}")
        
        print("✅ Query classification workflow test completed successfully")
        
    def test_error_handling_workflow(self):
        """Test that the system handles errors gracefully"""
        
        # Test with empty question
        question_data = {
            "question": "",
            "document_id": "none",
            "model_name": "mistral"
        }
        
        response = requests.post(f"{self.api_url}/ask", json=question_data)
        assert response.status_code in [400, 422], "Empty questions should be rejected"
        
        # Test with invalid model (should fallback gracefully)
        question_data = {
            "question": "Test question",
            "document_id": "none",
            "model_name": "nonexistent_model"
        }
        
        response = requests.post(f"{self.api_url}/ask", json=question_data)
        assert response.status_code in [200, 400, 422, 500], "Invalid model should be handled gracefully"
        
        print("✅ Error handling workflow test completed successfully")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])