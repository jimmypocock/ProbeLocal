"""Unit tests for web search functionality"""
import pytest
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
        
    @pytest.mark.skip(reason="Requires internet connection")
    def test_actual_search(self):
        """Test actual web search (requires internet)"""
        searcher = WebSearcher()
        
        results = searcher.search("Python programming", num_results=3)
        
        assert len(results) <= 3
        for result in results:
            assert result.title
            assert result.url
            assert result.url.startswith("http")
            
    @pytest.mark.skip(reason="Requires internet connection")
    def test_content_extraction(self):
        """Test content extraction from URL"""
        searcher = WebSearcher()
        
        # Use a reliable test URL
        content = searcher.extract_content("https://example.com")
        
        assert content is not None
        assert len(content) > 0
        assert "Example Domain" in content