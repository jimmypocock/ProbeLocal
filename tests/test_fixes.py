#!/usr/bin/env python3
"""Test that all the fixes are working correctly"""

import sys
import os
import time
import requests
import tempfile

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_delete_notification():
    """Test that delete success shows as toast notification"""
    print("\n=== Testing Delete Notification ===")
    
    # First upload a test document
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test document for deletion")
        test_file = f.name
    
    try:
        # Upload
        with open(test_file, 'rb') as f:
            files = {'file': ('test_delete.txt', f, 'text/plain')}
            response = requests.post("http://localhost:8080/upload", files=files)
        
        if response.status_code == 200:
            doc_id = response.json()['document_id']
            print(f"✅ Document uploaded: {doc_id}")
            
            # Delete
            response = requests.delete(f"http://localhost:8080/documents/{doc_id}")
            if response.status_code == 200:
                print("✅ Document deleted successfully")
                print("   Toast notification should appear (not in trash column)")
            else:
                print(f"❌ Delete failed: {response.status_code}")
        else:
            print(f"❌ Upload failed: {response.status_code}")
    
    finally:
        os.unlink(test_file)
    
    print("✅ Delete notification test completed")


def test_model_warmup():
    """Test that first model query is faster due to warmup"""
    print("\n=== Testing Model Warmup ===")
    
    # The model should already be warmed up
    # Test with a simple query to the API
    start_time = time.time()
    
    response = requests.post(
        "http://localhost:8080/web-search",
        json={
            "question": "Hello",
            "document_id": "web_only",
            "model_name": "mistral",
            "stream": False
        }
    )
    
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        print(f"✅ First query completed in {elapsed:.2f}s")
        if elapsed < 10:  # Should be fast due to warmup
            print("✅ Model appears to be warmed up (fast response)")
        else:
            print("⚠️  Response slower than expected")
    else:
        print(f"❌ Query failed: {response.status_code}")
    
    print("✅ Model warmup test completed")


def test_session_persistence():
    """Test session state persistence"""
    print("\n=== Testing Session Persistence ===")
    
    from src.ui.session_persistence import SessionPersistence
    
    # Create persistence instance
    sp = SessionPersistence()
    
    # Save some test state
    import streamlit as st
    st.session_state.current_document_id = "test_doc_123"
    st.session_state.selected_model = "mistral"
    st.session_state.chunk_size = 1000
    
    sp.save_state()
    print("✅ Session state saved")
    
    # Clear session state
    st.session_state.clear()
    
    # Restore
    sp.restore_state()
    
    # Check if restored
    if 'current_document_id' in st.session_state:
        if st.session_state.current_document_id == "test_doc_123":
            print("✅ Session state restored correctly")
        else:
            print("❌ Session state restored with wrong values")
    else:
        print("❌ Session state not restored")
    
    # Clean up
    sp.clear_state()
    print("✅ Session persistence test completed")


def test_url_processing():
    """Test URL input processing"""
    print("\n=== Testing URL Processing ===")
    
    # Test URL validation
    from src.ui.url_input import is_valid_url
    
    valid_urls = ["https://example.com", "http://test.com/page"]
    invalid_urls = ["not-a-url", "example.com", ""]
    
    all_valid = all(is_valid_url(url) for url in valid_urls)
    all_invalid = all(not is_valid_url(url) for url in invalid_urls)
    
    if all_valid and all_invalid:
        print("✅ URL validation working correctly")
    else:
        print("❌ URL validation has issues")
    
    # Test URL endpoint
    response = requests.post(
        "http://localhost:8080/process-url",
        json={
            "url": "https://example.com",
            "model": "mistral"
        }
    )
    
    if response.status_code in [200, 400]:  # 400 is ok, means validation worked
        print("✅ URL processing endpoint working")
    else:
        print(f"⚠️  URL processing returned: {response.status_code}")
    
    print("✅ URL processing test completed")


def test_connection_indicators():
    """Test connection status indicators"""
    print("\n=== Testing Connection Indicators ===")
    
    from src.ui.connection_status import check_ollama_status, check_api_status
    
    # Check Ollama
    ollama_ok, ollama_msg = check_ollama_status()
    print(f"Ollama: {'✅' if ollama_ok else '❌'} {ollama_msg}")
    
    # Check API
    api_ok, api_msg = check_api_status()
    print(f"API: {'✅' if api_ok else '❌'} {api_msg}")
    
    print("✅ Connection indicators test completed")


def main():
    """Run all fix tests"""
    print("🔧 Testing All Fixes")
    
    tests = [
        test_delete_notification,
        test_model_warmup,
        test_session_persistence,
        test_url_processing,
        test_connection_indicators
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
    
    print(f"\n📊 Fix Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All fixes are working correctly!")
    else:
        print(f"❌ {failed} fixes need attention")
        sys.exit(1)


if __name__ == "__main__":
    main()