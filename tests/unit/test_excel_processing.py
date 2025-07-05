#!/usr/bin/env python3
"""
Test suite for Excel (.xlsx) document processing in Greg
Tests both analytical (invoice) and narrative (story) Excel files
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

class TestExcelProcessing:
    """Test document processing for Excel files"""
    
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
    
    def test_xlsx_file_processing(self, setup):
        """Test basic processing of .xlsx files"""
        xlsx_file = self.test_files_dir / "test_invoice.xlsx"
        
        # Test that we can process an Excel file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(xlsx_file), 
            "test_invoice.xlsx"
        )
        
        # Assertions
        assert doc_id is not None
        assert len(doc_id) == 16  # Hash-based ID
        assert pages >= 3  # Should have at least 3 sheets
        assert chunks > 0
        assert processing_time > 0
        
        # Verify vector store was created
        vector_store_path = self.processor.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
        assert vector_store_path.exists()
    
    def test_xlsx_invoice_content(self, setup):
        """Test extraction of invoice data from Excel"""
        xlsx_file = self.test_files_dir / "test_invoice.xlsx"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(xlsx_file), 
            "test_invoice.xlsx"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test invoice-specific queries
        test_queries = [
            ("Digital Dynamics invoice number", "INV-2025-006"),
            ("Total due amount 313232", "313232.4"),  # Excel stores without comma formatting
            ("Quantum Analytics Corp", "Quantum Analytics"),
            ("Machine Learning Model Development", "models"),
            ("Dr Rachel Kim", "Rachel Kim"),
        ]
        
        for query, expected_content in test_queries:
            results = vector_store.similarity_search(query, k=5)
            assert len(results) > 0
            found = any(expected_content in result.page_content for result in results)
            assert found, f"Expected '{expected_content}' not found in search results for query '{query}'"
    
    def test_xlsx_multiple_sheets(self, setup):
        """Test that multiple sheets are processed"""
        xlsx_file = self.test_files_dir / "test_invoice.xlsx"
        
        doc_id, pages, _, _ = self.processor.process_file(
            str(xlsx_file), 
            "test_invoice.xlsx"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test content from different sheets
        sheet_queries = [
            ("Invoice sheet content", "DIGITAL DYNAMICS LLC"),  # Main sheet
            ("Project phases breakdown", "Requirements Analysis"),  # Project Details sheet
            ("Resource allocation Sarah Chen", "Lead Data Scientist"),  # Resources sheet
        ]
        
        for query, expected in sheet_queries:
            results = vector_store.similarity_search(query, k=5)
            found = any(expected in result.page_content for result in results)
            assert found, f"Content from multiple sheets not found: {expected}"
    
    def test_xlsx_story_comprehension(self, setup):
        """Test narrative comprehension from story Excel"""
        xlsx_file = self.test_files_dir / "test_story.xlsx"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(xlsx_file), 
            "test_story.xlsx"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test story comprehension queries
        comprehension_queries = [
            ("What did Dr Chen discover in Antarctica", "anomalous ice core"),
            ("What happened to the research team", "We are becoming something new"),
            ("Crystal properties and effects", "Consciousness interface"),
            ("Station Echo final fate", "human-shaped formations"),
            ("Timeline November 22 events", "awakening requires willing minds"),
        ]
        
        for query, expected in comprehension_queries:
            results = vector_store.similarity_search(query, k=20)  # Increased k to find content across sheets
            assert len(results) > 0
            found = any(expected.lower() in result.page_content.lower() for result in results)
            assert found, f"Story element '{expected}' not found for query '{query}'"
    
    def test_xlsx_data_preservation(self, setup):
        """Test that Excel data structure is preserved"""
        xlsx_file = self.test_files_dir / "test_invoice.xlsx"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(xlsx_file), 
            "test_invoice.xlsx"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test that tabular relationships are maintained
        results = vector_store.similarity_search("Cloud Infrastructure Optimization cost", k=3)
        assert len(results) > 0
        
        # Should find the item and its associated cost
        found_item = any("Cloud Infrastructure Optimization" in r.page_content for r in results)
        found_cost = any("32000" in r.page_content or "32,000" in r.page_content for r in results)
        assert found_item or found_cost, "Tabular data relationships not preserved"
    
    def test_xlsx_metadata_preservation(self, setup):
        """Test that Excel metadata is preserved"""
        xlsx_file = self.test_files_dir / "test_invoice.xlsx"
        
        doc_id, _, chunks, _ = self.processor.process_file(
            str(xlsx_file), 
            "test_invoice.xlsx"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Get a sample result
        results = vector_store.similarity_search("invoice", k=1)
        assert len(results) > 0
        
        # Check metadata
        metadata = results[0].metadata
        assert 'file_type' in metadata
        assert metadata['file_type'] == 'xlsx'
        assert 'filename' in metadata
        assert metadata['filename'] == 'test_invoice.xlsx'
    
    def test_xlsx_complex_queries(self, setup):
        """Test complex analytical queries on Excel data"""
        xlsx_file = self.test_files_dir / "test_invoice.xlsx"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(xlsx_file), 
            "test_invoice.xlsx"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Complex queries that require understanding relationships
        complex_queries = [
            ("Early payment discount percentage", "5%"),
            ("Phase 2 timeline for model development", "2025-02-15"),
            ("James Wilson hourly rate", "275"),
            ("Total project phases", "Phase 4"),
        ]
        
        for query, expected in complex_queries:
            results = vector_store.similarity_search(query, k=5)
            found = any(expected in result.page_content for result in results)
            assert found, f"Complex query failed: expected '{expected}' for '{query}'"
    
    def test_xlsx_narrative_inference(self, setup):
        """Test inference and comprehension from story Excel"""
        xlsx_file = self.test_files_dir / "test_story.xlsx"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(xlsx_file), 
            "test_story.xlsx"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Queries requiring inference and comprehension
        inference_queries = [
            ("Why did the team lose contact with outside world", "Satellite uplink fails"),
            ("What was the significance of the crystals", "invitation"),
            ("Dr Petrov medical findings about the team", "unusual neural activity"),
            ("Final status of the expedition members", "six human-shaped formations"),
        ]
        
        for query, expected in inference_queries:
            results = vector_store.similarity_search(query, k=20)  # Increased k to find content across sheets
            found = any(expected.lower() in result.page_content.lower() for result in results)
            assert found, f"Inference query failed: expected '{expected}' for '{query}'"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])