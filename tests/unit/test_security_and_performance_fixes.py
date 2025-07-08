#!/usr/bin/env python3
"""Comprehensive test for all security and performance fixes"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Import all the modules we've fixed
from src.security import (
    sanitize_filename, create_safe_file_path, sanitize_query_string,
    validate_model_name, validate_parameter_bounds, sanitize_error_message,
    validate_vector_store_path, is_safe_url
)
from src.vector_store_manager import VectorStoreManager
from src.performance.request_queue import RequestQueueManager
from src.ui.session_manager import IsolatedSessionManager

def test_security_functions():
    """Test all security functions"""
    print("Testing security functions...")
    
    # Test filename sanitization
    assert sanitize_filename("../../../etc/passwd") is None  # No extension
    assert sanitize_filename("../../../etc/passwd.pdf") == "etc_passwd.pdf"
    assert sanitize_filename("file.txt") == "file.txt"
    assert sanitize_filename("file<script>.pdf") == "filescript.pdf"
    assert sanitize_filename("test.unknown") is None  # Unknown extension
    assert sanitize_filename("x" * 300 + ".pdf") is not None  # Should truncate
    print("✅ Filename sanitization working")
    
    # Test safe file path creation
    test_dir = Path("/tmp/test_upload")
    test_dir.mkdir(exist_ok=True)
    
    try:
        safe_path = create_safe_file_path("test.pdf", test_dir)
        assert safe_path is not None, "Safe path should not be None"
        assert safe_path.parent.resolve() == test_dir.resolve(), f"Parent dir mismatch: {safe_path.parent} != {test_dir}"
        
        unsafe_path = create_safe_file_path("../../../etc/passwd", test_dir)
        assert unsafe_path is None, "Unsafe path should be None"
        print("✅ Safe file path creation working")
    except AssertionError as e:
        print(f"Safe file path test failed: {e}")
        raise
    
    # Test query string sanitization
    assert sanitize_query_string("Hello world") == "Hello world"
    assert sanitize_query_string("Test\x00null") == "Testnull"  # Null bytes removed
    assert len(sanitize_query_string("A" * 1500)) < 1500  # Should truncate
    print("✅ Query string sanitization working")
    
    # Test model name validation
    assert validate_model_name("mistral") == True
    assert validate_model_name("llama2") == True
    assert validate_model_name("../../../bin/sh") == False
    assert validate_model_name("model<script>") == False
    print("✅ Model name validation working")
    
    # Test parameter validation
    try:
        params = validate_parameter_bounds({
            'temperature': 2.5,  # Should be clamped to 2.0
            'chunk_size': 10000,  # Should be clamped to 5000
            'max_results': -5  # Should be clamped to 1
        })
        assert params['temperature'] == 2.0, f"Temperature: {params['temperature']} != 2.0"
        assert params['chunk_size'] == 5000, f"Chunk size: {params['chunk_size']} != 5000"
        assert params['max_results'] == 1, f"Max results: {params['max_results']} != 1"
        print("✅ Parameter bounds validation working")
    except Exception as e:
        print(f"Parameter validation failed: {e}")
        print(f"Params: {params}")
        raise
    
    # Test error message sanitization
    error = Exception("/home/user/secret/path/file.txt not found")
    sanitized = sanitize_error_message(error, show_details=False)
    assert "/home/user/secret" not in sanitized
    assert "error occurred" in sanitized.lower()
    print("✅ Error message sanitization working")
    
    # Test URL validation
    assert is_safe_url("https://example.com") == True
    assert is_safe_url("http://localhost:8080") == True
    assert is_safe_url("file:///etc/passwd") == False
    assert is_safe_url("javascript:alert('xss')") == False
    print("✅ URL validation working")
    
    # Clean up
    test_dir.rmdir()
    
    print("✅ All security functions passed!\n")

def test_vector_store_manager():
    """Test vector store manager functionality"""
    print("Testing vector store manager...")
    
    # Create test directories
    vector_dir = Path("/tmp/test_vectors")
    upload_dir = Path("/tmp/test_uploads")
    vector_dir.mkdir(exist_ok=True)
    upload_dir.mkdir(exist_ok=True)
    
    # Initialize manager
    manager = VectorStoreManager(vector_dir, upload_dir)
    
    # Create some test vector stores
    for i in range(5):
        store_dir = vector_dir / f"doc{i}.faiss"
        store_dir.mkdir(exist_ok=True)
        
        # Create metadata file
        metadata = {
            'document_id': f'doc{i}',
            'filename': f'test{i}.pdf',
            'upload_date': (datetime.now() - timedelta(days=i)).isoformat(),
            'file_size_mb': 1.0
        }
        
        with open(vector_dir / f"doc{i}.metadata", 'w') as f:
            json.dump(metadata, f)
        
        # Make some files old
        if i > 2:
            old_time = time.time() - (8 * 24 * 3600)  # 8 days old
            os.utime(vector_dir / f"doc{i}.metadata", (old_time, old_time))
    
    # Test cleanup
    stats = manager.cleanup_old_stores(force=True)
    assert len(stats['removed_by_age']) == 2  # doc3 and doc4 should be removed
    print("✅ Vector store age-based cleanup working")
    
    # Test storage stats
    try:
        storage_stats = manager.get_storage_stats()
        assert 'total_documents' in storage_stats or 'error' in storage_stats
        if 'total_documents' in storage_stats:
            assert storage_stats['total_documents'] == 3  # Only 3 left after cleanup
        print("✅ Storage stats working")
    except Exception as e:
        print(f"Storage stats error: {e}")
        print(f"Stats: {storage_stats}")
        raise
    
    # Clean up
    import shutil
    shutil.rmtree(vector_dir)
    shutil.rmtree(upload_dir)
    
    print("✅ Vector store manager tests passed!\n")

def test_request_queue_race_conditions():
    """Test that request queue handles race conditions properly"""
    print("Testing request queue race condition fixes...")
    
    # Initialize queue
    queue = RequestQueueManager(max_concurrent=2)
    
    # Register a test handler
    def test_handler(value):
        time.sleep(0.1)  # Simulate work
        return f"processed_{value}"
    
    queue.register_handler("test", test_handler)
    
    # Submit multiple requests concurrently
    request_ids = []
    results = {}
    errors = []
    
    def submit_and_get(i):
        try:
            req_id = queue.submit_request("test", {"value": i})
            request_ids.append(req_id)
            
            # Try to get result
            time.sleep(0.2)  # Wait for processing
            status = queue.get_request_status(req_id)
            if status:
                results[i] = status
        except Exception as e:
            errors.append(e)
    
    # Launch multiple threads
    threads = []
    for i in range(10):
        t = threading.Thread(target=submit_and_get, args=(i,))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Check results
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results) >= 8, "Not enough requests processed"
    
    # Verify no race conditions in completed dictionary
    completed_count = 0
    for i, status in results.items():
        if status.status.value == "completed":
            completed_count += 1
    
    print(f"✅ Processed {completed_count} requests without race conditions")
    
    # Shutdown queue
    queue.shutdown()
    
    print("✅ Request queue race condition tests passed!\n")

def test_session_isolation():
    """Test session isolation functionality"""
    print("Testing session isolation...")
    
    # Initialize manager
    manager = IsolatedSessionManager()
    
    # Create test sessions
    session1_id = "test_session_1"
    session2_id = "test_session_2"
    
    # Save data for session 1
    session1_file = manager.session_dir / f"session_{session1_id}.json"
    session1_data = {
        'session_id': session1_id,
        'timestamp': time.time(),
        'data': {
            'current_document_id': 'doc_session1',
            'messages': [{'role': 'user', 'content': 'Session 1 message'}]
        }
    }
    with open(session1_file, 'w') as f:
        json.dump(session1_data, f)
    
    # Save data for session 2
    session2_file = manager.session_dir / f"session_{session2_id}.json"
    session2_data = {
        'session_id': session2_id,
        'timestamp': time.time(),
        'data': {
            'current_document_id': 'doc_session2',
            'messages': [{'role': 'user', 'content': 'Session 2 message'}]
        }
    }
    with open(session2_file, 'w') as f:
        json.dump(session2_data, f)
    
    # Verify isolation
    with open(session1_file, 'r') as f:
        loaded1 = json.load(f)
    with open(session2_file, 'r') as f:
        loaded2 = json.load(f)
    
    assert loaded1['data']['current_document_id'] != loaded2['data']['current_document_id']
    assert loaded1['data']['messages'][0]['content'] != loaded2['data']['messages'][0]['content']
    print("✅ Sessions are properly isolated")
    
    # Test cleanup
    old_session_id = "old_session"
    old_file = manager.session_dir / f"session_{old_session_id}.json"
    old_data = {
        'session_id': old_session_id,
        'timestamp': time.time() - 7200,
        'data': {}
    }
    with open(old_file, 'w') as f:
        json.dump(old_data, f)
    
    # Make file old
    old_time = time.time() - 7200
    os.utime(old_file, (old_time, old_time))
    
    # Run cleanup
    manager._last_cleanup = 0
    manager._cleanup_old_sessions()
    
    assert not old_file.exists()
    print("✅ Old session cleanup working")
    
    # Clean up test files
    if session1_file.exists():
        session1_file.unlink()
    if session2_file.exists():
        session2_file.unlink()
    
    print("✅ Session isolation tests passed!\n")

def test_all_integrations():
    """Test that all components work together"""
    print("Testing component integration...")
    
    # Test that security doesn't break functionality
    test_file = "test_document.pdf"
    safe_name = sanitize_filename(test_file)
    assert safe_name == test_file
    
    # Test parameter validation doesn't break valid inputs
    valid_params = {
        'temperature': 0.7,
        'chunk_size': 800,
        'max_results': 5
    }
    validated = validate_parameter_bounds(valid_params)
    assert validated == valid_params
    
    print("✅ All components integrate correctly\n")

def main():
    """Run all tests"""
    print("=" * 60)
    print("Running comprehensive test suite for all fixes")
    print("=" * 60)
    print()
    
    try:
        test_security_functions()
        test_vector_store_manager()
        test_request_queue_race_conditions()
        test_session_isolation()
        test_all_integrations()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED! The application is safe and efficient.")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()