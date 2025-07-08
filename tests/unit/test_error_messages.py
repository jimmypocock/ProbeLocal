"""Test error message specificity"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.error_messages import ErrorMessages


def test_ollama_connection_error():
    """Test Ollama connection error message"""
    error = ConnectionRefusedError("Connection refused on port 11434")
    message = ErrorMessages.get_specific_error(error, {})
    
    assert "Ollama Service Not Running" in message
    assert "ollama serve" in message
    assert "ollama pull mistral" in message


def test_model_422_error():
    """Test model configuration error message"""
    error = Exception("422 Unprocessable Entity")
    context = {'model_name': 'deepseek'}
    message = ErrorMessages.get_specific_error(error, context)
    
    assert "Model Configuration Error" in message
    assert "deepseek" in message
    assert "test_models.py" in message


def test_file_too_large_error():
    """Test file size error message"""
    error = Exception("File too large")
    context = {'max_size': 50}
    message = ErrorMessages.get_specific_error(error, context)
    
    assert "File Too Large" in message
    assert "50MB" in message
    assert "Compressing the file" in message


def test_unsupported_file_error():
    """Test unsupported file type error"""
    error = Exception("Unsupported file type")
    context = {'file_type': '.xyz'}
    message = ErrorMessages.get_specific_error(error, context)
    
    assert "Unsupported File Type" in message
    assert ".xyz" in message
    assert "PDF, TXT, MD" in message


def test_document_not_found_error():
    """Test document not found error"""
    error = Exception("404 Document not found")
    message = ErrorMessages.get_specific_error(error, {})
    
    assert "Document Not Found" in message
    assert "deleted or expired" in message


def test_rate_limit_error():
    """Test rate limit error message"""
    error = Exception("429 Rate limit exceeded")
    message = ErrorMessages.get_specific_error(error, {})
    
    assert "Rate Limit Exceeded" in message
    assert "60/minute" in message
    assert "wait a moment" in message


def test_timeout_error():
    """Test timeout error message"""
    error = Exception("Request timed out")
    message = ErrorMessages.get_specific_error(error, {})
    
    assert "Model Response Timeout" in message
    assert "simpler question" in message
    assert "first query" in message


def test_memory_error():
    """Test memory error message"""
    error = Exception("Out of memory")
    message = ErrorMessages.get_specific_error(error, {})
    
    assert "Out of Memory" in message
    assert "memory usage:" in message.lower()
    assert "smaller documents" in message


def test_web_search_error():
    """Test web search error message"""
    error = Exception("DuckDuckGo search failed")
    message = ErrorMessages.get_specific_error(error, {})
    
    assert "Web Search Failed" in message
    assert "Network connection" in message
    assert "disable web search" in message


def test_generic_error_fallback():
    """Test generic error fallback message"""
    error = ValueError("Some random error")
    message = ErrorMessages.get_specific_error(error, {})
    
    assert "ValueError" in message
    assert "Some random error" in message
    assert "check:" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])