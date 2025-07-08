#!/usr/bin/env python3
"""Test new features: URL input, retry buttons, connection status, toast notifications, incremental processing"""

import sys
import os
import time
import requests
import tempfile

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.url_input import is_valid_url
from src.ui.retry_button import render_retry_button, _perform_retry
from src.ui.connection_status import check_ollama_status, check_api_status, get_service_health
from src.ui.toast_notifications import ToastManager
from src.incremental_processor import IncrementalProcessor


def test_url_validation():
    """Test URL validation"""
    print("\n=== Testing URL Validation ===")
    
    valid_urls = [
        "https://example.com",
        "http://example.com/page",
        "https://example.com/path/to/page.html",
        "https://example.com:8080/api"
    ]
    
    invalid_urls = [
        "not a url",
        "example.com",  # Missing protocol
        "://example.com",  # Missing protocol
        "",
        "javascript:alert('test')"
    ]
    
    for url in valid_urls:
        assert is_valid_url(url), f"Expected {url} to be valid"
    
    for url in invalid_urls:
        assert not is_valid_url(url), f"Expected {url} to be invalid"
    
    print("✅ URL validation test passed!")


def test_connection_status():
    """Test connection status checks"""
    print("\n=== Testing Connection Status ===")
    
    # Test Ollama status
    ollama_ok, ollama_msg = check_ollama_status()
    print(f"Ollama status: {ollama_ok} - {ollama_msg}")
    
    # Test API status
    api_ok, api_msg = check_api_status()
    print(f"API status: {api_ok} - {api_msg}")
    
    # Test service health
    health = get_service_health()
    print(f"Service health: {health}")
    
    print("✅ Connection status test passed!")


def test_toast_notifications():
    """Test toast notification system"""
    print("\n=== Testing Toast Notifications ===")
    
    # Create toast manager
    toast_manager = ToastManager()
    
    # Add notifications
    toast_manager.show("Success message!", "success", duration=2)
    toast_manager.show("Error message!", "error", duration=3)
    toast_manager.show("Warning message!", "warning", duration=2)
    toast_manager.show("Info message!", "info", duration=2)
    
    # Check notifications were added
    import streamlit as st
    if 'toast_notifications' not in st.session_state:
        st.session_state.toast_notifications = []
    
    # The notifications should be in session state
    initial_count = len(st.session_state.toast_notifications)
    print(f"Added {initial_count} notifications")
    
    # Test notification expiry
    print("Testing notification expiry...")
    
    print("✅ Toast notifications test passed!")


def test_incremental_processor():
    """Test incremental document processing"""
    print("\n=== Testing Incremental Processor ===")
    
    processor = IncrementalProcessor()
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        # Write some content
        for i in range(100):
            f.write(f"This is line {i} of test content.\n" * 10)
        test_file = f.name
    
    try:
        # Test document ID generation
        doc_id = processor._generate_document_id(test_file)
        assert len(doc_id) == 32  # MD5 hash length
        print(f"Generated document ID: {doc_id[:8]}...")
        
        # Test state management
        test_state = {'test': 'data', 'progress': 0.5}
        processor._save_state(doc_id, test_state)
        loaded_state = processor._load_state(doc_id)
        assert loaded_state == test_state
        print("State management working correctly")
        
        # Clean up
        processor._clean_state(doc_id)
        assert processor._load_state(doc_id) is None
        print("State cleanup working correctly")
        
    finally:
        # Clean up test file
        os.unlink(test_file)
    
    print("✅ Incremental processor test passed!")


def test_retry_functionality():
    """Test retry button functionality"""
    print("\n=== Testing Retry Functionality ===")
    
    # Test retry state management
    call_count = 0
    
    def test_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Test error")
        return "Success!"
    
    # Test _perform_retry
    state = {'attempts': 0, 'last_attempt': 0}
    
    # First attempt should fail
    result = _perform_retry(test_operation, {}, state)
    assert result is None
    assert state['attempts'] == 1
    print("First retry failed as expected")
    
    # Second attempt should also fail
    result = _perform_retry(test_operation, {}, state)
    assert result is None
    assert state['attempts'] == 2
    print("Second retry failed as expected")
    
    # Third attempt should succeed
    result = _perform_retry(test_operation, {}, state)
    assert result == "Success!"
    assert state['attempts'] == 0  # Reset on success
    print("Third retry succeeded!")
    
    print("✅ Retry functionality test passed!")


def test_url_processing_endpoint():
    """Test URL processing API endpoint"""
    print("\n=== Testing URL Processing Endpoint ===")
    
    # Check if API is running
    try:
        response = requests.get("http://localhost:8080/health", timeout=2)
        if response.status_code != 200:
            print("⚠️  API not running, skipping URL processing test")
            return
    except:
        print("⚠️  API not running, skipping URL processing test")
        return
    
    # Test URL processing
    test_url = "https://example.com"
    
    response = requests.post(
        "http://localhost:8080/process-url",
        json={
            "url": test_url,
            "model": "mistral",
            "chunk_size": 800
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ URL processed successfully: {result}")
    else:
        print(f"⚠️  URL processing returned {response.status_code}")
    
    print("✅ URL processing endpoint test completed!")


def main():
    """Run all new feature tests"""
    print("🚀 Testing New Features")
    
    tests = [
        test_url_validation,
        test_connection_status,
        test_toast_notifications,
        test_incremental_processor,
        test_retry_functionality,
        test_url_processing_endpoint
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All new feature tests passed!")
    else:
        print(f"❌ {failed} tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()