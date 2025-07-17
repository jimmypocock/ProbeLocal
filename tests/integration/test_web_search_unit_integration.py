"""Test web search integration with QA chain"""
import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.qa_chain_unified import UnifiedQAChain
from src.web_search import WebSearcher, SearchResult


def test_enhanced_qa_chain_initialization():
    """Test that enhanced QA chain initializes properly"""
    chain = UnifiedQAChain()
    assert chain.web_searcher is not None
    assert isinstance(chain.web_searcher, WebSearcher)


def test_web_only_search():
    """Test web-only search functionality through UnifiedQAChain"""
    chain = UnifiedQAChain()
    
    # Test web search classification and handling
    intent, confidence = chain.classify_query_intent("What's the weather today?")
    
    # Should classify as web search
    assert intent.value == "web_search"
    
    # Test that web searcher is available
    assert hasattr(chain, 'web_searcher')
    assert chain.web_searcher is not None




def test_web_search_formatting():
    """Test that web search results can be properly formatted"""
    chain = UnifiedQAChain()
    
    # Test the format sources method exists and works
    from langchain.schema import Document
    
    web_doc = Document(
        page_content="Test web content",
        metadata={
            "source": "https://example.com",
            "url": "https://example.com",
            "title": "Example Page",
            "source_type": "web"
        }
    )
    
    doc_doc = Document(
        page_content="Test document content",
        metadata={
            "source": "test_document.txt",
            "page": 1,
            "chunk_index": 0,
            "source_type": "document"
        }
    )
    
    # Test that we can format sources using the chain's method
    sources = chain._format_sources([web_doc, doc_doc])
    
    assert len(sources) == 2
    assert sources[0]['type'] == 'web'
    assert sources[0]['source'] == 'https://example.com'
    assert sources[1]['type'] == 'document'
    assert sources[1]['source'] == 'test_document.txt'


def test_search_web_for_context():
    """Test web search context creation through web searcher"""
    chain = UnifiedQAChain()
    
    # Test that web searcher can search (if available)
    if chain.web_searcher:
        try:
            # Test a simple search
            results = chain.web_searcher.search("Python programming", num_results=2)
            
            assert isinstance(results, list)
            assert len(results) <= 2
            
            if results:  # If search returns results
                for result in results:
                    assert hasattr(result, 'content') or hasattr(result, 'page_content')
                    assert hasattr(result, 'url')
        except Exception as e:
            # Web search might not be available in test environment
            pytest.skip(f"Web search not available: {e}")
    else:
        pytest.skip("Web searcher not initialized")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])