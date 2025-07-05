#!/usr/bin/env python3
"""
Test suite for content image processing (.png, .jpg) in Greg
Tests visual content analysis and image understanding (not OCR)
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

class TestContentImageProcessing:
    """Test document processing for visual content image files"""
    
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
    
    def test_png_content_processing(self, setup):
        """Test processing of PNG content image"""
        png_file = self.test_files_dir / "test_content.png"
        
        # Test that we can process a PNG content file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(png_file), 
            "test_content.png"
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
    
    def test_jpg_content_processing(self, setup):
        """Test processing of JPG content image"""
        jpg_file = self.test_files_dir / "test_content.jpg"
        
        # Test that we can process a JPG content file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(jpg_file), 
            "test_content.jpg"
        )
        
        # Assertions
        assert doc_id is not None
        assert chunks > 0
        assert processing_time > 0
        
        # Verify vector store was created
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test basic search functionality
        results = vector_store.similarity_search("image", k=3)
        assert len(results) > 0
    
    def test_visual_content_description(self, setup):
        """Test that visual content gets some form of description"""
        png_file = self.test_files_dir / "test_content.png"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(png_file), 
            "test_content.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Since this is a visual image with no text, OCR should return minimal content
        # But the system should still create a searchable document
        results = vector_store.similarity_search("content", k=3)
        assert len(results) > 0
        
        # Check that we have some form of content (even if just metadata)
        content = results[0].page_content
        assert len(content) > 0
        
        # Should contain image-related keywords
        content_lower = content.lower()
        image_keywords = ["image", "png", "jpg", "content", "file"]
        has_image_keyword = any(keyword in content_lower for keyword in image_keywords)
        assert has_image_keyword, f"Content should contain image-related keywords: {content}"
    
    def test_animal_content_queries(self, setup):
        """Test queries about the animal in the image"""
        # Note: Since we only have OCR currently, these tests expect basic functionality
        # When vision models are added, these can be enhanced for actual visual recognition
        png_file = self.test_files_dir / "test_content.png"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(png_file), 
            "test_content.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Basic queries that should work with current implementation
        basic_queries = [
            ("What type of file is this", "png"),
            ("Image content", "image"),
            ("Visual content", "content"),
        ]
        
        for query, expected in basic_queries:
            results = vector_store.similarity_search(query, k=3)
            assert len(results) > 0, f"Should return results for query: {query}"
            
            # Basic content check
            found = any(expected.lower() in result.page_content.lower() for result in results)
            assert found, f"Should find '{expected}' for query '{query}'"
    
    def test_visual_analysis_placeholder(self, setup):
        """Placeholder test for future vision model integration"""
        # This test documents what we want to achieve with vision models
        jpg_file = self.test_files_dir / "test_content.jpg"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(jpg_file), 
            "test_content.jpg"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # For now, just test that the image is processed
        results = vector_store.similarity_search("image analysis", k=3)
        assert len(results) > 0
        
        # TODO: When vision models are implemented, test for:
        # - Dog breed recognition ("English Bulldog")
        # - Accessory detection ("glasses", "Ray-Ban")
        # - Color analysis ("tan", "white", "black")
        # - Pose detection ("sitting")
        # - Expression analysis ("stern", "serious")
        # - Environmental details ("wood floor", "off-white wall")
        
        # Current implementation should at least handle the file
        content = results[0].page_content
        assert "image" in content.lower() or "content" in content.lower()
    
    def test_content_metadata_preservation(self, setup):
        """Test that content image metadata is preserved"""
        png_file = self.test_files_dir / "test_content.png"
        
        doc_id, _, chunks, _ = self.processor.process_file(
            str(png_file), 
            "test_content.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Get a sample result
        results = vector_store.similarity_search("image", k=1)
        assert len(results) > 0
        
        # Check metadata
        metadata = results[0].metadata
        assert 'file_type' in metadata
        assert metadata['file_type'] in ['png', 'jpg', 'image']
        assert 'filename' in metadata
        assert metadata['filename'] == 'test_content.png'
        
        # Should indicate the extraction method
        assert 'extraction_method' in metadata
    
    def test_content_format_consistency(self, setup):
        """Test that PNG and JPG content formats are processed consistently"""
        png_file = self.test_files_dir / "test_content.png"
        jpg_file = self.test_files_dir / "test_content.jpg"
        
        # Process both formats
        png_doc_id, _, png_chunks, _ = self.processor.process_file(
            str(png_file), "test_content.png"
        )
        jpg_doc_id, _, jpg_chunks, _ = self.processor.process_file(
            str(jpg_file), "test_content.jpg"
        )
        
        # Both should process successfully
        assert png_chunks > 0
        assert jpg_chunks > 0
        
        # Test same query on both
        png_store = self.processor.load_vector_store(png_doc_id)
        jpg_store = self.processor.load_vector_store(jpg_doc_id)
        
        test_query = "image content"
        png_results = png_store.similarity_search(test_query, k=3)
        jpg_results = jpg_store.similarity_search(test_query, k=3)
        
        # Both should return results
        assert len(png_results) > 0, "PNG should be searchable"
        assert len(jpg_results) > 0, "JPG should be searchable"
    
    def test_no_text_handling(self, setup):
        """Test handling of images with no extractable text"""
        png_file = self.test_files_dir / "test_content.png"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(png_file), 
            "test_content.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Should still create searchable content even with no text
        results = vector_store.similarity_search("no text", k=3)
        assert len(results) > 0
        
        # Content should indicate this is a visual image
        content = results[0].page_content.lower()
        visual_indicators = ["image", "content", "visual", "no text", "extractable"]
        has_visual_indicator = any(indicator in content for indicator in visual_indicators)
        assert has_visual_indicator, f"Should indicate visual content: {content}"
    
    def test_future_vision_capabilities(self, setup):
        """Test framework for future vision model capabilities"""
        # This test establishes the framework for when we add vision models
        jpg_file = self.test_files_dir / "test_content.jpg"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(jpg_file), 
            "test_content.jpg"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Framework for future vision queries about the English Bulldog
        future_vision_queries = [
            # Animal identification
            ("What animal is in the image", "bulldog"),
            ("What breed of dog", "english bulldog"),
            
            # Accessories and objects
            ("What is the dog wearing", "glasses"),
            ("What type of glasses", "ray-ban"),
            
            # Colors and markings  
            ("What colors is the dog", "tan"),
            ("What color is the chest", "white"),
            
            # Pose and expression
            ("How is the dog positioned", "sitting"),
            ("What is the dog's expression", "stern"),
            
            # Environment
            ("What type of floor", "wood"),
            ("What color is the wall", "white"),
        ]
        
        # For now, just ensure the image is processed and searchable
        for query, expected_future in future_vision_queries:
            results = vector_store.similarity_search(query, k=3)
            assert len(results) > 0, f"Image should be searchable for: {query}"
            
            # TODO: When vision models are implemented, uncomment this:
            # found = any(expected_future.lower() in result.page_content.lower() for result in results)
            # assert found, f"Vision model should detect '{expected_future}' for query '{query}'"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])