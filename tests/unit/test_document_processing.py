#!/usr/bin/env python3
"""
Test suite for multi-format document processing in Greg
Tests TXT, CSV, and future file format support
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

class TestDocumentProcessing:
    """Test document processing for different file types"""
    
    @pytest.fixture
    def setup(self):
        """Setup test environment"""
        # Create temp directories for testing
        self.temp_upload = tempfile.mkdtemp()
        self.temp_vectors = tempfile.mkdtemp()
        
        # Create config and override paths BEFORE creating processor
        self.config = Config()
        self.config.UPLOAD_DIR = Path(self.temp_upload)
        self.config.VECTOR_STORE_DIR = Path(self.temp_vectors)
        
        # Now create processor with the modified config
        self.processor = DocumentProcessor()
        # Override the processor's config paths too
        self.processor.config.UPLOAD_DIR = Path(self.temp_upload)
        self.processor.config.VECTOR_STORE_DIR = Path(self.temp_vectors)
        
        self.test_files_dir = Path(__file__).parent.parent / "fixtures"
        
        yield
        
        # Cleanup
        shutil.rmtree(self.temp_upload, ignore_errors=True)
        shutil.rmtree(self.temp_vectors, ignore_errors=True)
    
    def test_txt_file_processing(self, setup):
        """Test processing of .txt files"""
        txt_file = self.test_files_dir / "test_invoice.txt"
        
        # Test that we can process a txt file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(txt_file), 
            "test_invoice.txt"
        )
        
        # Assertions
        assert doc_id is not None
        assert len(doc_id) == 16  # Hash-based ID
        assert pages >= 1  # At least one "page" for text files
        assert chunks > 0  # Should create chunks
        assert processing_time > 0
        
        # Verify vector store was created
        vector_store_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
        assert vector_store_path.exists()
        
        # Verify metadata was saved
        metadata_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.metadata"
        assert metadata_path.exists()
    
    def test_csv_file_processing(self, setup):
        """Test processing of .csv files"""
        csv_file = self.test_files_dir / "test_invoice.csv"
        
        # Test that we can process a csv file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(csv_file), 
            "test_invoice.csv"
        )
        
        # Assertions
        assert doc_id is not None
        assert chunks > 0  # Should create chunks from CSV rows
        assert processing_time > 0
        
        # CSV-specific: should handle structured data
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test search functionality - look for DataTech Solutions
        results = vector_store.similarity_search("DataTech Solutions", k=3)
        assert len(results) > 0
        # Should find at least one row mentioning DataTech
    
    def test_file_type_detection(self, setup):
        """Test automatic file type detection"""
        # Test various file extensions
        test_cases = [
            ("test.txt", "text"),
            ("test.csv", "csv"),
            ("test.pdf", "pdf"),
            ("test.md", "markdown"),
            ("test.docx", "docx"),
        ]
        
        for filename, expected_type in test_cases:
            detected_type = self.processor.detect_file_type(filename)
            assert detected_type == expected_type
    
    def test_unsupported_file_type(self, setup):
        """Test handling of unsupported file types"""
        with pytest.raises(ValueError, match="Unsupported file type"):
            self.processor.detect_file_type("test.xyz")
    
    def test_txt_content_preservation(self, setup):
        """Test that text content is properly preserved"""
        txt_file = self.test_files_dir / "test_invoice.txt"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(txt_file), 
            "test_invoice.txt"
        )
        
        # Load vector store and search for specific content
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test searches for known content - search in top 3 results
        test_queries = [
            ("ACME CORPORATION invoice", "ACME CORPORATION"),
            ("Invoice Number INV-2025-002", "INV-2025-002"),
            ("Total Due 109500", "109,500.00"),
        ]
        
        for query, expected_content in test_queries:
            results = vector_store.similarity_search(query, k=3)
            assert len(results) > 0
            # Check if expected content is in any of the top 3 results
            found = any(expected_content in result.page_content for result in results)
            assert found, f"Expected '{expected_content}' not found in search results for query '{query}'"
    
    def test_csv_structured_data(self, setup):
        """Test that CSV data maintains structure"""
        csv_file = self.test_files_dir / "test_invoice.csv"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(csv_file), 
            "test_invoice.csv"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Search for products by different attributes
        results = vector_store.similarity_search("AI Software with 5.0 rating", k=3)
        assert len(results) > 0
        
        # Check that we can find specific items
        results = vector_store.similarity_search("Database Optimization hours", k=1)
        assert len(results) > 0
        # Should find the Database Optimization Service line

if __name__ == "__main__":
    pytest.main([__file__, "-v"])