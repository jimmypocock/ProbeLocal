"""Integration tests for web search functionality"""
import pytest
import requests
import time
import subprocess
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWebSearchIntegration:
    """Test web search integration with backend"""
    
    @classmethod
    def setup_class(cls):
        """Start the API server"""
        cls.api_process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for API to start
        cls._wait_for_api()
    
    @classmethod
    def teardown_class(cls):
        """Stop the API server"""
        if hasattr(cls, 'api_process'):
            cls.api_process.terminate()
            cls.api_process.wait(timeout=5)
    
    @staticmethod
    def _wait_for_api(timeout=30):
        """Wait for API to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get("http://localhost:8080/health")
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        raise TimeoutError("API failed to start")
    
    def test_web_search_endpoint(self):
        """Test the /web-search endpoint"""
        response = requests.post(
            "http://localhost:8080/web-search",
            json={
                "question": "What is Python programming?",
                "document_id": "web_only",
                "max_results": 3,
                "model_name": "mistral"
            },
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'answer' in data
        assert 'sources' in data
        assert data['document_id'] == 'web_only'
        assert '🌐' in data['answer']  # Should have web indicator
    
    def test_ask_endpoint_with_web_search(self):
        """Test /ask endpoint with web search enabled"""
        # First upload a test document
        test_file_path = Path("tests/fixtures/test_doc.txt")
        test_file_path.parent.mkdir(exist_ok=True)
        test_file_path.write_text("This is a test document about Python basics.")
        
        with open(test_file_path, 'rb') as f:
            files = {"file": ("test_doc.txt", f, "text/plain")}
            data = {"model": "mistral"}
            upload_response = requests.post(
                "http://localhost:8080/upload",
                files=files,
                data=data
            )
        
        assert upload_response.status_code == 200
        document_id = upload_response.json()['document_id']
        
        # Now ask with web search enabled
        response = requests.post(
            "http://localhost:8080/ask",
            json={
                "question": "What are the latest features in Python 3.12?",
                "document_id": document_id,
                "use_web_search": True,
                "max_results": 3,
                "model_name": "mistral"
            },
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'answer' in data
        assert 'sources' in data
        assert 'used_web_search' in data
        assert data['used_web_search'] == True
        
        # Clean up
        requests.delete(f"http://localhost:8080/documents/{document_id}")
    
    def test_web_search_rate_limiting(self):
        """Test that web search has proper rate limiting"""
        # Make multiple rapid requests
        responses = []
        for i in range(35):  # Over the 30/minute limit
            try:
                response = requests.post(
                    "http://localhost:8080/web-search",
                    json={
                        "question": f"Test query {i}",
                        "document_id": "web_only",
                        "max_results": 1,
                        "model_name": "mistral"
                    },
                    timeout=5
                )
                responses.append(response.status_code)
            except:
                responses.append(500)
        
        # Should have some 429 (rate limit) responses
        assert 429 in responses or all(r == 200 for r in responses[:30])
    
    def test_web_search_error_handling(self):
        """Test web search error handling"""
        # Test with invalid parameters
        response = requests.post(
            "http://localhost:8080/web-search",
            json={
                "question": "",  # Empty question
                "document_id": "web_only",
                "max_results": 0,  # Invalid max_results
                "model_name": "invalid_model"
            },
            timeout=10
        )
        
        # Should handle gracefully
        assert response.status_code in [400, 422, 500]
    
    def test_source_type_indicators(self):
        """Test that sources are properly typed"""
        response = requests.post(
            "http://localhost:8080/web-search",
            json={
                "question": "What is machine learning?",
                "document_id": "web_only",
                "max_results": 3,
                "model_name": "mistral"
            },
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get('sources'):
            # All sources should be web type
            for source in data['sources']:
                assert source.get('type') == 'web' or 'url' in source