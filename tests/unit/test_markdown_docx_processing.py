#!/usr/bin/env python3
"""
Test suite for Markdown and Word document processing in Greg
"""

import os
import sys
import pytest
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.document_processor import DocumentProcessor
from src.config import Config

class TestMarkdownDocxProcessing:
    """Test document processing for Markdown and Word files"""
    
    @pytest.fixture
    def setup(self):
        """Setup test environment"""
        # Create temp directories for testing
        self.temp_upload = tempfile.mkdtemp()
        self.temp_vectors = tempfile.mkdtemp()
        
        # Create config and override paths
        self.config = Config()
        self.config.UPLOAD_DIR = Path(self.temp_upload)
        self.config.VECTOR_STORE_DIR = Path(self.temp_vectors)
        
        # Create processor with modified config
        self.processor = DocumentProcessor()
        self.processor.config.UPLOAD_DIR = Path(self.temp_upload)
        self.processor.config.VECTOR_STORE_DIR = Path(self.temp_vectors)
        
        self.test_files_dir = Path(__file__).parent.parent / "fixtures"
        
        yield
        
        # Cleanup
        shutil.rmtree(self.temp_upload, ignore_errors=True)
        shutil.rmtree(self.temp_vectors, ignore_errors=True)
    
    def test_markdown_file_processing(self, setup):
        """Test processing of .md files"""
        md_file = self.test_files_dir / "test_invoice.md"
        
        # Test that we can process a markdown file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(md_file), 
            "test_invoice.md"
        )
        
        # Assertions
        assert doc_id is not None
        assert len(doc_id) == 16  # Hash-based ID
        assert pages >= 1
        assert chunks > 0
        assert processing_time > 0
        
        # Verify vector store was created
        vector_store_path = self.processor.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
        assert vector_store_path.exists()
        
        # Verify metadata includes file type
        metadata_path = self.processor.config.VECTOR_STORE_DIR / f"{doc_id}.metadata"
        assert metadata_path.exists()
    
    def test_docx_file_processing(self, setup):
        """Test processing of .docx files"""
        docx_file = self.test_files_dir / "test_invoice.docx"
        
        # Test that we can process a Word document
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(docx_file), 
            "test_invoice.docx"
        )
        
        # Assertions
        assert doc_id is not None
        assert chunks > 0
        assert processing_time > 0
        
        # Verify vector store was created
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test search functionality
        results = vector_store.similarity_search("TechVision Solutions", k=3)
        assert len(results) > 0
        # Should find company name in at least one chunk
    
    def test_markdown_content_preservation(self, setup):
        """Test that Markdown content and structure is preserved"""
        md_file = self.test_files_dir / "test_invoice.md"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(md_file), 
            "test_invoice.md"
        )
        
        # Load vector store and search for specific content
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test searches for known content
        test_queries = [
            ("CloudScale Technologies", "CloudScale"),
            ("Invoice INV-2025-004", "INV-2025-004"),
            ("Total Due 220500", "220,500.00"),
            ("March training", "March 10-14"),
        ]
        
        for query, expected_content in test_queries:
            results = vector_store.similarity_search(query, k=3)
            assert len(results) > 0
            found = any(expected_content in result.page_content for result in results)
            assert found, f"Expected '{expected_content}' not found in search results for query '{query}'"
    
    def test_docx_content_preservation(self, setup):
        """Test that Word document content is properly preserved"""
        docx_file = self.test_files_dir / "test_invoice.docx"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(docx_file), 
            "test_invoice.docx"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test various content types from the Word doc
        test_queries = [
            ("TechVision Solutions", "TechVision"),
            ("Invoice INV-2025-005", "INV-2025-005"),
            ("Total Due 197448", "197,448.00"),
            ("IoT Sensor Integration", "IoT"),
            ("March 15 go-live", "March 15"),
        ]
        
        for query, expected_content in test_queries:
            results = vector_store.similarity_search(query, k=3)
            assert len(results) > 0
            found = any(expected_content in result.page_content for result in results)
            assert found, f"Expected '{expected_content}' not found in search results for query '{query}'"
    
    def test_markdown_tables(self, setup):
        """Test that Markdown tables are preserved"""
        md_file = self.test_files_dir / "test_invoice.md"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(md_file), 
            "test_invoice.md"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Search for table content
        results = vector_store.similarity_search("AWS Architecture Design hours", k=3)
        assert len(results) > 0
        
        # Check that table data is preserved
        found_table = any("16,500" in result.page_content or "$275/hr" in result.page_content 
                        for result in results)
        assert found_table, "Table data not properly preserved"
    
    def test_docx_tables_and_lists(self, setup):
        """Test that Word document tables and lists are handled"""
        docx_file = self.test_files_dir / "test_invoice.docx"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(docx_file), 
            "test_invoice.docx"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Search for table content
        results = vector_store.similarity_search("Streamlit User interface", k=3)
        assert len(results) > 0
        
        # Search for list content
        results = vector_store.similarity_search("Privacy concerns cloud-based", k=3)
        assert len(results) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])