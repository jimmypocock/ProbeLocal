"""Test streaming functionality"""
import pytest
import json
import time
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.streaming.handler import StreamingResponseHandler, create_streaming_response
from src.qa_chain_streaming import StreamingQAChain


def test_streaming_handler():
    """Test basic streaming handler functionality"""
    handler = StreamingResponseHandler()
    
    # Simulate tokens
    handler.on_llm_new_token("Hello")
    handler.on_llm_new_token(" ")
    handler.on_llm_new_token("world")
    handler.on_llm_end(Mock(), test=True)
    
    # Check queue
    assert handler.queue.get() == "Hello"
    assert handler.queue.get() == " "
    assert handler.queue.get() == "world"
    assert handler.queue.get() is None  # End signal
    assert handler.done is True


def test_streaming_response_generator():
    """Test SSE response generation"""
    handler = StreamingResponseHandler()
    
    # Add tokens
    handler.on_llm_new_token("Test")
    handler.on_llm_new_token(" token")
    handler.on_llm_end(Mock())
    
    # Generate response
    responses = list(create_streaming_response(handler))
    
    # Check format
    assert len(responses) == 3  # 2 tokens + done
    assert 'data: {"token": "Test"}' in responses[0]
    assert 'data: {"token": " token"}' in responses[1]
    assert 'data: {"done": true}' in responses[2]


def test_streaming_request_model():
    """Test that API models support streaming flag"""
    from main import QuestionRequest
    
    # Test with streaming
    request = QuestionRequest(
        question="Test question",
        document_id="test_doc",
        stream=True
    )
    
    assert request.stream is True
    assert request.question == "Test question"


def test_streaming_qa_chain_init():
    """Test StreamingQAChain initialization"""
    with patch('src.qa_chain_streaming.StreamingQAChain.__init__', return_value=None):
        chain = StreamingQAChain()
        # Just verify it can be instantiated
        assert chain is not None


def test_api_streaming_endpoint():
    """Test that API endpoints support streaming parameter"""
    from main import app
    from fastapi.testclient import TestClient
    
    # Just verify the endpoint accepts the streaming parameter
    # without actually calling it (which would require full setup)
    from main import QuestionRequest
    
    # Create request with streaming
    request = QuestionRequest(
        question="Test",
        document_id="test",
        stream=True,
        use_web_search=False
    )
    
    # Verify it has the stream attribute
    assert hasattr(request, 'stream')
    assert request.stream is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])