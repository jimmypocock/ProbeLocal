#!/usr/bin/env python3
"""
Comprehensive test for all supported file types
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.document_processor import DocumentProcessor
from src.config import Config

def test_all_supported_file_types():
    """Test that all advertised file types are actually supported"""
    # Mock the LLM system to avoid needing Ollama
    with patch('src.document_processor.OptimizedLLM') as mock_llm:
        mock_llm.return_value.get_embeddings.return_value = Mock()
        processor = DocumentProcessor()
    
    # These should all be supported
    supported_files = [
        "test.pdf",
        "test.txt", 
        "test.csv",
        "test.md",
        "test.docx",
        "test.xlsx",  # Excel files now supported
        "test.png",   # Images now supported
        "test.jpg",   # Images now supported
        "test.jpeg"   # Images now supported
    ]
    
    for filename in supported_files:
        try:
            file_type = processor.detect_file_type(filename)
            assert file_type is not None, f"Failed to detect type for {filename}"
            print(f"✅ {filename} -> {file_type}")
        except ValueError:
            pytest.fail(f"File type {filename} should be supported but isn't")
    
    # These should not be supported
    unsupported_files = [
        "test.mp3",   # Audio - not planned
        "test.mp4",   # Video - not planned
        "test.xyz",   # Random extension
        "test.exe",   # Executable - blocked for security
        "test.sh",    # Script - blocked for security
        "test.zip",   # Archive - blocked for security
        "test.tar"    # Archive - blocked for security
    ]
    
    for filename in unsupported_files:
        with pytest.raises(ValueError):
            processor.detect_file_type(filename)
        print(f"❌ {filename} -> Correctly rejected (not supported)")
    
    # These are detected but not implemented
    future_files = [
        "test.pptx",  # PowerPoint - detected but NotImplementedError
    ]
    
    for filename in future_files:
        file_type = processor.detect_file_type(filename)
        print(f"⏳ {filename} -> {file_type} (detected but not implemented)")

def test_file_type_case_insensitive():
    """Test that file type detection is case insensitive"""
    # Mock the LLM system to avoid needing Ollama
    with patch('src.document_processor.OptimizedLLM') as mock_llm:
        mock_llm.return_value.get_embeddings.return_value = Mock()
        processor = DocumentProcessor()
    
    test_cases = [
        ("TEST.PDF", "pdf"),
        ("Test.TXT", "text"),
        ("DATA.CSV", "csv"),
        ("README.MD", "markdown"),
        ("Document.DOCX", "docx"),
        ("MiXeD.CaSe.pDf", "pdf")
    ]
    
    for filename, expected_type in test_cases:
        detected = processor.detect_file_type(filename)
        assert detected == expected_type, f"Failed for {filename}: expected {expected_type}, got {detected}"
        print(f"✅ {filename} -> {detected}")

if __name__ == "__main__":
    print("Testing all supported file types...")
    with patch('src.document_processor.OptimizedLLM') as mock_llm:
        mock_llm.return_value.get_embeddings.return_value = Mock()
        test_all_supported_file_types()
    print("\nTesting case insensitivity...")
    with patch('src.document_processor.OptimizedLLM') as mock_llm:
        mock_llm.return_value.get_embeddings.return_value = Mock()
        test_file_type_case_insensitive()
    print("\n✅ All file type tests passed!")