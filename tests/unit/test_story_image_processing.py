#!/usr/bin/env python3
"""
Test suite for story image processing (.png, .jpg) in Greg
Tests OCR narrative text extraction and story comprehension
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

class TestStoryImageProcessing:
    """Test document processing for story image files"""
    
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
    
    def test_png_story_processing(self, setup):
        """Test processing of PNG story image"""
        png_file = self.test_files_dir / "test_story.png"
        
        # Test that we can process a PNG story file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(png_file), 
            "test_story.png"
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
    
    def test_jpg_story_processing(self, setup):
        """Test processing of JPG story image"""
        jpg_file = self.test_files_dir / "test_story.jpg"
        
        # Test that we can process a JPG story file
        doc_id, pages, chunks, processing_time = self.processor.process_file(
            str(jpg_file), 
            "test_story.jpg"
        )
        
        # Assertions
        assert doc_id is not None
        assert chunks > 0
        assert processing_time > 0
        
        # Verify vector store was created
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test search functionality for story content
        results = vector_store.similarity_search("WHAT REMAINS", k=3)
        assert len(results) > 0
    
    def test_png_story_narrative_content(self, setup):
        """Test narrative content extraction from PNG story"""
        png_file = self.test_files_dir / "test_story.png"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(png_file), 
            "test_story.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test story-specific narrative elements
        narrative_queries = [
            ("Story title What Remains", "WHAT REMAINS"),
            ("Publication Sucharnochee Review", "Sucharnochee"),
            ("Woman gathered dead animals", "raccoon"),
            ("Dead squirrel with tail", "squirrel"),
            ("Bird that might be crow or raven", "crow"),
            ("Woman carried sack", "sack"),
            ("Digging graves with spade", "spade"),
        ]
        
        for query, expected_content in narrative_queries:
            results = vector_store.similarity_search(query, k=5)
            assert len(results) > 0
            found = any(expected_content.lower() in result.page_content.lower() for result in results)
            assert found, f"Narrative content '{expected_content}' not found in PNG for query '{query}'"
    
    def test_jpg_story_narrative_content(self, setup):
        """Test narrative content extraction from JPG story"""
        jpg_file = self.test_files_dir / "test_story.jpg"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(jpg_file), 
            "test_story.jpg"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test story-specific narrative elements
        narrative_queries = [
            ("Story title", "WHAT REMAINS"),
            ("Review publication", "Review"),
            ("Woman collecting dead animals", "woman"),
            ("Gathering motionless bundle", "bundle"),
            ("Dead raccoon carried", "raccoon"),
            ("Squirrel without tail", "tail"),
            ("Burial with stones", "stones"),
        ]
        
        for query, expected_content in narrative_queries:
            results = vector_store.similarity_search(query, k=5)
            assert len(results) > 0
            found = any(expected_content.lower() in result.page_content.lower() for result in results)
            assert found, f"Narrative content '{expected_content}' not found in JPG for query '{query}'"
    
    def test_story_character_actions(self, setup):
        """Test extraction of character actions from story"""
        png_file = self.test_files_dir / "test_story.png"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(png_file), 
            "test_story.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test specific character actions and story events
        action_queries = [
            ("Woman stooped low to gather", "stooped"),
            ("Cradled the dead animal", "cradled"),
            ("Walking home with sack", "walked home"),
            ("Gate squeaked shut", "squeaked"),
            ("Digging holes with spade", "spade"),
            ("Wiping forehead with hand", "forehead"),
            ("Brushing hands on pants", "brushed"),
        ]
        
        for query, expected in action_queries:
            results = vector_store.similarity_search(query, k=5)
            found = any(expected.lower() in result.page_content.lower() for result in results)
            assert found, f"Character action '{expected}' not found for query '{query}'"
    
    def test_story_setting_details(self, setup):
        """Test extraction of setting and environmental details"""
        jpg_file = self.test_files_dir / "test_story.jpg"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(jpg_file), 
            "test_story.jpg"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test setting and environmental details
        setting_queries = [
            ("Neighborhood where she walked", "neighborhood"),
            ("Rusted gate at home", "rusted gate"),
            ("Sun setting during burial", "sun"),
            ("Dirt thrown on lap and shoes", "dirt"),
            ("Squared hole for graves", "hole"),  # OCR shows "hole" singular
            ("Small rocks marking graves", "rock"),
        ]
        
        for query, expected in setting_queries:
            results = vector_store.similarity_search(query, k=5)
            found = any(expected.lower() in result.page_content.lower() for result in results)
            assert found, f"Setting detail '{expected}' not found for query '{query}'"
    
    def test_story_emotional_content(self, setup):
        """Test extraction of emotional and descriptive content"""
        png_file = self.test_files_dir / "test_story.png"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(png_file), 
            "test_story.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test emotional and descriptive elements
        emotional_queries = [
            ("Careful handling of animals", "careful"),
            ("Motionless bundle of fur", "motionless"),
            ("Thumb dipped into skull", "skull"),
            ("Pressing dirt into mount", "pressing"),
            ("Sitting on heels tired", "heels"),
            ("Cracked her back from work", "cracked"),
        ]
        
        for query, expected in emotional_queries:
            results = vector_store.similarity_search(query, k=5)
            found = any(expected.lower() in result.page_content.lower() for result in results)
            assert found, f"Emotional content '{expected}' not found for query '{query}'"
    
    def test_story_comprehension_questions(self, setup):
        """Test comprehension of story themes and meaning"""
        jpg_file = self.test_files_dir / "test_story.jpg"
        
        doc_id, _, _, _ = self.processor.process_file(
            str(jpg_file), 
            "test_story.jpg"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Test comprehension-level questions about the story
        comprehension_queries = [
            ("What does the woman collect", "dead"),  # Dead animals
            ("How does she transport them", "sack"),  # In a sack
            ("Where does she bury them", "graves"),  # In graves
            ("What marks the burial sites", "stones"),  # Small stones/rocks
            ("When does the burial take place", "sun"),  # When sun was setting
            ("What kind of gate does she have", "rusted"),  # Rusted gate
        ]
        
        for query, expected in comprehension_queries:
            results = vector_store.similarity_search(query, k=5)
            found = any(expected.lower() in result.page_content.lower() for result in results)
            assert found, f"Comprehension element '{expected}' not found for query '{query}'"
    
    def test_story_format_consistency(self, setup):
        """Test that PNG and JPG story formats produce consistent results"""
        png_file = self.test_files_dir / "test_story.png"
        jpg_file = self.test_files_dir / "test_story.jpg"
        
        # Process both formats
        png_doc_id, _, png_chunks, _ = self.processor.process_file(
            str(png_file), "test_story.png"
        )
        jpg_doc_id, _, jpg_chunks, _ = self.processor.process_file(
            str(jpg_file), "test_story.jpg"
        )
        
        # Both should extract meaningful content
        assert png_chunks > 0
        assert jpg_chunks > 0
        
        # Test same narrative query on both
        png_store = self.processor.load_vector_store(png_doc_id)
        jpg_store = self.processor.load_vector_store(jpg_doc_id)
        
        test_query = "woman gathered raccoon"
        png_results = png_store.similarity_search(test_query, k=3)
        jpg_results = jpg_store.similarity_search(test_query, k=3)
        
        # Both should find story elements
        png_found = any("raccoon" in r.page_content.lower() for r in png_results)
        jpg_found = any("raccoon" in r.page_content.lower() for r in jpg_results)
        
        assert png_found, "PNG should extract story content about raccoon"
        assert jpg_found, "JPG should extract story content about raccoon"
    
    def test_story_metadata_preservation(self, setup):
        """Test that story image metadata is preserved"""
        png_file = self.test_files_dir / "test_story.png"
        
        doc_id, _, chunks, _ = self.processor.process_file(
            str(png_file), 
            "test_story.png"
        )
        
        vector_store = self.processor.load_vector_store(doc_id)
        
        # Get a sample result
        results = vector_store.similarity_search("story", k=1)
        assert len(results) > 0
        
        # Check metadata
        metadata = results[0].metadata
        assert 'file_type' in metadata
        assert metadata['file_type'] in ['png', 'jpg', 'image']
        assert 'filename' in metadata
        assert metadata['filename'] == 'test_story.png'
        assert 'extraction_method' in metadata
        assert metadata['extraction_method'] == 'OCR'

if __name__ == "__main__":
    pytest.main([__file__, "-v"])