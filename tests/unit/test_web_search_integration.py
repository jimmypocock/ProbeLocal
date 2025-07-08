"""Test web search integration with QA chain"""
import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.qa_chain_enhanced import EnhancedQAChain
from src.web_search import WebSearcher, SearchResult


def test_enhanced_qa_chain_initialization():
    """Test that enhanced QA chain initializes properly"""
    chain = EnhancedQAChain()
    assert chain.web_searcher is not None
    assert isinstance(chain.web_searcher, WebSearcher)


def test_web_only_search():
    """Test web-only search functionality"""
    chain = EnhancedQAChain()
    
    # Test with a simple query
    result = chain.answer_question_with_web(
        question="What is Python programming language?",
        document_id="web_only",
        use_web=True,
        max_results=3,
        model_name="mistral",
        temperature=0.7
    )
    
    assert 'answer' in result
    assert 'sources' in result
    assert result['document_id'] == 'web_only'
    assert result.get('used_web_search', False) == True
    assert '🌐' in result['answer']  # Should have web indicator


def test_hybrid_search_with_document():
    """Test that hybrid search falls back to web when document doesn't exist"""
    chain = EnhancedQAChain()
    
    # When document doesn't exist but web is enabled, it should use web search
    result = chain.answer_question_with_web(
        question="What is in this document?",
        document_id="non_existent_doc",
        use_web=True,
        max_results=3,
        model_name="mistral",
        temperature=0.7
    )
    
    # Should get a web-based answer
    assert result is not None
    assert 'answer' in result
    assert result['sources'] is not None


def test_web_search_formatting():
    """Test that web search results are properly formatted"""
    chain = EnhancedQAChain()
    
    # Create mock search results
    from langchain.schema import Document
    
    web_doc = Document(
        page_content="Test web content",
        metadata={
            "source": "web",
            "url": "https://example.com",
            "title": "Example Page",
            "search_rank": 1
        }
    )
    
    doc_doc = Document(
        page_content="Test document content",
        metadata={
            "page": 1,
            "chunk_index": 0
        }
    )
    
    sources = chain._format_sources([web_doc, doc_doc])
    
    assert len(sources) == 2
    assert sources[0]['type'] == 'web'
    assert sources[0]['url'] == 'https://example.com'
    assert sources[1]['type'] == 'document'
    assert sources[1]['page'] == 1


def test_search_web_for_context():
    """Test web search context creation"""
    chain = EnhancedQAChain()
    
    # Test search for context
    docs = chain._search_web_for_context("Python programming", num_results=2)
    
    assert isinstance(docs, list)
    assert len(docs) <= 2
    
    if docs:  # If search returns results
        assert all(hasattr(doc, 'page_content') for doc in docs)
        assert all(hasattr(doc, 'metadata') for doc in docs)
        assert all(doc.metadata.get('source') == 'web' for doc in docs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])