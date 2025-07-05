#!/usr/bin/env python3
"""
Test suite for image processing (.png, .jpg) in Greg
Tests OCR text extraction and image content analysis
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

class TestImageProcessing:
    """Test document processing for image files"""
    
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
    
    def test_png_invoice_processing(self, setup):
        """Test processing of PNG invoice image"""
        png_file = self.test_files_dir / "test_invoice.png"
        
        # Test that we can process a PNG file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(png_file), 
            "test_invoice.png"
        )
        
        # Assertions
        assert doc_id is not None
        assert len(doc_id) == 16  # Hash-based ID
        assert pages >= 1  # At least one "page" for images
        assert chunks > 0
        assert processing_time > 0
        
        # Verify vector store was created
        vector_store_path = self.processor.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
        assert vector_store_path.exists()
    
    def test_jpg_invoice_processing(self, setup):
        """Test processing of JPG invoice image"""
        jpg_file = self.test_files_dir / "test_invoice.jpg"
        
        # Test that we can process a JPG file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(jpg_file), 
            "test_invoice.jpg"
        )
        
        # Assertions
        assert doc_id is not None
        assert chunks > 0
        assert processing_time > 0
        
        # Verify vector store was created
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test search functionality
        results = vector_store.similarity_search("Easy Repair Inc", k=3)
        assert len(results) > 0
    
    def test_png_invoice_ocr_content(self, setup):
        """Test OCR text extraction from PNG invoice"""
        png_file = self.test_files_dir / "test_invoice.png"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(png_file), 
            "test_invoice.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test OCR-specific queries for invoice content
        # Note: OCR may have some errors, so we test for core recognizable content
        ocr_queries = [
            ("Repair Inc company name", "Repair Inc"),  # OCR shows "East Repair Inc"
            ("Invoice number US-001", "us-001"),  # OCR may change case
            ("Total amount 154.06", "154.06"),
            ("John Smith billing", "John Smith"),
            ("Harvest Lane address", "Harvest Lane"),
            ("brake cables item", "brake cables"),
            ("Sales Tax percentage", "6.25%"),
        ]
        
        for query, expected_content in ocr_queries:
            results = vector_store.similarity_search(query, k=5)
            assert len(results) > 0
            found = any(expected_content in result.page_content for result in results)
            assert found, f"OCR content '{expected_content}' not found in PNG for query '{query}'"
    
    def test_jpg_invoice_ocr_content(self, setup):
        """Test OCR text extraction from JPG invoice"""
        jpg_file = self.test_files_dir / "test_invoice.jpg"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(jpg_file), 
            "test_invoice.jpg"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test OCR-specific queries for invoice content
        ocr_queries = [
            ("Repair Inc company", "Repair Inc"),
            ("Invoice US-001", "us-001"),
            ("Total 154.06", "154.06"),
            ("John Smith customer", "John Smith"),
            ("New York address", "New York"),
            ("pedal arms", "pedal arms"),
            ("Labor hours", "Labor"),
        ]
        
        for query, expected_content in ocr_queries:
            results = vector_store.similarity_search(query, k=5)
            assert len(results) > 0
            found = any(expected_content in result.page_content for result in results)
            assert found, f"OCR content '{expected_content}' not found in JPG for query '{query}'"
    
    def test_invoice_detailed_extraction(self, setup):
        """Test detailed data extraction from invoice image"""
        png_file = self.test_files_dir / "test_invoice.png"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(png_file), 
            "test_invoice.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test specific invoice data extraction (based on OCR output)
        detailed_queries = [
            ("Invoice date 2019", "2019"),  # OCR shows "1110272019" 
            ("Due date 26/02/2019", "26/02/2019"),
            ("P.O. number 2312", "2312"),
            ("Front and rear brake cables price", "100.00"),
            ("Subtotal before tax", "145.00"),
            ("Payment terms 15 days", "15 days"),
            ("Make checks payable Repair", "Repair"),  # OCR shows "East Repair Inc"
        ]
        
        for query, expected in detailed_queries:
            results = vector_store.similarity_search(query, k=5)
            found = any(expected in result.page_content for result in results)
            assert found, f"Detailed content '{expected}' not found for query '{query}'"
    
    def test_invoice_calculations(self, setup):
        """Test extraction of calculated values from invoice"""
        jpg_file = self.test_files_dir / "test_invoice.jpg"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(jpg_file), 
            "test_invoice.jpg"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test mathematical calculations and totals
        calculation_queries = [
            ("Quantity 2 pedal arms cost", "30.00"),  # 2 × 15.00
            ("Labor cost 3 hours", "15.00"),  # 3 × 5.00
            ("Sales tax calculation", "9.06"),  # 6.25% of 145.00
            ("Final total amount", "154.06"),  # 145.00 + 9.06
        ]
        
        for query, expected in calculation_queries:
            results = vector_store.similarity_search(query, k=5)
            found = any(expected in result.page_content for result in results)
            assert found, f"Calculation '{expected}' not found for query '{query}'"
    
    def test_image_metadata_preservation(self, setup):
        """Test that image metadata is preserved"""
        png_file = self.test_files_dir / "test_invoice.png"
        
        doc_id, _, chunks, _ = self.processor.process_file(
            str(png_file), 
            "test_invoice.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Get a sample result
        results = vector_store.similarity_search("invoice", k=1)
        assert len(results) > 0
        
        # Check metadata
        metadata = results[0].metadata
        assert 'file_type' in metadata
        assert metadata['file_type'] in ['png', 'jpg', 'image']
        assert 'filename' in metadata
        assert metadata['filename'] == 'test_invoice.png'
    
    def test_both_formats_consistency(self, setup):
        """Test that PNG and JPG formats produce consistent results"""
        png_file = self.test_files_dir / "test_invoice.png"
        jpg_file = self.test_files_dir / "test_invoice.jpg"
        
        # Process both formats
        png_doc_id, _, png_chunks, _ = self.processor.process_file(
            str(png_file), "test_invoice.png"
        )
        jpg_doc_id, _, jpg_chunks, _ = self.processor.process_file(
            str(jpg_file), "test_invoice.jpg"
        )
        
        # Both should extract meaningful content
        assert png_chunks > 0
        assert jpg_chunks > 0
        
        # Test same query on both
        png_store = self.processor.load_vector_store(png_doc_id)
        jpg_store = self.processor.load_vector_store(jpg_doc_id)
        
        test_query = "Repair Inc"  # OCR shows "East Repair Inc"
        png_results = png_store.similarity_search(test_query, k=3)
        jpg_results = jpg_store.similarity_search(test_query, k=3)
        
        # Both should find the company name
        png_found = any("Repair Inc" in r.page_content for r in png_results)
        jpg_found = any("Repair Inc" in r.page_content for r in jpg_results)
        
        assert png_found, "PNG should extract 'Repair Inc'"
        assert jpg_found, "JPG should extract 'Repair Inc'"
    
    def test_complex_invoice_queries(self, setup):
        """Test complex analytical queries on invoice image"""
        png_file = self.test_files_dir / "test_invoice.png"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(png_file), 
            "test_invoice.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Complex queries requiring understanding relationships (based on OCR output)
        complex_queries = [
            ("Who is the invoice billed to", "John Smith"),
            ("What is the company providing service", "Repair Inc"),  # OCR shows "East Repair Inc"
            ("When is payment due", "26/02/2019"),
            ("What items were purchased", "brake cables"),
            ("What is the tax rate", "6.25%"),
            ("Where should checks be made payable", "Repair"),  # OCR may vary
        ]
        
        for query, expected in complex_queries:
            results = vector_store.similarity_search(query, k=5)
            found = any(expected in result.page_content for result in results)
            assert found, f"Complex query failed: expected '{expected}' for '{query}'"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])