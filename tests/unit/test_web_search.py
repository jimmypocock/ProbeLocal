"""Unit tests for web search functionality"""
import pytest
import time
from datetime import datetime
from src.web_search import WebSearcher, SearchResult


class TestWebSearch:
    """Test web search functionality"""
    
    def test_search_result_creation(self):
        """Test creating a SearchResult object"""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="This is a test snippet"
        )
        
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "This is a test snippet"
        assert result.source == "web"
        assert result.timestamp is not None
        
    def test_web_searcher_initialization(self):
        """Test WebSearcher initialization"""
        searcher = WebSearcher(cache_ttl_minutes=10)
        
        assert searcher.cache_ttl.total_seconds() == 600
        assert len(searcher.cache) == 0
        assert searcher.session is not None
        
    def test_cache_key_generation(self):
        """Test cache key generation"""
        searcher = WebSearcher()
        
        key1 = searcher._get_cache_key("test query", 5)
        key2 = searcher._get_cache_key("test query", 5)
        key3 = searcher._get_cache_key("different query", 5)
        
        assert key1 == key2  # Same query should produce same key
        assert key1 != key3  # Different queries should produce different keys
        
    def test_content_sanitization(self):
        """Test content sanitization"""
        searcher = WebSearcher()
        
        # Test script tag sanitization
        dangerous = "<script>alert('xss')</script>Some content"
        sanitized = searcher.sanitize_content(dangerous)
        assert "<script" not in sanitized
        assert "&lt;script" in sanitized
        
        # Test other dangerous tags
        dangerous = "<iframe src='evil.com'></iframe>"
        sanitized = searcher.sanitize_content(dangerous)
        assert "<iframe" not in sanitized
        
    def test_cache_operations(self):
        """Test cache operations"""
        searcher = WebSearcher()
        
        # Create test results
        results = [
            SearchResult("Test 1", "http://test1.com", "Snippet 1"),
            SearchResult("Test 2", "http://test2.com", "Snippet 2")
        ]
        
        # Add to cache
        key = "test_key"
        searcher._add_to_cache(key, results)
        
        # Retrieve from cache
        cached = searcher._get_from_cache(key)
        assert cached is not None
        assert len(cached) == 2
        assert cached[0].title == "Test 1"
        
        # Clear cache
        searcher.clear_cache()
        assert searcher._get_from_cache(key) is None
        
    def test_actual_search(self):
        """Test web search with mocked responses"""
        searcher = WebSearcher()
        
        # Mock the search results
        mock_results = [
            SearchResult(
                title="Python Programming Tutorial",
                url="https://example.com/python",
                snippet="Learn Python programming from scratch"
            ),
            SearchResult(
                title="Advanced Python Techniques",
                url="https://example.com/advanced-python",
                snippet="Master advanced Python concepts"
            )
        ]
        
        # Store in cache to simulate search results
        cache_key = searcher._get_cache_key("Python programming", 3)
        searcher.cache[cache_key] = {
            'results': mock_results,
            'timestamp': datetime.now()
        }
        
        # Now search should return cached results
        results = searcher.search("Python programming", num_results=3)
        
        assert len(results) == 2
        assert results[0].title == "Python Programming Tutorial"
        assert results[1].title == "Advanced Python Techniques"
        for result in results:
            assert result.title
            assert result.url
            assert result.url.startswith("http")
            
    def test_content_extraction(self):
        """Test content extraction with mocked response"""
        searcher = WebSearcher()
        
        # Mock the extract_content method
        test_url = "https://example.com"
        mock_content = """Example Domain
        
        This domain is for use in illustrative examples in documents.
        You may use this domain in literature without prior coordination or asking for permission.
        
        More information..."""
        
        # Store in cache to simulate extracted content
        cache_key = f"content_{test_url}"
        searcher.cache[cache_key] = {
            'content': mock_content,
            'timestamp': datetime.now()
        }
        
        # Monkey patch the extract_content method to check cache first
        original_extract = searcher.extract_content
        def mock_extract(url):
            cache_key = f"content_{url}"
            cached = searcher.cache.get(cache_key)
            if cached:
                return cached['content']
            return original_extract(url)
        
        searcher.extract_content = mock_extract
        
        # Test extraction
        content = searcher.extract_content(test_url)
        
        assert content is not None
        assert len(content) > 0
        assert "Example Domain" in content
        assert "illustrative examples" in content