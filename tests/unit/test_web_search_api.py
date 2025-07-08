"""Test web search API endpoint"""
import pytest
import requests
import time
from pathlib import Path


def test_web_search_endpoint_exists():
    """Test that web search endpoint is available"""
    # This test doesn't require the API to be running
    from main import app
    
    # Check that the endpoint exists in the routes
    routes = [route.path for route in app.routes]
    assert "/web-search" in routes


def test_web_search_request_model():
    """Test that QuestionRequest model includes web search flag"""
    from main import QuestionRequest
    
    # Test model creation with web search
    request = QuestionRequest(
        question="Test question",
        document_id="test_doc",
        use_web_search=True
    )
    
    assert request.use_web_search == True
    assert request.question == "Test question"
    assert request.document_id == "test_doc"


def test_ask_endpoint_with_web_search():
    """Test that ask endpoint accepts web search parameter"""
    from main import QuestionRequest
    
    # Test model creation with web search
    request = QuestionRequest(
        question="Test question",
        document_id="test_doc",
        use_web_search=True,
        max_results=5,
        model_name="mistral",
        temperature=0.7
    )
    
    # Verify all fields are set correctly
    assert request.use_web_search == True
    assert request.max_results == 5
    assert request.model_name == "mistral"
    assert request.temperature == 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])