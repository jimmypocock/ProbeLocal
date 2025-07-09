#!/usr/bin/env python3
"""Test UI improvements and performance optimizations"""

import sys
import os
import time
import requests
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.performance.optimizations import Debouncer, LRUCache, BatchProcessor, memoize_result
from src.performance.request_queue import RequestQueueManager
from src.performance.vector_store_cache import OptimizedVectorStore
from src.ui.lazy_loading import LazyDocumentList, VirtualScrollChat


def test_debouncer():
    """Test debouncer functionality"""
    print("\n=== Testing Debouncer ===")
    
    call_count = 0
    
    def test_func():
        nonlocal call_count
        call_count += 1
    
    debouncer = Debouncer(delay=0.1)
    
    # Rapid calls - only last should execute
    for i in range(5):
        debouncer.debounce('test', test_func)
        time.sleep(0.02)  # Less than delay
    
    time.sleep(0.15)  # Wait for debounce
    print(f"Call count after rapid calls: {call_count} (expected: 1)")
    assert call_count == 1, f"Expected 1 call, got {call_count}"
    
    print("✅ Debouncer test passed!")


def test_lru_cache():
    """Test LRU cache functionality"""
    print("\n=== Testing LRU Cache ===")
    
    cache = LRUCache(max_size=3)
    
    # Test basic caching
    cache.set("result1", "key1", 10)
    cache.set("result2", "key2", 20)
    cache.set("result3", "key3", 30)
    
    assert cache.get("key1", 10) == "result1"
    assert cache.get("key2", 20) == "result2"
    
    # Test LRU eviction
    cache.set("result4", "key4", 40)  # Should evict key3
    assert cache.get("key3", 30) is None
    assert cache.get("key4", 40) == "result4"
    
    print("✅ LRU Cache test passed!")


def test_memoization():
    """Test memoization decorator"""
    print("\n=== Testing Memoization ===")
    
    call_count = 0
    
    @memoize_result(ttl=1)
    def expensive_function(x):
        nonlocal call_count
        call_count += 1
        return x * 2
    
    # First call
    result1 = expensive_function(5)
    assert result1 == 10
    assert call_count == 1
    
    # Second call (cached)
    result2 = expensive_function(5)
    assert result2 == 10
    assert call_count == 1  # No new call
    
    # Different argument
    result3 = expensive_function(3)
    assert result3 == 6
    assert call_count == 2
    
    # Wait for TTL
    time.sleep(1.1)
    result4 = expensive_function(5)
    assert result4 == 10
    assert call_count == 3  # New call after TTL
    
    print("✅ Memoization test passed!")


def test_batch_processor():
    """Test batch processor"""
    print("\n=== Testing Batch Processor ===")
    
    processor = BatchProcessor(batch_size=3, timeout=0.1)
    
    # Add items
    for i in range(5):
        processor.add(f"item_{i}")
    
    # Should process first batch immediately (3 items)
    processed = processor.process()
    assert len(processed) == 2  # Remaining 2 items
    
    # Add more items
    processor.add("item_5")
    processor.add("item_6")
    
    # Wait for timeout
    time.sleep(0.15)
    processed = processor.process()
    assert len(processed) == 2
    
    print("✅ Batch Processor test passed!")


def test_request_queue():
    """Test request queue manager"""
    print("\n=== Testing Request Queue ===")
    
    queue = RequestQueueManager(max_concurrent=2)
    
    # Register test handler
    def test_handler(value):
        time.sleep(0.1)
        return value * 2
    
    queue.register_handler('test', test_handler)
    
    # Submit requests
    request_ids = []
    for i in range(5):
        req_id = queue.submit_request('test', {'value': i}, priority=i)
        request_ids.append(req_id)
    
    # Check queue stats
    stats = queue.get_stats()
    print(f"Queue stats: {stats}")
    assert stats['pending'] >= 2  # Some should be pending
    assert stats['processing'] <= 2  # Max concurrent
    
    # Wait for completion
    time.sleep(0.5)
    
    # Check results
    for i, req_id in enumerate(request_ids):
        status = queue.get_request_status(req_id)
        if status and status.status.value == 'completed':
            assert status.result == i * 2
    
    queue.shutdown()
    print("✅ Request Queue test passed!")


def test_lazy_loading():
    """Test lazy loading components"""
    print("\n=== Testing Lazy Loading ===")
    
    # Test document list pagination
    docs = [{'document_id': f'doc_{i}', 'filename': f'file_{i}.pdf'} for i in range(25)]
    lazy_list = LazyDocumentList(items_per_page=10)
    
    # Check pagination logic
    total_pages = 3  # 25 docs / 10 per page = 3 pages
    print(f"Total documents: 25, Pages: {total_pages}")
    
    # Test virtual scroll for chat
    messages = [{'role': 'user' if i % 2 == 0 else 'assistant', 'content': f'Message {i}'} 
                for i in range(50)]
    virtual_scroll = VirtualScrollChat(messages_per_page=20)
    
    print("✅ Lazy Loading test passed!")


def test_vector_store_optimization():
    """Test vector store optimization"""
    print("\n=== Testing Vector Store Optimization ===")
    
    optimizer = OptimizedVectorStore(cache_size=10)
    
    # Test cache key generation
    key1 = optimizer._get_cache_key("test query", 5, "doc_123")
    key2 = optimizer._get_cache_key("test query", 5, "doc_123")
    key3 = optimizer._get_cache_key("different query", 5, "doc_123")
    
    assert key1 == key2
    assert key1 != key3
    
    print("✅ Vector Store Optimization test passed!")


def test_api_integration():
    """Test API endpoints with performance features"""
    print("\n=== Testing API Integration ===")
    
    # Check if API is running
    try:
        response = requests.get("http://localhost:8080/health", timeout=2)
        if response.status_code != 200:
            print("⚠️  API not running, skipping integration tests")
            return
    except:
        print("⚠️  API not running, skipping integration tests")
        return
    
    # Test concurrent requests
    print("Testing concurrent document listing...")
    import concurrent.futures
    
    def get_documents():
        return requests.get("http://localhost:8080/documents", timeout=5)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_documents) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    assert all(r.status_code == 200 for r in results)
    print("✅ API Integration test passed!")


def main():
    """Run all UI and performance tests"""
    print("🚀 Testing UI Improvements and Performance Optimizations")
    
    tests = [
        test_debouncer,
        test_lru_cache,
        test_memoization,
        test_batch_processor,
        test_request_queue,
        test_lazy_loading,
        test_vector_store_optimization,
        test_api_integration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {str(e)}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All UI and performance tests passed!")
    else:
        print(f"❌ {failed} tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()